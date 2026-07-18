import json
with open("tools/backtest2_final_results.json") as f:
    data = json.load(f)

print("config:", data["config"])
print()
print("summary:", data["summary"])
print()
results = data["results"]
print("Number of results:", len(results))
print("First result:", results[0])
print()
print("skipped count:", len(data["skipped"]))
