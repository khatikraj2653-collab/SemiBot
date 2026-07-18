import json
with open("tools/stats_items45_results.json") as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
