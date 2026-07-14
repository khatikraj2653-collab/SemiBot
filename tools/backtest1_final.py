"""
Backtest 1a and 1b: Incidental Development-Period Directional Consistency Check
Source: semibot_checkpoints.db (analysis_history table)

1a uses MA50 as the price-at-prediction-time proxy.
1b uses MA200 as the price-at-prediction-time proxy (sensitivity check).
Both compare against the SAME 151 stored predictions and the SAME current live prices.
"""
import sqlite3
import json
import re
import yfinance as yf
import time

import os
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'semibot_checkpoints.db')
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT id, ticker, timestamp, result_json FROM analysis_history ORDER BY id ASC")
rows = cursor.fetchall()

results_1a = []
results_1b = []
price_cache = {}

for row_id, ticker, timestamp, result_json in rows:
    try:
        data = json.loads(result_json)
        pred_text = data.get('prediction', '')

        up_match = re.search(r'UP_PROBABILITY:\s*(\d+)%', pred_text)
        down_match = re.search(r'DOWN_PROBABILITY:\s*(\d+)%', pred_text)
        if not up_match or not down_match:
            continue
        up_prob = int(up_match.group(1))
        down_prob = int(down_match.group(1))
        predicted_direction = "UP" if up_prob > down_prob else "DOWN"

        tech_signal = data.get('technical_signal', '')
        ma50_match = re.search(r'MA50:\s*([\d.]+)', tech_signal)
        ma200_match = re.search(r'MA200:\s*([\d.]+)', tech_signal)
        if not ma50_match or not ma200_match:
            continue
        ma50_price = float(ma50_match.group(1))
        ma200_price = float(ma200_match.group(1))

        if ticker not in price_cache:
            try:
                current_price = yf.Ticker(ticker).info.get('regularMarketPrice')
                price_cache[ticker] = current_price
                time.sleep(0.5)
            except Exception:
                price_cache[ticker] = None
        current_price = price_cache[ticker]
        if current_price is None:
            continue

        # --- 1a: MA50 proxy ---
        actual_direction_1a = "UP" if current_price > ma50_price else "DOWN"
        correct_1a = (predicted_direction == actual_direction_1a)
        results_1a.append({
            "id": row_id, "ticker": ticker, "predicted": predicted_direction,
            "proxy_price": ma50_price, "current_price": current_price,
            "actual_direction": actual_direction_1a, "correct": correct_1a
        })

        # --- 1b: MA200 proxy ---
        actual_direction_1b = "UP" if current_price > ma200_price else "DOWN"
        correct_1b = (predicted_direction == actual_direction_1b)
        results_1b.append({
            "id": row_id, "ticker": ticker, "predicted": predicted_direction,
            "proxy_price": ma200_price, "current_price": current_price,
            "actual_direction": actual_direction_1b, "correct": correct_1b
        })

    except Exception as e:
        print(f"Skipped row {row_id} ({ticker}): {e}")

conn.close()

total_1a = len(results_1a)
correct_1a_count = sum(1 for r in results_1a if r["correct"])
accuracy_1a = (correct_1a_count / total_1a * 100) if total_1a > 0 else 0

total_1b = len(results_1b)
correct_1b_count = sum(1 for r in results_1b if r["correct"])
accuracy_1b = (correct_1b_count / total_1b * 100) if total_1b > 0 else 0

print("\n" + "=" * 60)
print("BACKTEST 1a: Incidental Data, MA50 Proxy")
print("=" * 60)
print(f"Total valid predictions evaluated: {total_1a}")
print(f"Correct directional calls: {correct_1a_count}")
print(f"Directional accuracy: {accuracy_1a:.1f}%")

print("\n" + "=" * 60)
print("BACKTEST 1b: Incidental Data, MA200 Proxy (Sensitivity Check)")
print("=" * 60)
print(f"Total valid predictions evaluated: {total_1b}")
print(f"Correct directional calls: {correct_1b_count}")
print(f"Directional accuracy: {accuracy_1b:.1f}%")

print("\n" + "=" * 60)
print(f"SUMMARY: 1a (MA50) = {accuracy_1a:.1f}%  |  1b (MA200) = {accuracy_1b:.1f}%  |  Delta = {accuracy_1b - accuracy_1a:+.1f} pts")
print("=" * 60)

with open('backtest1a_results.json', 'w') as f:
    json.dump({"label": "Backtest 1a - MA50 proxy", "total": total_1a, "correct": correct_1a_count,
               "accuracy_pct": accuracy_1a, "details": results_1a}, f, indent=2)

with open('backtest1b_results.json', 'w') as f:
    json.dump({"label": "Backtest 1b - MA200 proxy", "total": total_1b, "correct": correct_1b_count,
               "accuracy_pct": accuracy_1b, "details": results_1b}, f, indent=2)

print("\nSaved to backtest1a_results.json and backtest1b_results.json")