import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from graph.state import SemiconductorState
from tools.macro_tools import get_cpi, get_ppi, get_fed_rate, get_usd_index
from tools.fundamental_tools import get_pe_ratio, get_market_cap, get_earnings_guidance, get_insider_selling
from tools.market_tools import get_sector_rally, get_technical_signal, get_analyst_ratings, get_sell_the_news
from tools.external_tools import get_geopolitics, get_news_sentiment, get_capital_rotation, get_competitor_contagion, get_beta, get_supply_chain

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)


def resolve_ticker(user_input: str) -> str:
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
    cleaned = user_input.lower().strip()
    for name, ticker in quick_map.items():
        if name in cleaned:
            return ticker
    if user_input.isupper() and len(user_input) <= 5:
        return user_input
    try:
        response = llm.invoke(f"What is the stock ticker symbol for '{user_input}'? Reply with ONLY the ticker symbol, nothing else.")
        ticker = response.content.strip().upper().replace(".", "").replace(" ", "")
        if len(ticker) <= 6 and ticker.isalpha():
            return ticker
    except:
        pass
    return user_input.upper()

FACTOR_WEIGHTS = {
    "geopolitics": 9, "supply_chain": 9, "fed_rate": 8, "competitor_contagion": 8,
    "cpi": 7, "sell_the_news": 7, "insider_selling": 7, "sector_rally": 6,
    "technical_signal": 6, "earnings_guidance": 6, "pe_ratio": 5, "analyst_ratings": 5,
    "news_sentiment": 5, "capital_rotation": 3, "ppi": 3, "market_cap": 3,
    "usd_index": 2, "beta": 1,
}

def calculate_probability(scores: dict) -> tuple:
    weighted_sum = sum(scores[k] * FACTOR_WEIGHTS[k] for k in scores)
    normalized = (weighted_sum + 1000) / 2000
    up_prob = max(15, min(85, round(normalized * 100)))
    return up_prob, 100 - up_prob

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

reasoning_prompt = ChatPromptTemplate.from_template("""
You are a semiconductor equity analyst. Write a 2-3 sentence reasoning for why {ticker} stock
scored UP {up_prob}% based on these factor scores:

{scores_text}

Identify the 3 most bullish and 3 most bearish factors (by weight x score).
Format EXACTLY like this:
BULLISH_FACTORS: [factor1] | [factor2] | [factor3]
BEARISH_FACTORS: [factor1] | [factor2] | [factor3]
REASONING: [2-3 sentences]
CONFIDENCE: [High/Medium/Low]
""")

def generate_prediction(state: SemiconductorState) -> dict:
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
    score_map = {
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
    for line in scoring_response.content.split("\n"):
        line = line.strip()
        for score_key, factor_key in score_map.items():
            if line.startswith(score_key + ":"):
                try:
                    scores[factor_key] = int(line.split(":")[-1].strip())
                except:
                    scores[factor_key] = 0
    for key in FACTOR_WEIGHTS:
        if key not in scores:
            scores[key] = 0

    up_prob, down_prob = calculate_probability(scores)

    scores_text = "\n".join([f"{k}: {scores[k]:+d} (weight {FACTOR_WEIGHTS[k]})" for k in FACTOR_WEIGHTS])

    reasoning_response = (reasoning_prompt | llm).invoke({
        "ticker": state["ticker"],
        "up_prob": up_prob,
        "scores_text": scores_text
    })

    final_prediction = f"UP_PROBABILITY: {up_prob}%\nDOWN_PROBABILITY: {down_prob}%\n{reasoning_response.content}"

    return {"prediction": final_prediction, "scores": scores}