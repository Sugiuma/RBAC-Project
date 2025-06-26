import pandas as pd
import json

# Load evaluation results CSV
df = pd.read_csv("evaluation_results_openai.csv")

# Lists to store each score
faithfulness_scores = []
relevancy_scores = []
context_recall_scores = []

for i, row in df.iterrows():
    try:
        metrics = json.loads(row["metrics"])
        faithfulness_scores.append(metrics.get("faithfulness", 0))
        relevancy_scores.append(metrics.get("relevancy", 0))
        context_recall_scores.append(metrics.get("context_recall", 0))
    except Exception as e:
        print(f"Row {i} has invalid JSON: {e}")
        continue

# Compute averages
avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
avg_relevancy = sum(relevancy_scores) / len(relevancy_scores)
avg_context_recall = sum(context_recall_scores) / len(context_recall_scores)

# Print summary
print("=== Evaluation Summary ===")
print(f"Faithfulness:     {avg_faithfulness:.2f}")
print(f"Relevancy:        {avg_relevancy:.2f}")
print(f"Context Recall:   {avg_context_recall:.2f}")
