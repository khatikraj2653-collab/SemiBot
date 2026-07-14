import json
import numpy as np
import statsmodels.api as sm
import pandas as pd
from collections import defaultdict

with open("backtest2_final_results.json") as f:
    data = json.load(f)

results = data["results"]
valid = [r for r in results if r.get("market_cap_usd") is not None]

# --- Category mapping for all 48 tickers ---
CATEGORY_MAP = {
    "MU": "Memory", "SNDK": "Memory",
    "NVDA": "Fabless", "AMD": "Fabless", "INTC": "Fabless", "QCOM": "Fabless",
    "AVGO": "Fabless", "MRVL": "Fabless", "ARM": "Fabless",
    "ASML": "Equipment", "AMAT": "Equipment", "LRCX": "Equipment", "KLAC": "Equipment",
    "ONTO": "Equipment", "ACMR": "Equipment", "MKSI": "Equipment",
    "TXN": "Analog", "ADI": "Analog", "MCHP": "Analog", "MPWR": "Analog",
    "SWKS": "Analog", "QRVO": "Analog", "SLAB": "Analog", "SMTC": "Analog",
    "TSM": "Foundry", "GFS": "Foundry", "UMC": "Foundry",
    "ON": "Diversified", "STM": "Diversified", "NXPI": "Diversified",
    "ALGM": "Diversified", "DIOD": "Diversified",
    "ALAB": "Emerging", "FORM": "Emerging", "RMBS": "Emerging",
    "CRUS": "Consumer", "SITM": "Consumer", "MTSI": "Consumer",
    "000660.KS": "International", "005930.KS": "International",
    "2308.TW": "International", "2454.TW": "International", "3711.TW": "International",
    "6723.T": "International", "6857.T": "International", "8035.T": "International",
    "285A.T": "International", "IFX.DE": "International",
}

# ============================================================
# ITEM 4: Sector-controlled logistic regression
# ============================================================
print("=" * 70)
print("ITEM 4: LOGISTIC REGRESSION WITH SECTOR/CATEGORY CONTROL")
print("=" * 70)

df = pd.DataFrame(valid)
df["category"] = df["ticker"].map(CATEGORY_MAP)
df["log_mcap"] = np.log(df["market_cap_usd"])
df["correct_bin"] = df["correct"].astype(int)

# Build category dummies (drop first as reference category)
cat_dummies = pd.get_dummies(df["category"], drop_first=True, dtype=float)
X = pd.concat([df["log_mcap"], cat_dummies], axis=1)
X = sm.add_constant(X)
y = df["correct_bin"]

model = sm.Logit(y, X).fit(disp=0)
print(model.summary())

log_mcap_beta = model.params["log_mcap"]
log_mcap_p = model.pvalues["log_mcap"]

print(f"\nlog(market_cap) coefficient AFTER controlling for category: {log_mcap_beta:.4f}")
print(f"P-value: {log_mcap_p:.6f}")
print(f"Reference category (dropped): {sorted(df['category'].unique())[0]}")

if log_mcap_p < 0.05:
    print("\n--> Market cap effect REMAINS SIGNIFICANT after controlling for sector/category.")
else:
    print("\n--> Market cap effect is NOT significant after controlling for category")
    print("    (suggests the effect may be partly/fully explained by sector composition).")

# ============================================================
# ITEM 5: Bull-market confound check (strongest vs weakest dates)
# ============================================================
print("\n" + "=" * 70)
print("ITEM 5: MARKET-CAP GRADIENT WITHIN STRONGEST vs WEAKEST DATES")
print("=" * 70)

by_date = defaultdict(lambda: {"correct": 0, "total": 0})
for r in valid:
    by_date[r["date"]]["total"] += 1
    if r["correct"]:
        by_date[r["date"]]["correct"] += 1

date_accuracy = {d: v["correct"] / v["total"] * 100 for d, v in by_date.items()}
sorted_dates = sorted(date_accuracy.items(), key=lambda x: x[1])

print("\nOverall accuracy by date (ascending):")
for d, acc in sorted_dates:
    print(f"  {d}: {acc:.1f}% (n={by_date[d]['total']})")

weakest_3 = [d for d, _ in sorted_dates[:3]]
strongest_3 = [d for d, _ in sorted_dates[-3:]]

print(f"\nWeakest 3 dates (overall): {weakest_3}")
print(f"Strongest 3 dates (overall): {strongest_3}")


def megamid_gap(date_list, label):
    subset = [r for r in valid if r["date"] in date_list]
    mega = [r for r in subset if r["market_cap_usd"] > 200_000_000_000]
    mid = [r for r in subset if 2_000_000_000 < r["market_cap_usd"] <= 10_000_000_000]
    mega_acc = sum(1 for r in mega if r["correct"]) / len(mega) * 100 if mega else None
    mid_acc = sum(1 for r in mid if r["correct"]) / len(mid) * 100 if mid else None
    print(f"\n{label}:")
    print(f"  Mega-cap: {sum(1 for r in mega if r['correct'])}/{len(mega)} = {mega_acc:.1f}%" if mega_acc is not None else "  Mega-cap: no data")
    print(f"  Mid-cap:  {sum(1 for r in mid if r['correct'])}/{len(mid)} = {mid_acc:.1f}%" if mid_acc is not None else "  Mid-cap: no data")
    if mega_acc is not None and mid_acc is not None:
        print(f"  Gap: {mega_acc - mid_acc:+.1f} pts")
    return mega_acc, mid_acc


weak_mega, weak_mid = megamid_gap(weakest_3, "On the 3 WEAKEST-performing dates overall")
strong_mega, strong_mid = megamid_gap(strongest_3, "On the 3 STRONGEST-performing dates overall")

print("\n--> Interpretation:")
if weak_mega is not None and weak_mid is not None:
    if weak_mega > weak_mid:
        print("    Mega-cap advantage PERSISTS even on the market's weakest days in this sample,")
        print("    providing partial evidence the effect is not purely a bull-market artifact.")
    else:
        print("    Mega-cap advantage did NOT clearly persist on the weakest days")
        print("    (small subsample - interpret cautiously).")

with open("stats_items45_results.json", "w") as f:
    json.dump({
        "item4_sector_controlled": {
            "log_mcap_beta": float(log_mcap_beta),
            "log_mcap_pvalue": float(log_mcap_p),
        },
        "item5_date_subsets": {
            "weakest_3_dates": weakest_3,
            "strongest_3_dates": strongest_3,
            "weakest_mega_acc": weak_mega,
            "weakest_mid_acc": weak_mid,
            "strongest_mega_acc": strong_mega,
            "strongest_mid_acc": strong_mid,
        }
    }, f, indent=2)

print("\nSaved to stats_items45_results.json")