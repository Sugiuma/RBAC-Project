from rag_module import vectorstore, model, chat_prompt  

from langchain.chains import RetrievalQA
from langchain.schema import Document
import pandas as pd
import time, os
from openai import OpenAI

# ========== ENV CONFIG ==========
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========== QUESTION GENERATION ==========
def generate_question_with_openai(text_chunk):
    prompt = f"""
    Based on the following text, write one specific, factual question that is directly answerable from it:

    \"\"\"{text_chunk}\"\"\"

    Only return the question.
    """

    response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    )

    return response.choices[0].message.content.strip()


def generate_qa_dataset(docs, output_csv="qa_pairs_openai.csv"):
    qa_list = []
    for doc in docs:
        question = generate_question_with_openai(doc.page_content)
        qa_list.append({
            "question": question,
            "answer": doc.page_content,
            "role": doc.metadata.get("role", ""),
            "source": doc.metadata.get("source", "")
        })
        time.sleep(1.2)
    pd.DataFrame(qa_list).to_csv(output_csv, index=False)
    return qa_list

# ========== RAG OUTPUT EVALUATION ==========
def evaluate_with_openai(question, predicted_answer, retrieved_contexts, reference_answer):
    prompt = f"""You are an evaluator for a RAG system.

Evaluate the predicted answer to a question using the retrieved context and compare it to the ground truth.

Return a JSON object with the following scores between 0 and 1:
- "faithfulness": Is the predicted answer grounded in the retrieved context?
- "relevancy": Is the answer relevant to the question?
- "context_recall": How well does the retrieved context cover the ground truth?

Question: {question}

Retrieved Context:
{retrieved_contexts}

Predicted Answer:
{predicted_answer}

Ground Truth:
{reference_answer}

Respond ONLY in valid JSON like:
{{
  "faithfulness": 1.0,
  "relevancy": 0.8,
  "context_recall": 0.9
}}
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()

# ========== RAG EVALUATION RUNNER ==========
def run_rag_eval(qa_list, retriever):
    qa_chain = RetrievalQA.from_chain_type(
        llm=model,
        retriever=retriever,
        return_source_documents=True
    )

    results = []
    for qa in qa_list:
        question = qa["question"]
        ground_truth = qa["answer"]

        result = qa_chain.invoke({"query": question})
        predicted = result["result"]
        contexts = "\n---\n".join([doc.page_content for doc in result["source_documents"]])

        try:
            scores = evaluate_with_openai(question, predicted, contexts, ground_truth)
        except Exception as e:
            scores = str(e)

        results.append({
            "question": question,
            "prediction": predicted,
            "ground_truth": ground_truth,
            "contexts": contexts,
            "metrics": scores
        })

    pd.DataFrame(results).to_csv("evaluation_results_openai.csv", index=False)
    return results

# ========== RUN EXAMPLE ==========
if __name__ == "__main__":
    docs = vectorstore.similarity_search("finance", k=50)
    qa_list = generate_qa_dataset(docs)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    run_rag_eval(qa_list, retriever)
