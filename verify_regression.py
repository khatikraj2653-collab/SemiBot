import json
import numpy as np
import statsmodels.api as sm
import pandas as pd

with open("tools/backtest2_final_results.json") as f:
    data = json.load(f)

results = data["results"]
df = pd.DataFrame(results)
df["log_market_cap"] = np.log(df["market_cap_usd"])
df["correct_int"] = df["correct"].astype(int)

X = sm.add_constant(df["log_market_cap"])
y = df["correct_int"]

model = sm.Logit(y, X).fit(disp=0)
print(model.summary())

print("\n--- Key coefficient ---")
print(f"log_market_cap coefficient: {model.params['log_market_cap']:.4f}")
print(f"Standard error: {model.bse['log_market_cap']:.4f}")
print(f"z-value: {model.tvalues['log_market_cap']:.4f}")
print(f"p-value: {model.pvalues['log_market_cap']:.2e}")
print(f"Odds ratio: {np.exp(model.params['log_market_cap']):.4f}")

# LR test p-value
llf_full = model.llf
null_model = sm.Logit(y, sm.add_constant(pd.Series(np.ones(len(y)), name="const"))).fit(disp=0)
from scipy.stats import chi2
lr_stat = 2 * (llf_full - null_model.llf)
lr_p = chi2.sf(lr_stat, df=1)
print(f"Likelihood-ratio p-value: {lr_p:.2e}")
