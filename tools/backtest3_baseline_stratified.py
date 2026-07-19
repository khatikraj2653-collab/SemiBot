import json

with open("tools/backtest2_final_results.json") as f:
    data = json.load(f)

results = data["results"]

def get_cap_tier(market_cap_usd):
    if market_cap_usd > 1_000_000_000_000:
        return ">$1T"
    elif market_cap_usd > 500_000_000_000:
        return "$500B-$1T"
    elif market_cap_usd > 100_000_000_000:
        return "$100B-$500B"
    elif market_cap_usd > 50_000_000_000:
        return "$50B-$100B"
    elif market_cap_usd > 10_000_000_000:
        return "$10B-$50B"
    else:
        return "<$10B"

def get_5tier(market_cap_usd):
    if market_cap_usd > 200_000_000_000:
        return "Mega-cap"
    elif market_cap_usd > 10_000_000_000:
        return "Large-cap"
    elif market_cap_usd > 2_000_000_000:
        return "Mid-cap"
    else:
        return "Small-cap"

tiers_6 = {}
tiers_5 = {}
overall = {"semibot_correct": 0, "always_up_correct": 0, "soxx_correct": 0, "total": 0}

for r in results:
    market_cap = r.get("market_cap_usd")
    if market_cap is None:
        continue

    actual_direction = r.get("actual_direction")
    semibot_pred = r.get("predicted_direction")

    if actual_direction is None or semibot_pred is None:
        continue

    semibot_correct = r.get("correct")
    always_up_correct = (actual_direction == "UP")
    soxx_correct = None

    tier6 = get_cap_tier(market_cap)
    tier5 = get_5tier(market_cap)

    for tier_dict, tier_key in [(tiers_6, tier6), (tiers_5, tier5)]:
        if tier_key not in tier_dict:
            tier_dict[tier_key] = {"semibot_correct": 0, "always_up_correct": 0, "soxx_correct": 0, "soxx_total": 0, "total": 0}
        tier_dict[tier_key]["total"] += 1
        if semibot_correct:
            tier_dict[tier_key]["semibot_correct"] += 1
        if always_up_correct:
            tier_dict[tier_key]["always_up_correct"] += 1
        if soxx_correct is not None:
            tier_dict[tier_key]["soxx_total"] += 1
            if soxx_correct:
                tier_dict[tier_key]["soxx_correct"] += 1

    overall["total"] += 1
    if semibot_correct:
        overall["semibot_correct"] += 1
    if always_up_correct:
        overall["always_up_correct"] += 1
    if soxx_correct is not None:
        overall.setdefault("soxx_total", 0)
        overall["soxx_total"] += 1
        if soxx_correct:
            overall["soxx_correct"] += 1

print("=== BACKTEST 3 (STRATIFIED): SemiBot vs Naive Baselines by Market Cap ===\n")

print(f"{'Tier':<15} {'N':>5} {'SemiBot':>10} {'Always-UP':>12} {'SOXX-Trend':>12}")
for tier_key, d in tiers_6.items():
    semibot_pct = round((d["semibot_correct"] / d["total"]) * 100, 1) if d["total"] > 0 else 0
    up_pct = round((d["always_up_correct"] / d["total"]) * 100, 1) if d["total"] > 0 else 0
    soxx_pct = round((d["soxx_correct"] / d["soxx_total"]) * 100, 1) if d.get("soxx_total", 0) > 0 else None
    print(f"{tier_key:<15} {d['total']:>5} {semibot_pct:>9}% {up_pct:>11}% {(str(soxx_pct)+'%') if soxx_pct is not None else 'N/A':>12}")

print(f"\n{'OVERALL':<15} {overall['total']:>5} "
      f"{round((overall['semibot_correct']/overall['total'])*100,1):>9}% "
      f"{round((overall['always_up_correct']/overall['total'])*100,1):>11}% "
      f"{(str(round((overall['soxx_correct']/overall['soxx_total'])*100,1))+'%') if overall.get('soxx_total',0) > 0 else 'N/A':>12}")

with open("tools/backtest3_baseline_stratified_results.json", "w") as f:
    json.dump({"tiers_6": tiers_6, "tiers_5": tiers_5, "overall": overall}, f, indent=2)

print("\nSaved to tools/backtest3_baseline_stratified_results.json")