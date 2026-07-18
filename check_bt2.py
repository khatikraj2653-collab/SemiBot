import json
with open("tools/backtest2_final_results.json") as f:
    data = json.load(f)

print(type(data))
if isinstance(data, list):
    print("Number of records:", len(data))
    print("First record keys:", list(data[0].keys()) if data else "empty")
    print("First record:", data[0] if data else "empty")
elif isinstance(data, dict):
    print("Top-level keys:", list(data.keys()))
