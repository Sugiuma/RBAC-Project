# **Project Report: Role-Based RAG System with Structured Query Handling**

## **Project Overview**

This project implements an advanced **Retrieval-Augmented Generation (RAG)** system tailored for multi-role enterprise environments. Users can upload documents (Markdown, CSV), and the system retrieves answers based on the user's role. The architecture includes:

* **Streamlit UI**: for user login, role-based access, and document upload.
* **FastAPI backend**: for business logic, user management, and RAG handling.
* **Chroma vector store**: for dense embedding search (unstructured).
* **DuckDB**: for SQL-like queries over structured data (CSV).
* **Query Classifier**: to route user queries to the appropriate retrieval mode.
* **Fallback Mechanism**: to ensure graceful degradation when structured query fails.

---

## **Key Features**

### ✅ **1. Role-Based Access Control**

* Users are assigned roles (e.g., HR, Finance, QA).
* Each document is tagged with the role it’s meant for.
* Queries are filtered to only retrieve content associated with the user's role.

### ✅ **2. Dual Query Handling (RAG + SQL)**

* **Unstructured queries** (e.g., "What are the QA best practices?") → handled by Chroma vector search + LLM.
* **Structured queries** (e.g., "Show me all employees with salary > 100K") → handled via DuckDB.

---

## **Why DuckDB for Structured Queries?**

We adopted **DuckDB** for handling structured queries on uploaded CSVs because:

* ✅ **In-process SQL engine**: DuckDB runs embedded in Python, no separate server needed.
* ✅ **Zero setup**: No configuration required; great for file-based structured queries.
* ✅ **Lightweight + Fast**: Efficiently handles large CSV files in memory.
* ✅ **Supports Pandas + SQL natively**: Easy to switch between Python dataframes and SQL.
* ✅ **Isolated query execution**: Each user session can be sandboxed.

This made DuckDB a perfect fit for answering precise, structured queries over tabular data uploaded by the user.

---

## **Query Classification Module**

A **query classifier** was implemented to determine the intent behind the user's input:

| Intent | Target System | Example Query                     |
| ------ | ------------- | --------------------------------- |
| RAG    | Chroma + LLM  | “Summarize this finance document” |
| SQL    | DuckDB        | “List invoices over \$5000”       |

* We trained a lightweight intent classifier using examples and embeddings.
* The classifier directs the query to either:

  * RAG (textual search in vector DB),
  * SQL (execute structured query using DuckDB).

This significantly **improved accuracy and speed**, avoiding LLM overhead when a SQL answer sufficed.

---

## **Fallback Handling Strategy**

In edge cases, a **fallback mechanism** is implemented:

1. If a **SQL query fails** (e.g., malformed, missing table):

   * Log the error,
   * Fallback to the RAG system with rephrased prompt like:
     *"Unable to process SQL. Try answering from available documents instead."*

2. If **no relevant docs** found in RAG:

   * Return a graceful message,
   * Suggest rephrasing or uploading new content.

This ensures the system is **resilient** and never leaves the user with a hard error.

---

## **System Architecture Diagram**

```
User (Streamlit UI)
       │
       ▼
   FastAPI Backend
       │
 ┌─────┴──────────────┐
 │  Query Classifier  │
 └─────┬──────────────┘
       │
  ┌────▼────┐      ┌─────▼───────┐
  │ DuckDB  │      │ VectorStore │
  │ (SQL)   │      │ (Chroma)    │
  └────┬────┘      └────┬────────┘
       ▼                ▼
 Structured Output   LLM Completion
       │                │
       └───────► Final Answer
```

---

## **Future Enhancements**

* ✅ Integrate **OpenInference** for evaluation (faithfulness, relevance).
* ✅ Support **admin analytics dashboard** (e.g., query types, usage).
* ✅ Add **table+text hybrid retrieval** (RAG with tabular fusion).
* ✅ Caching of SQL queries for repeated execution.

---

## **Conclusion**

This RAG system demonstrates a **flexible, intelligent retrieval pipeline** that dynamically routes user queries to either unstructured (LLM-based) or structured (SQL-based) engines. The use of **DuckDB**, **query classification**, and **fallback design** has led to a robust solution that balances performance, explainability, and adaptability. It’s an ideal architecture for real-world enterprise AI assistants where both document knowledge and structured analytics are needed in one place
