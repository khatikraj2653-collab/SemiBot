import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from graph.state import SemiconductorState
from tools.macro_tools import get_cpi, get_ppi, get_fed_rate, get_usd_index
from tools.fundamental_tools import get_pe_ratio, get_market_cap, get_earnings_guidance, get_insider_selling
from tools.market_tools import get_sector_rally, get_technical_signal, get_analyst_ratings, get_sell_the_news
from tools.external_tools import get_geopolitics, get_news_sentiment, get_capital_rotation, get_competitor_contagion, get_beta, get_supply_chain
from langchain_openai import ChatOpenAI

load_dotenv()


llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)

def resolve_ticker(user_input: str) -> str:
    """
    Converts company name or partial name to stock ticker.
    e.g. "Micron" → "MU", "nvidia" → "NVDA"
    """
    # Quick dictionary for common semiconductors
    quick_map = {
        "micron": "MU", "nvidia": "NVDA", "amd": "AMD",
        "intel": "INTC", "tsmc": "TSM", "asml": "ASML",
        "applied materials": "AMAT", "qualcomm": "QCOM",
        "broadcom": "AVGO", "texas instruments": "TXN",
        "sk hynix": "000660.KS", "samsung": "005930.KS",
        "arm": "ARM", "marvell": "MRVL", "on semiconductor": "ON",
        "microchip": "MCHP", "analog devices": "ADI",
        "lam research": "LRCX", "kla": "KLAC"
    }
    
    # Check dictionary first
    cleaned = user_input.lower().strip()
    for name, ticker in quick_map.items():
        if name in cleaned:
            return ticker
    
    # If already looks like a ticker (all caps, 1-5 chars) return as is
    if user_input.isupper() and len(user_input) <= 5:
        return user_input
    
    # Otherwise ask LLM
    try:
        response = llm.invoke(f"What is the stock ticker symbol for '{user_input}'? Reply with ONLY the ticker symbol, nothing else. Example: NVDA")
        ticker = response.content.strip().upper().replace(".", "").replace(" ", "")
        # Validate it looks like a ticker
        if len(ticker) <= 6 and ticker.isalpha():
            return ticker
    except:
        pass
    
    # Return uppercased input as fallback
    return user_input.upper()

def fetch_macro_factors(state: SemiconductorState) -> dict:
    """Fetches all 4 macroeconomic factors."""
    ticker = state["ticker"]
    return {
        "cpi": get_cpi.invoke({}),
        "ppi": get_ppi.invoke({}),
        "fed_rate": get_fed_rate.invoke({}),
        "usd_index": get_usd_index.invoke({})
    }

def fetch_fundamental_factors(state: SemiconductorState) -> dict:
    """Fetches all 4 fundamental factors."""
    ticker = state["ticker"]
    return {
        "pe_ratio": get_pe_ratio.invoke({"ticker": ticker}),
        "market_cap": get_market_cap.invoke({"ticker": ticker}),
        "earnings_guidance": get_earnings_guidance.invoke({"ticker": ticker}),
        "insider_selling": get_insider_selling.invoke({"ticker": ticker})
    }

def fetch_market_factors(state: SemiconductorState) -> dict:
    """Fetches all 4 market intelligence factors."""
    ticker = state["ticker"]
    return {
        "sector_rally": get_sector_rally.invoke({}),
        "technical_signal": get_technical_signal.invoke({"ticker": ticker}),
        "analyst_ratings": get_analyst_ratings.invoke({"ticker": ticker}),
        "sell_the_news": get_sell_the_news.invoke({"ticker": ticker})
    }

def fetch_external_factors(state: SemiconductorState) -> dict:
    """Fetches all 6 external signal factors."""
    ticker = state["ticker"]
    return {
        "geopolitics": get_geopolitics.invoke({}),
        "news_sentiment": get_news_sentiment.invoke({"ticker": ticker}),
        "capital_rotation": get_capital_rotation.invoke({}),
        "competitor_contagion": get_competitor_contagion.invoke({}),
        "beta": get_beta.invoke({"ticker": ticker}),
        "supply_chain": get_supply_chain.invoke({"ticker": ticker})
    }

# Factor weights — defined in Python, not LLM
FACTOR_WEIGHTS = {
    "geopolitics": 9,
    "supply_chain": 9,
    "fed_rate": 8,
    "competitor_contagion": 8,
    "cpi": 7,
    "sell_the_news": 7,
    "insider_selling": 7,
    "sector_rally": 6,
    "technical_signal": 6,
    "earnings_guidance": 6,
    "pe_ratio": 5,
    "analyst_ratings": 5,
    "news_sentiment": 5,
    "capital_rotation": 4,
    "ppi": 4,
    "market_cap": 3,
    "usd_index": 3,
    "beta": 2,
}

def calculate_probability(scores: dict) -> tuple:
    """
    Python calculates UP%/DOWN% mathematically from weighted scores.
    LLM never touches the probability number.
    """
    total_weight = sum(FACTOR_WEIGHTS.values())  # 100
    weighted_sum = sum(scores[k] * FACTOR_WEIGHTS[k] for k in scores)
    
    # weighted_sum range: -1000 to +1000
    # Normalize to 0-1
    normalized = (weighted_sum + 1000) / 2000
    
    # Clamp between 15% and 85% — markets always uncertain
    up_prob = max(15, min(85, round(normalized * 100)))
    down_prob = 100 - up_prob
    
    return up_prob, down_prob

def generate_prediction(state: SemiconductorState) -> dict:
    """
    Step 1: LLM scores each factor (-10 to +10)
    Step 2: Python calculates probability mathematically
    Step 3: LLM writes reasoning only
    """
    
    # Step 1 — Ask LLM to score each factor only
    scoring_prompt = ChatPromptTemplate.from_template("""
You are a semiconductor equity analyst. Score each factor from -10 (very bearish) to +10 (very bullish) for {ticker}.

FACTOR DATA:
CPI: {cpi}
PPI: {ppi}
Fed Rate: {fed_rate}
USD Index: {usd_index}
P/E Ratio: {pe_ratio}
Market Cap: {market_cap}
Earnings Guidance: {earnings_guidance}
Insider Selling: {insider_selling}
Sector Rally: {sector_rally}
Technical Signal: {technical_signal}
Analyst Ratings: {analyst_ratings}
Sell-the-News: {sell_the_news}
Geopolitics: {geopolitics}
Supply Chain: {supply_chain}
News Sentiment: {news_sentiment}
Capital Rotation: {capital_rotation}
Competitor Contagion: {competitor_contagion}
Beta: {beta}

Return ONLY this exact format, no other text:
CPI_SCORE: [integer -10 to 10]
PPI_SCORE: [integer -10 to 10]
FED_RATE_SCORE: [integer -10 to 10]
USD_INDEX_SCORE: [integer -10 to 10]
PE_RATIO_SCORE: [integer -10 to 10]
MARKET_CAP_SCORE: [integer -10 to 10]
EARNINGS_GUIDANCE_SCORE: [integer -10 to 10]
INSIDER_SELLING_SCORE: [integer -10 to 10]
SECTOR_RALLY_SCORE: [integer -10 to 10]
TECHNICAL_SIGNAL_SCORE: [integer -10 to 10]
ANALYST_RATINGS_SCORE: [integer -10 to 10]
SELL_THE_NEWS_SCORE: [integer -10 to 10]
GEOPOLITICS_SCORE: [integer -10 to 10]
SUPPLY_CHAIN_SCORE: [integer -10 to 10]
NEWS_SENTIMENT_SCORE: [integer -10 to 10]
CAPITAL_ROTATION_SCORE: [integer -10 to 10]
COMPETITOR_CONTAGION_SCORE: [integer -10 to 10]
BETA_SCORE: [integer -10 to 10]
""")

    scoring_chain = scoring_prompt | llm
    scoring_response = scoring_chain.invoke({
        "ticker": state["ticker"],
        "cpi": state["cpi"],
        "ppi": state["ppi"],
        "fed_rate": state["fed_rate"],
        "usd_index": state["usd_index"],
        "pe_ratio": state["pe_ratio"],
        "market_cap": state["market_cap"],
        "earnings_guidance": state["earnings_guidance"],
        "insider_selling": state["insider_selling"],
        "sector_rally": state["sector_rally"],
        "technical_signal": state["technical_signal"],
        "analyst_ratings": state["analyst_ratings"],
        "sell_the_news": state["sell_the_news"],
        "geopolitics": state["geopolitics"],
        "supply_chain": state["supply_chain"],
        "news_sentiment": state["news_sentiment"],
        "capital_rotation": state["capital_rotation"],
        "competitor_contagion": state["competitor_contagion"],
        "beta": state["beta"]
    })
    
    # Step 2 — Parse scores in Python
    scores = {}
    score_map = {
        "CPI_SCORE": "cpi",
        "PPI_SCORE": "ppi",
        "FED_RATE_SCORE": "fed_rate",
        "USD_INDEX_SCORE": "usd_index",
        "PE_RATIO_SCORE": "pe_ratio",
        "MARKET_CAP_SCORE": "market_cap",
        "EARNINGS_GUIDANCE_SCORE": "earnings_guidance",
        "INSIDER_SELLING_SCORE": "insider_selling",
        "SECTOR_RALLY_SCORE": "sector_rally",
        "TECHNICAL_SIGNAL_SCORE": "technical_signal",
        "ANALYST_RATINGS_SCORE": "analyst_ratings",
        "SELL_THE_NEWS_SCORE": "sell_the_news",
        "GEOPOLITICS_SCORE": "geopolitics",
        "SUPPLY_CHAIN_SCORE": "supply_chain",
        "NEWS_SENTIMENT_SCORE": "news_sentiment",
        "CAPITAL_ROTATION_SCORE": "capital_rotation",
        "COMPETITOR_CONTAGION_SCORE": "competitor_contagion",
        "BETA_SCORE": "beta"
    }
    
    for line in scoring_response.content.split("\n"):
        line = line.strip()
        for score_key, factor_key in score_map.items():
            if line.startswith(score_key + ":"):
                try:
                    scores[factor_key] = int(line.split(":")[-1].strip())
                except:
                    scores[factor_key] = 0
    
    # Fill missing scores with 0
    for key in FACTOR_WEIGHTS:
        if key not in scores:
            scores[key] = 0
    
    # Step 3 — Python calculates probability (no LLM involvement)
    up_prob, down_prob = calculate_probability(scores)
    
    # Step 4 — Ask LLM for reasoning only (not probability)
    reasoning_prompt = ChatPromptTemplate.from_template("""
You are a semiconductor equity analyst. Write a 2-3 sentence reasoning for why {ticker} stock 
scored UP {up_prob}% based on these factor scores:

{scores_text}

Identify the 3 most bullish and 3 most bearish factors (by weight × score).
Format EXACTLY like this:
BULLISH_FACTORS: [factor1] | [factor2] | [factor3]
BEARISH_FACTORS: [factor1] | [factor2] | [factor3]
REASONING: [2-3 sentences]
CONFIDENCE: [High/Medium/Low]
""")
    
    # Build scores text for reasoning
    scores_text = "\n".join([
        f"{k}: {scores[k]:+d} (weight {FACTOR_WEIGHTS[k]})" 
        for k in FACTOR_WEIGHTS
    ])
    
    reasoning_chain = reasoning_prompt | llm
    reasoning_response = reasoning_chain.invoke({
        "ticker": state["ticker"],
        "up_prob": up_prob,
        "scores_text": scores_text
    })
    
    # Step 5 — Assemble final prediction string
    final_prediction = f"""UP_PROBABILITY: {up_prob}%
DOWN_PROBABILITY: {down_prob}%
{reasoning_response.content}"""
    
    return {"prediction": final_prediction}