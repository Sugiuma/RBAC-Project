import sqlite3
import pandas as pd
import os
from pathlib import Path
from pydantic import BaseModel
import duckdb

from fastapi import FastAPI, UploadFile,File, Form, HTTPException, Depends
from fastapi import BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from langchain_community.embeddings.openai import OpenAIEmbeddings
from dotenv import load_dotenv
from passlib.hash import bcrypt
from langchain_core.documents import Document

from .rag_utils.rag_module import run_indexer,vectorstore,get_rag_chain
from .rag_utils.query_classifier import detect_query_type_llm
from .rag_utils.csv_query import ask_csv
from .rag_utils.rag_chain import ask_rag

app = FastAPI()
security = HTTPBasic()
load_dotenv()

# Set path to DuckDB database file
DUCKDB_DIR = Path("static/data")
DUCKDB_DIR.mkdir(parents=True, exist_ok=True)  # ensure directory exists

DUCKDB_PATH = DUCKDB_DIR/"structured_queries.duckdb"

# Connect to DuckDB file (creates file if not exists)
duck_conn = duckdb.connect(str(DUCKDB_PATH))

duck_conn.execute("""
    CREATE TABLE IF NOT EXISTS tables_metadata (
        table_name TEXT,
        role TEXT
    )
""")


# -------------------------
# === DATABASE SETUP ===
# -------------------------

conn = sqlite3.connect("roles_docs.db", check_same_thread=False)
c = conn.cursor()
c.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    role TEXT,
    filepath TEXT NOT NULL,
    embedded INTEGER DEFAULT 0
);
""")
conn.commit()

def create_default_user():
    conn_local = sqlite3.connect("roles_docs.db")
    c_local = conn_local.cursor()

    c_local.execute("INSERT OR IGNORE INTO roles (role_name) VALUES (?)", ("C-Level",))
    hashed_pw = bcrypt.hash("admin123")
    try:
        c_local.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", hashed_pw, "C-Level"))
        conn_local.commit()
        print("✅ Default C-Level user created.")
    except sqlite3.IntegrityError:
        print("⚠️ User already exists.")
    conn_local.close()


# Call it on startup
create_default_user()

# -------------------------
# === AUTHENTICATION ===
# -------------------------
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    print("username: ", username)
    print("password: ", password)
    c.execute("SELECT password, role FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    print("DB row:", row)
    if not row or not bcrypt.verify(password, row[0]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": row[1]}

# === MODELS ===
class ChatRequest(BaseModel):
    question: str

# -------------------------
# === ROUTES ===
# -------------------------
@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}

@app.get("/roles")
def get_roles(user=Depends(authenticate)):
    c.execute("SELECT role_name FROM roles")
    roles = [r[0] for r in c.fetchall()]
    return {"roles": roles}

@app.post("/create-user")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    user=Depends(authenticate)
):
    if user["role"] != "C-Level":
        raise HTTPException(status_code=403, detail="Only C-Level can create users.")

    c.execute("SELECT 1 FROM roles WHERE role_name = ?", (role,))
    if not c.fetchone():
        raise HTTPException(status_code=400, detail="Invalid role")

    hashed = bcrypt.hash(password)
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed, role))
        conn.commit()
        return {"message": f"User '{username}' added with role '{role}'"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already exists")

@app.post("/create-role")
def create_role(role_name: str = Form(...), user=Depends(authenticate)):
    if user["role"] != "C-Level":
        raise HTTPException(status_code=403, detail="Only C-Level can create roles.")

    try:
        c.execute("INSERT INTO roles (role_name) VALUES (?)", (role_name,))
        conn.commit()
        return {"message": f"Role '{role_name}' created"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Role already exists")



UPLOAD_DIR = "static/uploads"

@app.post("/upload-docs")
async def upload_docs(file: UploadFile = File(...), role: str = Form(...)):
    try:
        filename = file.filename
        extension = Path(filename).suffix.lower()

        # Prepare storage
        role_dir = os.path.join(UPLOAD_DIR, role)
        os.makedirs(role_dir, exist_ok=True)
        filepath = os.path.join(role_dir, filename)

        # Read content + save file
        data = await file.read()  # Read once

        with open(filepath, "wb") as f:
            f.write(data)  # Save file for future indexing

        # Convert to string content for validation (optional)
        if extension == ".csv":
            from io import BytesIO
            df = pd.read_csv(BytesIO(data))
            content = df.to_string(index=False)

             # Load for DuckDB
            df1 = pd.read_csv(filepath)
            table_name = Path(filepath).stem.replace("-", "_")

            duck_conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df1")

            # ✅ Save metadata to DuckDB tables_metadata
            duck_conn.execute(
                "INSERT INTO tables_metadata (table_name, role) VALUES (?, ?)",
                (table_name, role)
            )

        elif extension == ".md":
            content = data.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Save metadata to DB
        conn = sqlite3.connect("roles_docs.db")
        c = conn.cursor()
        c.execute("INSERT INTO documents (filename, role, filepath) VALUES (?, ?, ?)",
                  (filename, role, filepath))
        #doc_id = c.lastrowid  # ✅ Get inserted doc ID
        conn.commit()
        conn.close()
        
        run_indexer()
        print("Files indexed successfully")
        return JSONResponse(content={"message": f"{filename} uploaded successfully for role '{role}'."})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    
   
"""
@app.post("/chat")
async def chat(req: ChatRequest, user=Depends(authenticate)):
    role = user["role"]
    username = user["username"]
    question = req.question

    # 1. Detect mode: SQL or RAG
    mode = detect_query_type_llm(question)
    print(mode)

    
    # 2. Route to appropriate handler
    if mode == "SQL":
        result = await ask_csv(question, role, username, return_sql=True)
        #result = await ask_csv(question)  # assuming ask_csv returns dict with "answer" or similar
    else:
    
        result = await ask_rag(question, role)  # pass role to enforce role-based doc access

    return {
        "user": username,
        "role": role,
        "mode": mode,
        "answer": result["answer"],
        **({"sql": result["sql"]} if "sql" in result else {})
    }
"""
@app.post("/chat")
async def chat(req: ChatRequest, user=Depends(authenticate)):
    role = user["role"]
    username = user["username"]
    question = req.question

    # 1. Detect mode: SQL or RAG
    mode = detect_query_type_llm(question)
    print(f"Detected mode: {mode}")

    result = {}
    fallback_used = False

    # 2. Route to appropriate handler
    if mode == "SQL":
        try:
            result = await ask_csv(question, role, username, return_sql=True)

            if result.get("error") or not result.get("answer", "").strip():
                raise ValueError("SQL query blocked or failed")

        except Exception as e:
            print(f"[SQL Fallback Triggered] Error: {e}")
            result = await ask_rag(question, role)
            fallback_used = True
            mode = "SQL → fallback to RAG"

    else:
        result = await ask_rag(question, role)

    return {
        "user": username,
        "role": role,
        "mode": mode,
        "fallback": fallback_used,
        "answer": result["answer"],
        **({"sql": result["sql"]} if "sql" in result else {})
    }
