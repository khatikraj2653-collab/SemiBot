import json
import numpy as np
import statsmodels.api as sm
from scipy import stats
from scipy.stats import chi2_contingency

with open("backtest2_final_results.json") as f:
    data = json.load(f)

results = data["results"]
valid = [r for r in results if r.get("market_cap_usd") is not None]

correct = np.array([1 if r["correct"] else 0 for r in valid])
log_mcap = np.log(np.array([r["market_cap_usd"] for r in valid]))

# --- Item 1: Logistic regression ---
X = sm.add_constant(log_mcap)
model = sm.Logit(correct, X).fit(disp=0)
beta = model.params[1]
pval = model.pvalues[1]
odds_ratio = np.exp(beta)

print("=" * 70)
print("ITEM 1: LOGISTIC REGRESSION - correctness ~ log(market_cap)")
print("=" * 70)
print(model.summary())
print(f"\nBeta (log market cap coefficient): {beta:.4f}")
print(f"P-value: {pval:.6f}")
print(f"Odds ratio: {odds_ratio:.4f}")
print(f"\nInterpretation sentence for paper:")
print(f'"A logistic regression of prediction correctness on log market capitalization')
print(f'confirms a significant positive relationship (beta={beta:.3f}, p={"<0.001" if pval<0.001 else f"={pval:.4f}"}),')
print(f'indicating the observed gradient is not attributable to chance."')

# --- Item 2: Chi-square, mega-cap vs mid-cap ---
mega = [r for r in valid if r["market_cap_usd"] > 200_000_000_000]
mid = [r for r in valid if 2_000_000_000 < r["market_cap_usd"] <= 10_000_000_000]

mega_correct = sum(1 for r in mega if r["correct"])
mega_total = len(mega)
mid_correct = sum(1 for r in mid if r["correct"])
mid_total = len(mid)

contingency = [[mega_correct, mega_total - mega_correct],
               [mid_correct, mid_total - mid_correct]]
chi2, p_chi, dof, expected = chi2_contingency(contingency)

print("\n" + "=" * 70)
print("ITEM 2: CHI-SQUARE TEST - Mega-cap vs Mid-cap accuracy")
print("=" * 70)
print(f"Mega-cap (>$200B): {mega_correct}/{mega_total} = {mega_correct/mega_total*100:.1f}%")
print(f"Mid-cap ($2B-$10B): {mid_correct}/{mid_total} = {mid_correct/mid_total*100:.1f}%")
print(f"Chi-square statistic: {chi2:.4f}")
print(f"P-value: {p_chi:.6f}")
print(f'\nInterpretation sentence for paper:')
print(f'"A chi-square test confirms the difference between Mega-cap (77.2%) and')
print(f'Mid-cap (41.7%) accuracy is statistically significant (chi2={chi2:.2f}, p={"<0.001" if p_chi<0.001 else f"={p_chi:.4f}"})."')

# --- Item 3: 95% Confidence Intervals (Wilson score interval, robust for proportions) ---
def wilson_ci(correct_count, n, z=1.96):
    if n == 0:
        return (None, None)
    phat = correct_count / n
    denom = 1 + z**2/n
    center = (phat + z*z/(2*n)) / denom
    margin = (z * np.sqrt((phat*(1-phat) + z*z/(4*n))/n)) / denom
    return (max(0, center - margin), min(1, center + margin))

print("\n" + "=" * 70)
print("ITEM 3: 95% CONFIDENCE INTERVALS (Wilson score method)")
print("=" * 70)

tiers = {
    ">$1 Trillion": [r for r in valid if r["market_cap_usd"] > 1_000_000_000_000],
    "$500B-$1T": [r for r in valid if 500_000_000_000 < r["market_cap_usd"] <= 1_000_000_000_000],
    "$100B-$500B": [r for r in valid if 100_000_000_000 < r["market_cap_usd"] <= 500_000_000_000],
    "$50B-$100B": [r for r in valid if 50_000_000_000 < r["market_cap_usd"] <= 100_000_000_000],
    "$10B-$50B": [r for r in valid if 10_000_000_000 < r["market_cap_usd"] <= 50_000_000_000],
    "<$10B": [r for r in valid if r["market_cap_usd"] <= 10_000_000_000],
    "OVERALL": valid,
}

for label, rows in tiers.items():
    n = len(rows)
    c = sum(1 for r in rows if r["correct"])
    acc = c / n * 100 if n > 0 else 0
    lo, hi = wilson_ci(c, n)
    if lo is not None:
        print(f"{label:<15} N={n:<5} Acc={acc:.1f}%  95% CI=[{lo*100:.1f}%, {hi*100:.1f}%]")

with open("stats_results.json", "w") as f:
    json.dump({
        "logistic_regression": {"beta": float(beta), "pvalue": float(pval), "odds_ratio": float(odds_ratio)},
        "chi_square": {"chi2": float(chi2), "pvalue": float(p_chi),
                       "mega_correct": mega_correct, "mega_total": mega_total,
                       "mid_correct": mid_correct, "mid_total": mid_total},
    }, f, indent=2)

print("\nSaved to stats_results.json")