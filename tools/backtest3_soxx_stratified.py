import json
import yfinance as yf
import pandas as pd

with open("tools/backtest2_final_results.json") as f:
    data = json.load(f)

results = data["results"]
dates = data["config"]["dates"]

print("Fetching SOXX historical data...")
soxx = yf.Ticker("SOXX").history(start="2025-06-01", end="2026-06-01")
soxx.index = soxx.index.tz_localize(None)

def get_soxx_trend(analysis_date_str, lookback_days=20):
    analysis_date = pd.Timestamp(analysis_date_str)
    window = soxx[soxx.index <= analysis_date].tail(lookback_days)
    if len(window) < 2:
        return None
    start_price = window["Close"].iloc[0]
    end_price = window["Close"].iloc[-1]
    return "UP" if end_price > start_price else "DOWN"

date_trends = {}
for d in dates:
    trend = get_soxx_trend(d)
    date_trends[d] = trend
    print(f"  {d}: SOXX prior trend = {trend}")

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

tiers = {}
overall = {"semibot_correct": 0, "soxx_correct": 0, "total": 0}

for r in results:
    market_cap = r.get("market_cap_usd")
    actual_direction = r.get("actual_direction")
    semibot_correct = r.get("correct")
    analysis_date = r.get("date")

    if market_cap is None or actual_direction is None or analysis_date not in date_trends:
        continue

    soxx_pred = date_trends[analysis_date]
    if soxx_pred is None:
        continue

    soxx_correct = (soxx_pred == actual_direction)
    tier = get_cap_tier(market_cap)

    if tier not in tiers:
        tiers[tier] = {"semibot_correct": 0, "soxx_correct": 0, "total": 0}
    tiers[tier]["total"] += 1
    if semibot_correct:
        tiers[tier]["semibot_correct"] += 1
    if soxx_correct:
        tiers[tier]["soxx_correct"] += 1

    overall["total"] += 1
    if semibot_correct:
        overall["semibot_correct"] += 1
    if soxx_correct:
        overall["soxx_correct"] += 1

print("\n=== BACKTEST 3 (SOXX-TREND, STRATIFIED) ===\n")
print(f"{'Tier':<15} {'N':>5} {'SemiBot':>10} {'SOXX-Trend':>12}")
for tier_key, d in tiers.items():
    semibot_pct = round((d["semibot_correct"] / d["total"]) * 100, 1) if d["total"] > 0 else 0
    soxx_pct = round((d["soxx_correct"] / d["total"]) * 100, 1) if d["total"] > 0 else 0
    print(f"{tier_key:<15} {d['total']:>5} {semibot_pct:>9}% {soxx_pct:>11}%")

print(f"\n{'OVERALL':<15} {overall['total']:>5} "
      f"{round((overall['semibot_correct']/overall['total'])*100,1):>9}% "
      f"{round((overall['soxx_correct']/overall['total'])*100,1):>11}%")

with open("tools/backtest3_soxx_stratified_results.json", "w") as f:
    json.dump({"tiers": tiers, "overall": overall, "date_trends": date_trends}, f, indent=2)

print("\nSaved to tools/backtest3_soxx_stratified_results.json")