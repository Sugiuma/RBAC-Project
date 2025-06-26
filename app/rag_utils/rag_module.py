# ========== CONFIG ==========
from pathlib import Path
import os
import pandas as pd
from collections import defaultdict
from langchain.schema import Document
import sqlite3


from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

from .secret_key import openapi_key,langchain_key,cohere_api_key



os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_PROJECT"] = "RAG"
os.environ["LANGCHAIN_API_KEY"] = langchain_key
os.environ["OPENAI_API_KEY"] = openapi_key
os.environ["COHERE_API_KEY"] = cohere_api_key


# ==============================
# ====Split,load,embed==========
# ==============================

openai_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(
    collection_name="my_collection",
    persist_directory="chroma_db",
    embedding_function=openai_embeddings
)


def embed_documents_to_vectorstore(docs):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore.add_documents(splits)
    
    print("Documents embedded and saved to vectorstore.")
    print("Total documents:", len(vectorstore.get()["documents"]))
    #print("Chunks being added:")
    #for chunk in splits:
    #    print(f"---\n{chunk.page_content[:150]}...\nMetadata: {chunk.metadata}")


def load_file(filepath, role):
    ext = Path(filepath).suffix.lower()
    try:
        if ext == ".csv":
            df1 = pd.read_csv(filepath)
            content = df1.to_string(index=False)
               

        elif ext == ".md":
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            return None

        return Document(
            page_content=content,
            metadata={"role": role.lower(), "source": Path(filepath).name}
        )
    except Exception as e:
        print(f"Failed to process {filepath}: {e}")
        return None

def run_indexer():
    conn = sqlite3.connect("roles_docs.db")
    c = conn.cursor()
    c.execute("SELECT id, filepath, role FROM documents WHERE embedded = 0")
    docs_to_embed = []

    for doc_id, path, role in c.fetchall():
        doc = load_file(path, role)
        if doc:
            docs_to_embed.append((doc_id, doc))

    if docs_to_embed:
        docs = [d for (_, d) in docs_to_embed]
        #print(docs)
        embed_documents_to_vectorstore(docs)

        for doc_id, _ in docs_to_embed:
            c.execute("UPDATE documents SET embedded = 1 WHERE id = ?", (doc_id,))
        conn.commit()

    conn.close()
    print(f"Indexed {len(docs_to_embed)} documents.")

# ==============================
# ========== PROMPT TEMPLATE ==========
# ==============================
system_prompt = (
    "You are an assistant for summarizing and answering queries from internal company documents.\n"
    "Always use the retrieved context to answer the query, even if partial.\n"
    "Do not guess. If data is not found, explain what you searched for.\n"
    "When responding:\n"
    "- Add **Source** from document metadata if possible.\n"
    "- Use headers\n"
    "- Use bullet points\n"
    "- For CSV-style data, format in table with two columns\n"
    "\n{context}"
)

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# ==============================
# ========== MODEL ==========
# ==============================
model = ChatOpenAI(
    model="gpt-4o",  
    temperature=0.2
)

question_answering_chain = create_stuff_documents_chain(model, chat_prompt)

# ==============================
# Add a Reranker
# ==============================
def wrap_with_reranker(retriever, cohere_api_key, top_n=4):
    #print("[INFO] Using Cohere reranker.")
    reranker = CohereRerank(cohere_api_key=cohere_api_key, top_n=top_n)
    return ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=retriever
    )

def get_rag_chain(user_role: str,cohere_api_key: str = None):
    user_role = user_role.lower()

    if user_role == "c-level":
        # C-level sees everything
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    elif user_role == "general":
        # General role sees only general documents
        retriever = vectorstore.as_retriever(search_kwargs={
            "k": 4,
            "filter": {"role": "general"}
        })

    else:
        # All other roles see their docs + general
        retriever = vectorstore.as_retriever(search_kwargs={
            "k": 4,
            "filter": {
                "role": {"$in": [user_role, "general"]}
            }
        })

    # wrap with reranker
    if cohere_api_key:
        print("Using cohere reranker")
        retriever = wrap_with_reranker(retriever, cohere_api_key)

    return create_retrieval_chain(retriever, question_answering_chain)
    """
    from langchain_core.runnables import RunnableLambda, RunnableMap

    extract_input = RunnableLambda(lambda x: x["input"])

    return RunnableMap({
        "context": extract_input | retriever,
        "answer": extract_input | retriever | question_answering_chain
    })"""


"""
# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    run_indexer()  
"""
    # ========== EXAMPLE USAGE ==========
"""
    user_role = "hr"  
    rag_chain = get_rag_chain(user_role)

    
    query = "give me Campaign Highlights from marketing summary."
    response = rag_chain.invoke({"input": query})

    print((response["answer"]))
    for doc in response.get("context", []):
        print(f"Source: {doc.metadata['source']}, Role: {doc.metadata.get('role')}")

"""

