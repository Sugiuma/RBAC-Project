import sys
from pathlib import Path

# Add root directory to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app  # adjust as needed
import io
from unittest.mock import patch

client = TestClient(app)

@pytest.fixture
def c_level_auth():
    return ("admin", "admin123")

@pytest.fixture
def regular_auth():
    return ("testuser", "testpass")

def test_create_role_c_level(c_level_auth):
    res = client.post("/create-role", auth=c_level_auth, data={"role_name": "engineering"})
    assert res.status_code == 200
    assert "Role 'engineering' created" in res.json().get("message", "")


def test_create_user_c_level(c_level_auth):
    # First ensure the role exists
    client.post("/create-role", auth=c_level_auth, data={"role_name": "marketing"})

    res = client.post(
        "/create-user",
        auth=c_level_auth,
        data={
            "username": "newuser",
            "password": "newpass",
            "role": "marketing"
        }
    )
    assert res.status_code == 200
    assert "User 'newuser'" in res.json().get("message", "")



def test_upload_csv_doc(c_level_auth):
    content = b"Name,Policy\nAdmin,Compliant"
    file = io.BytesIO(content)
    client.post("/create-role", auth=c_level_auth, data={"role_name": "csvrole"})

    res = client.post(
        "/upload-docs",
        auth=c_level_auth,
        files={"file": ("test.csv", file, "text/csv")},
        data={"role": "csvrole"}
    )

    assert res.status_code == 200
    assert "uploaded successfully" in res.json()["message"]

def test_upload_md_doc(c_level_auth):
    content = b"# Engineering Policies\nFollow coding guidelines."
    file = io.BytesIO(content)
    client.post("/create-role", auth=c_level_auth, data={"role_name": "mdrole"})

    res = client.post(
        "/upload-docs",
        auth=c_level_auth,
        files={"file": ("guide.md", file, "text/markdown")},
        data={"role": "mdrole"}
    )

    assert res.status_code == 200
    assert "uploaded successfully" in res.json()["message"]

@patch("app.main.detect_query_type_llm", return_value="RAG")
@patch("app.main.ask_rag", return_value={"answer": "This is RAG response"})
def test_chat_rag_mode(mock_ask_rag, mock_detect, c_level_auth):
    res = client.post(
        "/chat",
        auth=c_level_auth,
        json={"question": "What are engineering policies?"}
    )
    assert res.status_code == 200
    assert res.json()["mode"] == "RAG"
    assert res.json()["answer"] == "This is RAG response"

@patch("app.main.detect_query_type_llm", return_value="SQL")
@patch("app.main.ask_csv", return_value={"answer": "Here is the SQL data", "sql": "SELECT * FROM table"})
def test_chat_sql_mode(mock_ask_csv, mock_detect, c_level_auth):
    res = client.post(
        "/chat",
        auth=c_level_auth,
        json={"question": "List all employees in HR"}
    )
    assert res.status_code == 200
    assert res.json()["mode"] == "SQL"
    assert res.json()["answer"] == "Here is the SQL data"
    assert "sql" in res.json()

def test_create_role_no_auth():
    res = client.post("/create-role", data={"role_name": "bad"})
    assert res.status_code == 401 or res.status_code == 403


from unittest.mock import patch
"""
@patch("main.detect_query_type_llm", return_value="RAG")
@patch("main.ask_rag")
def test_chat_rag_blocks_cross_role(mock_ask_rag, mock_detect, regular_auth):
    res = client.post(
        "/chat",
        auth=regular_auth,
        json={"question": "What are the finance team policies?"}
    )

    # Check role filtering is enforced
    mock_ask_rag.assert_called_once()
    _, kwargs = mock_ask_rag.call_args
    assert kwargs["role"] == "HR"  # Role passed must be user's role

    # Validate response is still returned safely
    assert res.status_code == 200
    assert "answer" in res.json()

@patch("main.detect_query_type_llm", return_value="SQL")
@patch("main.ask_csv")
def test_chat_sql_blocks_cross_role(mock_ask_csv, mock_detect, regular_auth):
    res = client.post(
        "/chat",
        auth=regular_auth,
        json={"question": "List salaries from Finance department"}
    )

    mock_ask_csv.assert_called_once()
    _, kwargs = mock_ask_csv.call_args
    assert kwargs["role"] == "HR"  # Should not be Finance

    assert res.status_code == 200
    assert "answer" in res.json()

@patch("main.ask_rag", return_value={"answer": "No documents found for your role."})
def test_chat_rag_returns_nothing_for_unmatched_docs(mock_ask_rag, regular_auth):
    res = client.post(
        "/chat",
        auth=regular_auth,
        json={"question": "Tell me about executive bonuses"}
    )
    assert res.status_code == 200
    assert "no documents found" in res.json()["answer"].lower()
"""