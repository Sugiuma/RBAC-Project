import re
import duckdb
import os,tabulate
from openai import OpenAI

# DuckDB setup
DUCKDB_FILE = "static/data/structured_queries.duckdb"
duck_conn = duckdb.connect(DUCKDB_FILE, read_only=False)

# OpenAI setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_allowed_tables_for_role(role: str) -> list[str]:
    if role.lower() == "c-level":
        query = "SELECT table_name FROM tables_metadata"
        return [row[0] for row in duck_conn.execute(query).fetchall()]
    elif role.lower() == "general":
        query = "SELECT table_name FROM tables_metadata WHERE role = 'general'"
        return [row[0] for row in duck_conn.execute(query).fetchall()]
    else:
        query = """
        SELECT table_name FROM tables_metadata
        WHERE role = ? OR role = 'general'
        """
        return [row[0] for row in duck_conn.execute(query, [role]).fetchall()]

def extract_tables_from_sql(sql: str) -> list[str]:
    # Extract tables used in FROM and JOIN clauses
    return re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql, flags=re.IGNORECASE)

def flatten_matches(matches: list[tuple]) -> list[str]:
    return [item for tup in matches for item in tup if item]

def is_safe_query(sql: str) -> bool:
    lowered = sql.strip().lower()

    # Remove trailing semicolon for validation
    if lowered.endswith(";"):
        lowered = lowered[:-1].strip()

    # Check that it's a single SELECT statement
    return lowered.startswith("select") and ";" not in lowered[1:]

def translate_nl_to_sql(question: str, allowed_tables: list[str]) -> str:
    prompt = f"""
You are an assistant that converts natural language questions into safe SQL SELECT queries.

Constraints:
- Only use these tables: {', '.join(allowed_tables)}
- Do not modify, insert, delete, or drop data.
- Return only a single SELECT query.
- if asked for details about employee,if employee_name column header is not found, search for full name, last name etc in headers.
Question: "{question}"

SQL:
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

#async def ask_csv(question: str, role: str) -> dict:
async def ask_csv(question: str, role: str, username: str, return_sql: bool = False) -> dict:

    allowed_tables = get_allowed_tables_for_role(role)

    try:
        # Step 1: Translate NL → SQL
        sql = translate_nl_to_sql(question, allowed_tables)
        print(sql)
        # Step 2: Security check: SELECT-only
        if not is_safe_query(sql):
            return {"answer": "⚠️ Only SELECT queries are allowed.",
                "error": True}

        # Step 3: Validate table usage
        raw_matches = extract_tables_from_sql(sql)
        referenced_tables = flatten_matches(raw_matches)

        for table in referenced_tables:
            if table not in allowed_tables:
                return {"answer": f"⛔ Access denied to table: {table}",
                    "error": True}

        # Step 4: Execute query
        result = duck_conn.execute(sql).fetchall()
        columns = [desc[0] for desc in duck_conn.description]
        output = [list(row) for row in result]  # convert rows to lists

        status = "Success" if output else "Success (no results)"
        #log_query(username, role, question, sql, status)

        # Format as markdown table
        table = tabulate.tabulate(output, headers=columns, tablefmt="github")

        response = {
            "answer": table if output else "✅ Query executed, but no results found."
        }
        if return_sql:
            response["sql"] = sql

        return response

    except Exception as e:
        #return {"answer": f"❌ Error: {str(e)}"}
         return {
            "answer": f"❌ Error: {str(e)}",
            "error": True
        }

