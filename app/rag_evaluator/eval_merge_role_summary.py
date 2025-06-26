import pandas as pd
import json

# Load both CSVs
qa_df = pd.read_csv("qa_pairs_openai.csv")
eval_df = pd.read_csv("evaluation_results_openai.csv")

# Merge on 'question'
merged_df = pd.merge(eval_df, qa_df[['question', 'role']], on='question', how='left')

# Save merged output
merged_df.to_csv("final_eval_with_roles.csv", index=False)


from collections import defaultdict

# Parse metrics and add to new columns
def extract_metric(row, metric_name):
    try:
        metrics = json.loads(row["metrics"])
        return metrics.get(metric_name, None)
    except:
        return None

merged_df["faithfulness"] = merged_df.apply(lambda row: extract_metric(row, "faithfulness"), axis=1)
merged_df["relevancy"] = merged_df.apply(lambda row: extract_metric(row, "relevancy"), axis=1)
merged_df["context_recall"] = merged_df.apply(lambda row: extract_metric(row, "context_recall"), axis=1)

# Drop rows with missing metrics
filtered_df = merged_df.dropna(subset=["faithfulness", "relevancy", "context_recall"])

# Group by role and compute averages
grouped = filtered_df.groupby("role")[["faithfulness", "relevancy", "context_recall"]].mean()

# Show summary
print("=== Role-based Evaluation Summary ===")
print(grouped.round(2))
