from .rag_module import get_rag_chain


async def ask_rag(question: str, role: str, cohere_api_key: str = None) -> dict:
    chain = get_rag_chain(user_role=role, cohere_api_key=cohere_api_key)
    result = chain.invoke({"input": question})
    return {"answer": result["answer"]}

    """
      # result now includes: {"context": [...], "answer": "..."}
    return {
        "answer": result["answer"],
        "context": result["context"]
    }"""