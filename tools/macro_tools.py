import os
from langchain_core.tools import tool
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
fred = Fred(api_key=os.getenv("FRED_API_KEY"))

from tools.cache_utils import cached_tool, TTL_SLOW
@tool
@cached_tool(TTL_SLOW)
def get_cpi() -> str:
    """Fetches latest CPI value from FRED as inflation signal."""
    try:
        cpi = fred.get_series('CPIAUCSL').iloc[-1]
        return f"CPI: {round(float(cpi), 2)}"
    except Exception as e:
        return f"CPI: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_ppi() -> str:
    """Fetches latest PPI value from FRED as producer cost signal."""
    try:
        ppi = fred.get_series('PPIACO').iloc[-1]
        return f"PPI: {round(float(ppi), 2)}"
    except Exception as e:
        return f"PPI: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_fed_rate() -> str:
    """Fetches current Federal Funds Rate from FRED."""
    try:
        rate = fred.get_series('FEDFUNDS').iloc[-1]
        return f"Fed Rate: {round(float(rate), 2)}%"
    except Exception as e:
        return f"Fed Rate: Data unavailable ({str(e)})"

@tool
@cached_tool(TTL_SLOW)
def get_usd_index() -> str:
    """Fetches current USD Index (DXY) value as dollar strength signal.
    Tries yfinance .info first; on rate-limit or missing value, falls
    back to the last daily close via .history(), then to FRED's broad
    USD index (DTWEXBGS) so the signal never silently 404s."""
    import yfinance as yf

    # 1) Try yfinance .info (live price)
    try:
        dxy = yf.Ticker("DX-Y.NYB")
        price = dxy.info.get('regularMarketPrice')
        if isinstance(price, (int, float)) and price > 0:
            return f"USD Index (DXY): {round(price, 2)}"
    except Exception:
        pass

    # 2) Fallback: last close from 5d history (cheaper than .info)
    try:
        hist = yf.Ticker("DX-Y.NYB").history(period="5d")
        if hist is not None and not hist.empty:
            last = float(hist['Close'].dropna().iloc[-1])
            return f"USD Index (DXY): {round(last, 2)} (last close)"
    except Exception:
        pass

    # 3) FRED trade-weighted USD index as last resort
    try:
        val = fred.get_series('DTWEXBGS').dropna().iloc[-1]
        return f"USD Index (FRED trade-weighted): {round(float(val), 2)}"
    except Exception as e:
        return f"USD Index: Data unavailable ({str(e)})"
