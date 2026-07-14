"""
Backtest 2: Designed Fixed-Horizon Point-in-Time Experiment
48 tickers x 10 stratified dates, 20-trading-day forward return.
Reports overall accuracy PLUS stratified by market-cap tier (two table formats).
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from fredapi import Fred
from graph.nodes import scoring_prompt, llm, FACTOR_WEIGHTS, calculate_probability

fred = Fred(api_key=os.getenv("FRED_API_KEY"))

TICKERS = [
    "MU", "SNDK", "NVDA", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "ARM",
    "ASML", "AMAT", "LRCX", "KLAC", "ONTO", "ACMR", "MKSI",
    "TXN", "ADI", "MCHP", "MPWR", "SWKS", "QRVO", "SLAB", "SMTC",
    "TSM", "GFS", "UMC",
    "ON", "STM", "NXPI", "ALGM", "DIOD",
    "ALAB", "FORM", "RMBS",
    "CRUS", "SITM", "MTSI",
    "000660.KS", "005930.KS",
    "2308.TW", "2454.TW", "3711.TW",
    "6723.T", "6857.T", "8035.T", "285A.T",
    "IFX.DE"
]

DATES = [
    "2025-08-15", "2025-09-04", "2025-10-01", "2025-11-07", "2025-12-04",
    "2026-01-22", "2026-02-19", "2026-03-23", "2026-04-27", "2026-05-01"
]

FORWARD_DAYS = 20

FORCED_NEUTRAL_FACTORS = [
    "geopolitics", "supply_chain", "news_sentiment",
    "capital_rotation", "competitor_contagion", "sell_the_news"
]

SCORE_MAP = {
    "CPI_SCORE": "cpi", "PPI_SCORE": "ppi", "FED_RATE_SCORE": "fed_rate",
    "USD_INDEX_SCORE": "usd_index", "PE_RATIO_SCORE": "pe_ratio",
    "MARKET_CAP_SCORE": "market_cap", "EARNINGS_GUIDANCE_SCORE": "earnings_guidance",
    "INSIDER_SELLING_SCORE": "insider_selling", "SECTOR_RALLY_SCORE": "sector_rally",
    "TECHNICAL_SIGNAL_SCORE": "technical_signal", "ANALYST_RATINGS_SCORE": "analyst_ratings",
    "SELL_THE_NEWS_SCORE": "sell_the_news", "GEOPOLITICS_SCORE": "geopolitics",
    "SUPPLY_CHAIN_SCORE": "supply_chain", "NEWS_SENTIMENT_SCORE": "news_sentiment",
    "CAPITAL_ROTATION_SCORE": "capital_rotation", "COMPETITOR_CONTAGION_SCORE": "competitor_contagion",
    "BETA_SCORE": "beta"
}

# Approx FX-to-USD rates, for market-cap-bucketing purposes only (not precise financial conversion)
FX_TO_USD = {"USD": 1.0, "TWD": 0.031, "KRW": 0.00072, "JPY": 0.0068, "EUR": 1.08}

EARLIEST_DATE = pd.Timestamp(min(DATES)) - pd.Timedelta(days=420)
LATEST_DATE = pd.Timestamp(max(DATES)) + pd.Timedelta(days=45)

print("Fetching shared macro series (FRED)...")
cpi_series = fred.get_series('CPIAUCSL')
ppi_series = fred.get_series('PPIACO')
fedrate_series = fred.get_series('FEDFUNDS')

print("Fetching DXY history...")
dxy_hist = yf.Ticker("DX-Y.NYB").history(start=str(EARLIEST_DATE.date()), end=str(LATEST_DATE.date()))

print("Fetching SOXX history...")
soxx_hist = yf.Ticker("SOXX").history(start=str(EARLIEST_DATE.date()), end=str(LATEST_DATE.date()))

print("Fetching SPY history (for beta calc)...")
spy_hist = yf.Ticker("SPY").history(start=str(EARLIEST_DATE.date()), end=str(LATEST_DATE.date()))
spy_returns = spy_hist['Close'].pct_change()


def fred_value_asof(series, date):
    ts = pd.Timestamp(date)
    valid = series[series.index <= ts]
    if valid.empty:
        return None
    return float(valid.iloc[-1])


def price_asof(hist_df, date, tolerance_days=5):
    ts = pd.Timestamp(date)
    if hist_df.index.tz is not None:
        if ts.tz is None:
            ts = ts.tz_localize(hist_df.index.tz)
        else:
            ts = ts.tz_convert(hist_df.index.tz)
    valid = hist_df[hist_df.index <= ts]
    if valid.empty:
        return None, None
    if (ts - valid.index[-1]).days > tolerance_days:
        return None, None
    return float(valid['Close'].iloc[-1]), valid.index[-1]


def forward_price(hist_df, anchor_date, n_trading_days):
    ts = pd.Timestamp(anchor_date)
    if hist_df.index.tz is not None:
        if ts.tz is None:
            ts = ts.tz_localize(hist_df.index.tz)
        else:
            ts = ts.tz_convert(hist_df.index.tz)
    future = hist_df[hist_df.index > ts]
    if len(future) < n_trading_days:
        return None
    return float(future['Close'].iloc[n_trading_days - 1])


print("\nFetching per-ticker history + info...")
ticker_data = {}

for t in TICKERS:
    print(f"  {t}...")
    try:
        stock = yf.Ticker(t)
        hist = stock.history(start=str(EARLIEST_DATE.date()), end=str(LATEST_DATE.date()))
        if hist.empty:
            print(f"    WARNING: no price history for {t}, skipping ticker entirely")
            continue

        info = stock.info
        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
        trailing_pe = info.get('trailingPE')
        shares_out = info.get('sharesOutstanding')
        forward_eps = info.get('forwardEps', 'N/A')
        earnings_growth = info.get('earningsGrowth', 'N/A')
        rec_mean = info.get('recommendationMean', 'N/A')
        rec_key = info.get('recommendationKey', 'N/A')
        market_cap_raw = info.get('marketCap')
        currency = info.get('currency', 'USD')
        market_cap_usd = (market_cap_raw * FX_TO_USD.get(currency, 1.0)) if market_cap_raw else None

        implied_eps = None
        if current_price and trailing_pe and trailing_pe != 0:
            implied_eps = current_price / trailing_pe

        insider_text = "Insider Selling: No recent transactions found"
        try:
            insider = stock.insider_transactions
            if insider is not None and not insider.empty:
                recent = insider.head(3)
                lines = []
                for _, row in recent.iterrows():
                    name = row.get('Insider', 'Unknown')
                    shares = row.get('Shares', 'N/A')
                    value = row.get('Value', 'N/A')
                    text = row.get('Text', '')
                    if isinstance(value, (int, float)) and value == value:
                        value = f"${value:,.0f}"
                    else:
                        value = "Not disclosed"
                    lines.append(f"{name}: {text} | Shares: {shares} | Value: {value}")
                insider_text = "Recent Insider Transactions:\n" + "\n".join(lines)
        except Exception:
            pass

        ticker_data[t] = {
            "hist": hist, "current_price": current_price, "trailing_pe": trailing_pe,
            "shares_out": shares_out, "implied_eps": implied_eps, "forward_eps": forward_eps,
            "earnings_growth": earnings_growth, "rec_mean": rec_mean, "rec_key": rec_key,
            "insider_text": insider_text, "market_cap_usd": market_cap_usd,
        }
        time.sleep(0.3)
    except Exception as e:
        print(f"    ERROR fetching {t}: {e}")

print(f"\nSuccessfully loaded {len(ticker_data)}/{len(TICKERS)} tickers.\n")


def build_state(ticker, date):
    td = ticker_data[ticker]
    hist = td["hist"]

    hist_price, actual_date = price_asof(hist, date)
    if hist_price is None:
        return None, "no_price_at_date"

    cpi_val = fred_value_asof(cpi_series, date)
    ppi_val = fred_value_asof(ppi_series, date)
    fed_val = fred_value_asof(fedrate_series, date)
    dxy_val, _ = price_asof(dxy_hist, date)

    window = hist[hist.index <= actual_date]
    if len(window) < 200:
        return None, "insufficient_history_for_MA200"
    ma50 = window['Close'].rolling(50).mean().iloc[-1]
    ma200 = window['Close'].rolling(200).mean().iloc[-1]
    signal = "Golden Cross (Bullish)" if ma50 > ma200 else "Death Cross (Bearish)"
    technical_signal_str = f"MA50: {round(ma50,2)}, MA200: {round(ma200,2)}, Signal: {signal}"

    soxx_window = soxx_hist[soxx_hist.index <= actual_date]
    if len(soxx_window) < 22:
        sector_rally_str = "Sector Rally: Data unavailable (insufficient history)"
    else:
        month_ago_price = soxx_window['Close'].iloc[-22]
        latest_price = soxx_window['Close'].iloc[-1]
        change = ((latest_price - month_ago_price) / month_ago_price) * 100
        sector_rally_str = f"SOXX 1-month change: {round(change,2)}% ({'Bullish' if change > 0 else 'Bearish'})"

    stock_returns = window['Close'].pct_change()
    aligned = pd.concat([stock_returns.tail(252), spy_returns.reindex(stock_returns.tail(252).index)], axis=1).dropna()
    aligned.columns = ["stock", "spy"]
    if len(aligned) > 30 and aligned["spy"].var() > 0:
        beta_val = aligned["stock"].cov(aligned["spy"]) / aligned["spy"].var()
        volatility = 'High volatility' if beta_val > 1.5 else 'Moderate' if beta_val > 1 else 'Low volatility'
        beta_str = f"Beta: {round(beta_val,2)} ({volatility})"
    else:
        beta_str = "Beta: N/A (insufficient data)"

    if td["implied_eps"] and td["implied_eps"] != 0:
        hist_pe = hist_price / td["implied_eps"]
        pe_str = f"P/E Ratio: {round(hist_pe,2)} (implied, proxy method)"
    else:
        pe_str = "P/E Ratio: N/A"

    if td["shares_out"]:
        hist_mc = hist_price * td["shares_out"]
        mc_str = f"Market Cap: ${hist_mc:,.0f} (proxy: historical price x current shares out)"
    else:
        mc_str = "Market Cap: N/A"

    cpi_str = f"CPI: {round(cpi_val,2)}" if cpi_val else "CPI: N/A"
    ppi_str = f"PPI: {round(ppi_val,2)}" if ppi_val else "PPI: N/A"
    fed_str = f"Fed Rate: {round(fed_val,2)}%" if fed_val else "Fed Rate: N/A"
    dxy_str = f"USD Index (DXY): {round(dxy_val,2)}" if dxy_val else "USD Index: N/A"

    earnings_str = f"Forward EPS: {td['forward_eps']}, Earnings Growth: {td['earnings_growth']}"
    insider_str = td["insider_text"]
    analyst_str = f"Analyst Rating: {td['rec_key']} (mean score: {td['rec_mean']}/5)"

    neutral_note = "Historical data unavailable for backtesting - factor forced neutral."
    geo_str = f"Geopolitics Signal: {neutral_note}"
    supply_str = f"Supply Chain: {neutral_note}"
    news_str = f"News Sentiment: {neutral_note}"
    capital_str = f"Capital Rotation Signal: {neutral_note}"
    contagion_str = f"Competitor Contagion: {neutral_note}"
    selltn_str = f"Sell-the-News Signal: {neutral_note}"

    state = {
        "ticker": ticker,
        "cpi": cpi_str, "ppi": ppi_str, "fed_rate": fed_str, "usd_index": dxy_str,
        "pe_ratio": pe_str, "market_cap": mc_str,
        "earnings_guidance": earnings_str, "insider_selling": insider_str,
        "sector_rally": sector_rally_str, "technical_signal": technical_signal_str,
        "analyst_ratings": analyst_str,
        "sell_the_news": selltn_str, "geopolitics": geo_str, "supply_chain": supply_str,
        "news_sentiment": news_str, "capital_rotation": capital_str,
        "competitor_contagion": contagion_str, "beta": beta_str,
    }

    forward_close = forward_price(hist, actual_date, FORWARD_DAYS)
    if forward_close is None:
        return None, "insufficient_forward_data"

    actual_return_pct = ((forward_close - hist_price) / hist_price) * 100
    actual_direction = "UP" if actual_return_pct > 0 else "DOWN"

    return state, {
        "actual_date": str(actual_date.date()), "hist_price": round(hist_price, 2),
        "forward_close": round(forward_close, 2), "actual_return_pct": round(actual_return_pct, 2),
        "actual_direction": actual_direction,
    }


def score_and_predict(state):
    scoring_response = (scoring_prompt | llm).invoke({
        "ticker": state["ticker"], "cpi": state["cpi"], "ppi": state["ppi"],
        "fed_rate": state["fed_rate"], "usd_index": state["usd_index"],
        "pe_ratio": state["pe_ratio"], "market_cap": state["market_cap"],
        "earnings_guidance": state["earnings_guidance"], "insider_selling": state["insider_selling"],
        "sector_rally": state["sector_rally"], "technical_signal": state["technical_signal"],
        "analyst_ratings": state["analyst_ratings"], "sell_the_news": state["sell_the_news"],
        "geopolitics": state["geopolitics"], "supply_chain": state["supply_chain"],
        "news_sentiment": state["news_sentiment"], "capital_rotation": state["capital_rotation"],
        "competitor_contagion": state["competitor_contagion"], "beta": state["beta"]
    })

    scores = {}
    for line in scoring_response.content.split("\n"):
        line = line.strip()
        for score_key, factor_key in SCORE_MAP.items():
            if line.startswith(score_key + ":"):
                try:
                    scores[factor_key] = int(line.split(":")[-1].strip())
                except Exception:
                    scores[factor_key] = 0
    for key in FACTOR_WEIGHTS:
        if key not in scores:
            scores[key] = 0

    for key in FORCED_NEUTRAL_FACTORS:
        scores[key] = 0

    up_prob, down_prob = calculate_probability(scores)
    predicted_direction = "UP" if up_prob > down_prob else "DOWN"

    return scores, up_prob, down_prob, predicted_direction


def get_6tier(mcap_usd):
    if mcap_usd is None:
        return "Unknown"
    if mcap_usd > 1_000_000_000_000:
        return ">$1 Trillion"
    if mcap_usd > 500_000_000_000:
        return "$500B - $1T"
    if mcap_usd > 100_000_000_000:
        return "$100B - $500B"
    if mcap_usd > 50_000_000_000:
        return "$50B - $100B"
    if mcap_usd > 10_000_000_000:
        return "$10B - $50B"
    return "<$10B"


def get_5tier(mcap_usd):
    if mcap_usd is None:
        return "Unknown"
    if mcap_usd > 200_000_000_000:
        return "Mega-cap (>$200B)"
    if mcap_usd > 10_000_000_000:
        return "Large-cap ($10B-$200B)"
    if mcap_usd > 2_000_000_000:
        return "Mid-cap ($2B-$10B)"
    if mcap_usd > 300_000_000:
        return "Small-cap ($300M-$2B)"
    return "Micro-cap (<$300M)"


def main():
    results = []
    skipped = []
    total_combos = len(ticker_data) * len(DATES)
    done = 0

    for ticker in ticker_data:
        for date in DATES:
            done += 1
            state, meta = build_state(ticker, date)
            if state is None:
                skipped.append({"ticker": ticker, "date": date, "reason": meta})
                print(f"[{done}/{total_combos}] SKIP {ticker} {date}: {meta}")
                continue

            try:
                scores, up_prob, down_prob, predicted_direction = score_and_predict(state)
            except Exception as e:
                skipped.append({"ticker": ticker, "date": date, "reason": f"llm_error: {e}"})
                print(f"[{done}/{total_combos}] SKIP {ticker} {date}: LLM error {e}")
                continue

            if up_prob == 50:
                skipped.append({"ticker": ticker, "date": date, "reason": "tie_50_50"})
                print(f"[{done}/{total_combos}] SKIP {ticker} {date}: 50/50 tie")
                continue

            correct = predicted_direction == meta["actual_direction"]
            results.append({
                "ticker": ticker, "date": date, "analysis_anchor_date": meta["actual_date"],
                "predicted_direction": predicted_direction, "up_prob": up_prob,
                "actual_direction": meta["actual_direction"],
                "actual_return_pct": meta["actual_return_pct"],
                "correct": correct,
                "market_cap_usd": ticker_data[ticker]["market_cap_usd"],
            })
            status = "CORRECT" if correct else "WRONG"
            print(f"[{done}/{total_combos}] {status} {ticker:10s} {date}  pred={predicted_direction:4s} "
                  f"up_prob={up_prob}%  actual={meta['actual_direction']:4s} ({meta['actual_return_pct']:+.1f}%)")
            time.sleep(0.2)

    total = len(results)
    correct_count = sum(1 for r in results if r["correct"])
    accuracy = (correct_count / total * 100) if total else 0

    print("\n" + "=" * 70)
    print("BACKTEST 2: OVERALL RESULTS (48 tickers x 10 dates, fixed 20-trading-day forward window)")
    print("=" * 70)
    print(f"Total combos attempted: {total_combos}")
    print(f"Valid predictions: {total}")
    print(f"Correct: {correct_count}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"Skipped: {len(skipped)}")

    per_ticker = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        per_ticker[r["ticker"]]["total"] += 1
        if r["correct"]:
            per_ticker[r["ticker"]]["correct"] += 1

    print("\n" + "=" * 70)
    print("PER-TICKER ACCURACY")
    print("=" * 70)
    for t, v in sorted(per_ticker.items(), key=lambda x: -x[1]["correct"]/x[1]["total"] if x[1]["total"] > 0 else 0):
        acc = v["correct"] / v["total"] * 100
        print(f"{t:12s} {v['correct']}/{v['total']} ({acc:.0f}%)")

    # --- 6-Tier Valuation Table ---
    tier6 = defaultdict(lambda: {"correct": 0, "total": 0, "tickers": set()})
    tier5 = defaultdict(lambda: {"correct": 0, "total": 0, "tickers": set()})
    for r in results:
        t6 = get_6tier(r["market_cap_usd"])
        t5 = get_5tier(r["market_cap_usd"])
        tier6[t6]["total"] += 1
        tier6[t6]["tickers"].add(r["ticker"])
        if r["correct"]:
            tier6[t6]["correct"] += 1
        tier5[t5]["total"] += 1
        tier5[t5]["tickers"].add(r["ticker"])
        if r["correct"]:
            tier5[t5]["correct"] += 1

    tier6_order = [">$1 Trillion", "$500B - $1T", "$100B - $500B", "$50B - $100B", "$10B - $50B", "<$10B", "Unknown"]
    tier5_order = ["Mega-cap (>$200B)", "Large-cap ($10B-$200B)", "Mid-cap ($2B-$10B)", "Small-cap ($300M-$2B)", "Micro-cap (<$300M)", "Unknown"]

    print("\n" + "=" * 70)
    print("TABLE 1: ANALYSIS BY VALUATION RANGE (6-Tier)")
    print("=" * 70)
    print(f"{'Valuation Range':<18} {'Companies':<12} {'N (valid)':<12} {'Correct':<10} {'Accuracy'}")
    for tier in tier6_order:
        if tier not in tier6:
            continue
        v = tier6[tier]
        acc = (v["correct"] / v["total"] * 100) if v["total"] > 0 else 0
        print(f"{tier:<18} {len(v['tickers']):<12} {v['total']:<12} {v['correct']:<10} {acc:.1f}%")
    print(f"{'TOTAL':<18} {len(ticker_data):<12} {total:<12} {correct_count:<10} {accuracy:.1f}%")

    print("\n" + "=" * 70)
    print("TABLE 2: ANALYSIS BY MARKET CAP (5-Tier Standard Classification)")
    print("=" * 70)
    print(f"{'Cap Tier':<25} {'# Companies':<14} {'N (valid)':<12} {'Correct':<10} {'Accuracy'}")
    for tier in tier5_order:
        if tier not in tier5:
            continue
        v = tier5[tier]
        acc = (v["correct"] / v["total"] * 100) if v["total"] > 0 else 0
        print(f"{tier:<25} {len(v['tickers']):<14} {v['total']:<12} {v['correct']:<10} {acc:.1f}%")
    print(f"{'TOTAL':<25} {len(ticker_data):<14} {total:<12} {correct_count:<10} {accuracy:.1f}%")

    output = {
        "config": {"tickers": TICKERS, "dates": DATES, "forward_trading_days": FORWARD_DAYS},
        "summary": {"total_combos": total_combos, "valid": total, "correct": correct_count,
                    "accuracy_pct": round(accuracy, 1), "skipped_count": len(skipped)},
        "results": results, "skipped": skipped,
        "tier6_table": {k: {"companies": len(v["tickers"]), "total": v["total"], "correct": v["correct"]} for k, v in tier6.items()},
        "tier5_table": {k: {"companies": len(v["tickers"]), "total": v["total"], "correct": v["correct"]} for k, v in tier5.items()},
    }

    with open("backtest2_final_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nSaved to tools/backtest2_final_results.json")


if __name__ == "__main__":
    main()