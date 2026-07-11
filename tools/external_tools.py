import os
import re
import json
import time
import asyncio
import threading
import yfinance as yf
from ddgs import DDGS
from tools.cache_utils import cached_tool, TTL_SLOW, TTL_FAST
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- Persistent background event loop for caching the Tavily MCP client ---
# Every tavily_search() call used to spin up a brand new MultiServerMCPClient
# and re-fetch the tool list from scratch. This runs one event loop forever
# in a background thread, so the client + tool list are created once and reused.

_loop = None
_loop_ready = threading.Event()
_mcp_tool = None
_mcp_init_lock = asyncio.Lock()


def _ensure_background_loop():
    global _loop
    if _loop is not None:
        return
    def run_loop():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop_ready.set()
        _loop.run_forever()
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    _loop_ready.wait()


async def _get_cached_tavily_tool():
    global _mcp_tool
    async with _mcp_init_lock:
        if _mcp_tool is not None:
            return _mcp_tool
        client = MultiServerMCPClient({
            "tavily": {
                "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
                "transport": "streamable_http",
            }
        })
        tools = await client.get_tools()
        _mcp_tool = next(t for t in tools if t.name == "tavily_search")
        return _mcp_tool


def ddgs_search(query: str, max_results: int = 5, retries: int = 3) -> str:
    """
    Robust search using ddgs news endpoint with retry logic.
    """
    for attempt in range(retries):
        try:
            with DDGS() as ddgs:
                results = ddgs.news(query, max_results=max_results)
                if results is None:
                    time.sleep(2)
                    continue
                results = list(results)
            if results:
                return " ".join([r['body'] for r in results if r.get('body')])[:800]
            time.sleep(2)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                return f"Search unavailable after {retries} attempts: {str(e)}"

    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if results is None:
                return "No results found."
            results = list(results)
        if results:
            return " ".join([r['body'] for r in results if r.get('body')])[:800]
    except Exception as e:
        return f"Search unavailable: {str(e)}"

    return "No results found."


async def _tavily_search_async(query: str, max_results: int = 5) -> str:
    search_tool = await _get_cached_tavily_tool()

    result = await search_tool.ainvoke({
        "query": query,
        "max_results": max_results
    })

    parsed = json.loads(result[0]["text"])
    contents = [r.get("content", "") for r in parsed.get("results", []) if r.get("content")]
    if not contents:
        raise ValueError("Tavily returned no usable content")

    combined = " ".join(contents)

    # Fix nested double-bracket links like [[Read more]](url "title")
    combined = combined.replace('[[', '[').replace(']]', ']')

    # Remove markdown images entirely: ![alt](url)
    combined = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', combined)

    # Remove bare parenthetical citation URLs with no [text]: (https://...)
    combined = re.sub(r'\(https?://[^\)]*\)', '', combined)

    # Remove markdown links (with or without a title): [text](url "title") -> text
    combined = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', combined)

    # Remove any remaining raw URLs
    combined = re.sub(r'https?://\S+', '', combined)

    # Remove leftover brackets and any stray/unmatched parentheses
    combined = re.sub(r'[\[\]]', '', combined)
    combined = re.sub(r'[()]', '', combined)

    # Collapse extra whitespace created by all the removals
    combined = re.sub(r'\s+', ' ', combined).strip()

    return combined[:1600]


def tavily_search(query: str, max_results: int = 5) -> str:
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set")
    _ensure_background_loop()
    future = asyncio.run_coroutine_threadsafe(_tavily_search_async(query, max_results), _loop)
    return future.result(timeout=30)


def web_search(query: str, max_results: int = 5, retries: int = 3) -> str:
    try:
        return tavily_search(query, max_results=max_results)
    except Exception as e:
        print(f"[TAVILY FALLBACK] {e}", flush=True)
        return ddgs_search(query, max_results=max_results, retries=retries)


def sentence_truncate(text: str, limit: int = 300) -> str:
    """Truncates at the nearest sentence boundary near `limit`, avoiding mid-sentence cuts."""
    text = str(text)
    if len(text) <= limit:
        return text
    window = text[:limit + 80]
    for punct in ['. ', '! ', '? ']:
        idx = window.rfind(punct, 0, limit + 80)
        if idx != -1 and idx > limit * 0.5:
            return window[:idx + 1].strip()
    return text[:limit].rsplit(' ', 1)[0].strip() + "..."

COMPETITOR_MAP = {
    # Memory
    "MU": ["SK Hynix", "Samsung"],
    "SNDK": ["Samsung", "Kioxia"],
    "000660.KS": ["Micron", "Samsung"],
    "005930.KS": ["SK Hynix", "Micron"],

    # GPU / CPU / AI compute
    "NVDA": ["AMD", "Intel"],
    "AMD": ["NVIDIA", "Intel"],
    "INTC": ["AMD", "TSMC"],
    "ARM": ["Intel", "RISC-V"],

    # Mobile / connectivity chips
    "QCOM": ["MediaTek", "Broadcom"],
    "AVGO": ["Qualcomm", "Marvell"],
    "MRVL": ["Broadcom", "Qualcomm"],
    "2454.TW": ["Qualcomm", "Broadcom"],

    # Semiconductor equipment
    "ASML": ["Applied Materials", "Lam Research"],
    "AMAT": ["Lam Research", "ASML"],
    "LRCX": ["Applied Materials", "ASML"],
    "KLAC": ["Onto Innovation", "Applied Materials"],
    "ONTO": ["KLA Corporation", "Applied Materials"],
    "ACMR": ["Lam Research", "Applied Materials"],
    "ICHR": ["Applied Materials", "Lam Research"],
    "MKSI": ["Applied Materials", "Advanced Energy"],
    "ACLS": ["Applied Materials", "Lam Research"],
    "ASMI.AS": ["Applied Materials", "Lam Research"],
    "BE.NA": ["Applied Materials", "ASM International"],
    "8035.T": ["Applied Materials", "Lam Research"],
    "6857.T": ["Teradyne", "Onto Innovation"],

    # Analog / mixed-signal
    "TXN": ["Analog Devices", "Microchip"],
    "ADI": ["Texas Instruments", "Microchip"],
    "MCHP": ["Texas Instruments", "Analog Devices"],
    "MPWR": ["Analog Devices", "Texas Instruments"],
    "SLAB": ["Microchip", "Texas Instruments"],
    "SMTC": ["Analog Devices", "Microchip"],
    "CRUS": ["Texas Instruments", "Analog Devices"],

    # RF / wireless
    "SWKS": ["Qorvo", "Qualcomm"],
    "QRVO": ["Skyworks", "Broadcom"],
    "MTSI": ["Skyworks", "Qorvo"],

    # Foundries
    "TSM": ["Samsung Foundry", "GlobalFoundries"],
    "2330.TW": ["Samsung Foundry", "GlobalFoundries"],
    "GFS": ["TSMC", "UMC"],
    "UMC": ["TSMC", "GlobalFoundries"],
    "2303.TW": ["TSMC", "GlobalFoundries"],

    # Power semiconductors
    "ON": ["Infineon", "STMicroelectronics"],
    "STM": ["Infineon", "ON Semiconductor"],
    "NXPI": ["Infineon", "Texas Instruments"],
    "WOLF": ["ON Semiconductor", "Infineon"],
    "ALGM": ["Infineon", "Texas Instruments"],
    "DIOD": ["ON Semiconductor", "Texas Instruments"],
    "NVTS": ["Infineon", "ON Semiconductor"],
    "POWI": ["Infineon", "ON Semiconductor"],
    "AOSL": ["ON Semiconductor", "Infineon"],
    "IFX.DE": ["STMicroelectronics", "ON Semiconductor"],

    # Niche / IP / specialty
    "ALAB": ["Marvell", "Broadcom"],
    "CEVA": ["Synopsys", "Arm"],
    "FORM": ["Onto Innovation", "KLA Corporation"],
    "RMBS": ["Synopsys", "CEVA"],
    "SITM": ["Skyworks", "Texas Instruments"],
    "AMBA": ["Qualcomm", "NVIDIA"],
    "AXTI": ["Sumitomo Electric", "Freiberger"],

    # Packaging / testing
    "3711.TW": ["Amkor Technology", "JCET"],
    "6723.T": ["NXP Semiconductors", "Infineon"],

    # Power supply / electronics
    "2308.TW": ["Eaton", "Vicor"],
}
DEFAULT_COMPETITORS = ["NVIDIA", "AMD"]


@tool
@cached_tool(TTL_FAST)
def get_geopolitics() -> str:
    """Searches for latest geopolitical signals affecting semiconductor supply chain."""
    try:
        result = web_search("semiconductor geopolitics Taiwan TSMC chip export ban 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search("semiconductor supply chain geopolitics risk")
        if not result or "unavailable" in result.lower():
            return "Geopolitics Signal: US-China chip tensions ongoing. Taiwan Strait risk elevated. Export controls on advanced semiconductors remain in force."
        return f"Geopolitics Signal: {result}"
    except Exception as e:
        return "Geopolitics Signal: US-China chip tensions ongoing. Taiwan Strait risk elevated. Export controls on advanced semiconductors remain in force."


@tool
@cached_tool(TTL_FAST)
def get_news_sentiment(ticker: str) -> str:
    """Searches for latest news sentiment around a given semiconductor ticker."""
    try:
        result = web_search(f"{ticker} semiconductor stock news analyst 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search(f"{ticker} semiconductor earnings forecast")
        if not result or "unavailable" in result.lower():
            return f"News Sentiment: No recent news available for {ticker}. Monitor earnings calendar."
        return f"News Sentiment: {result}"
    except Exception as e:
        return f"News Sentiment: Data temporarily unavailable for {ticker}."


@tool
@cached_tool(TTL_FAST)
def get_capital_rotation() -> str:
    """Searches for capital rotation signals between tech IPOs and semiconductors."""
    try:
        result = web_search("capital rotation semiconductor tech IPO investment 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search("semiconductor sector fund flows institutional 2025")
        if not result or "unavailable" in result.lower():
            return "Capital Rotation Signal: Institutional flows into AI/semiconductor sector remain elevated post-2024 AI boom."
        return f"Capital Rotation Signal: {result}"
    except Exception as e:
        return "Capital Rotation Signal: Data temporarily unavailable. Monitor SOX index flows."


@tool
@cached_tool(TTL_FAST)
def get_competitor_contagion(ticker: str) -> str:
    """Fetches recent earnings reactions from a company's actual competitors as contagion signals."""
    try:
        competitors = COMPETITOR_MAP.get(ticker.upper(), DEFAULT_COMPETITORS)
        results = []
        for comp in competitors[:2]:
            r = web_search(f"{comp} earnings revenue guidance 2025")
            if not r or "unavailable" in r.lower() or "No results" in r:
                r = web_search(f"{comp} stock quarterly results")
            r = r if r and "unavailable" not in r.lower() else f"{comp} data temporarily unavailable."
            results.append(f"{comp}: {sentence_truncate(r, 700)}")
        return "\n".join(results)
    except Exception as e:
        return "Competitor Contagion: Data temporarily unavailable."


@tool
@cached_tool(TTL_SLOW)
def get_beta(ticker: str) -> str:
    """Fetches beta coefficient as market volatility sensitivity signal."""
    try:
        stock = yf.Ticker(ticker)
        beta = stock.info.get('beta', 'N/A')
        if beta != 'N/A':
            volatility = 'High volatility' if beta > 1.5 else 'Moderate' if beta > 1 else 'Low volatility'
            return f"Beta: {beta} ({volatility})"
        return f"Beta: N/A for {ticker}"
    except Exception as e:
        return f"Beta: Data unavailable ({str(e)})"


@tool
@cached_tool(TTL_FAST)
def get_supply_chain(ticker: str) -> str:
    """Searches for supply chain signals for a semiconductor ticker."""
    try:
        result = web_search(f"{ticker} semiconductor supply chain TSMC ASML manufacturing 2025")
        if not result or "unavailable" in result.lower() or "No results" in result:
            result = web_search("semiconductor supply chain shortage TSMC 2025")
        if not result or "unavailable" in result.lower():
            return "Supply Chain: Global semiconductor supply chain remains constrained. TSMC capacity tight, ASML EUV tools in high demand. Lead times elevated across logic and memory."
        return f"Supply Chain: {result}"
    except Exception as e:
        return "Supply Chain: Global semiconductor supply chain remains constrained. TSMC capacity tight, ASML EUV tools in high demand."
