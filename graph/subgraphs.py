from langgraph.graph import StateGraph, START, END
from graph.state import SemiconductorState
from tools.macro_tools import get_cpi, get_ppi, get_fed_rate, get_usd_index
from tools.fundamental_tools import get_pe_ratio, get_market_cap, get_earnings_guidance, get_insider_selling
from tools.market_tools import get_sector_rally, get_technical_signal, get_analyst_ratings, get_sell_the_news
from tools.external_tools import get_geopolitics, get_news_sentiment, get_capital_rotation, get_competitor_contagion, get_beta, get_supply_chain


def fetch_cpi_node(state: SemiconductorState) -> dict:
    return {"cpi": get_cpi.invoke({})}

def fetch_ppi_node(state: SemiconductorState) -> dict:
    return {"ppi": get_ppi.invoke({})}

def fetch_fed_rate_node(state: SemiconductorState) -> dict:
    return {"fed_rate": get_fed_rate.invoke({})}

def fetch_usd_index_node(state: SemiconductorState) -> dict:
    return {"usd_index": get_usd_index.invoke({})}


def build_macro_subgraph():
    subgraph = StateGraph(SemiconductorState)
    subgraph.add_node("fetch_cpi", fetch_cpi_node)
    subgraph.add_node("fetch_ppi", fetch_ppi_node)
    subgraph.add_node("fetch_fed_rate", fetch_fed_rate_node)
    subgraph.add_node("fetch_usd_index", fetch_usd_index_node)

    subgraph.add_edge(START, "fetch_cpi")
    subgraph.add_edge(START, "fetch_ppi")
    subgraph.add_edge(START, "fetch_fed_rate")
    subgraph.add_edge(START, "fetch_usd_index")
    subgraph.add_edge("fetch_cpi", END)
    subgraph.add_edge("fetch_ppi", END)
    subgraph.add_edge("fetch_fed_rate", END)
    subgraph.add_edge("fetch_usd_index", END)

    return subgraph.compile()


def fetch_pe_ratio_node(state: SemiconductorState) -> dict:
    return {"pe_ratio": get_pe_ratio.invoke({"ticker": state["ticker"]})}

def fetch_market_cap_node(state: SemiconductorState) -> dict:
    return {"market_cap": get_market_cap.invoke({"ticker": state["ticker"]})}

def fetch_earnings_guidance_node(state: SemiconductorState) -> dict:
    return {"earnings_guidance": get_earnings_guidance.invoke({"ticker": state["ticker"]})}

def fetch_insider_selling_node(state: SemiconductorState) -> dict:
    return {"insider_selling": get_insider_selling.invoke({"ticker": state["ticker"]})}


def build_fundamental_subgraph():
    subgraph = StateGraph(SemiconductorState)
    subgraph.add_node("fetch_pe_ratio", fetch_pe_ratio_node)
    subgraph.add_node("fetch_market_cap", fetch_market_cap_node)
    subgraph.add_node("fetch_earnings_guidance", fetch_earnings_guidance_node)
    subgraph.add_node("fetch_insider_selling", fetch_insider_selling_node)

    subgraph.add_edge(START, "fetch_pe_ratio")
    subgraph.add_edge(START, "fetch_market_cap")
    subgraph.add_edge(START, "fetch_earnings_guidance")
    subgraph.add_edge(START, "fetch_insider_selling")
    subgraph.add_edge("fetch_pe_ratio", END)
    subgraph.add_edge("fetch_market_cap", END)
    subgraph.add_edge("fetch_earnings_guidance", END)
    subgraph.add_edge("fetch_insider_selling", END)

    return subgraph.compile()


def fetch_sector_rally_node(state: SemiconductorState) -> dict:
    return {"sector_rally": get_sector_rally.invoke({})}

def fetch_technical_signal_node(state: SemiconductorState) -> dict:
    return {"technical_signal": get_technical_signal.invoke({"ticker": state["ticker"]})}

def fetch_analyst_ratings_node(state: SemiconductorState) -> dict:
    return {"analyst_ratings": get_analyst_ratings.invoke({"ticker": state["ticker"]})}

def fetch_sell_the_news_node(state: SemiconductorState) -> dict:
    return {"sell_the_news": get_sell_the_news.invoke({"ticker": state["ticker"]})}


def build_market_subgraph():
    subgraph = StateGraph(SemiconductorState)
    subgraph.add_node("fetch_sector_rally", fetch_sector_rally_node)
    subgraph.add_node("fetch_technical_signal", fetch_technical_signal_node)
    subgraph.add_node("fetch_analyst_ratings", fetch_analyst_ratings_node)
    subgraph.add_node("fetch_sell_the_news", fetch_sell_the_news_node)

    subgraph.add_edge(START, "fetch_sector_rally")
    subgraph.add_edge(START, "fetch_technical_signal")
    subgraph.add_edge(START, "fetch_analyst_ratings")
    subgraph.add_edge(START, "fetch_sell_the_news")
    subgraph.add_edge("fetch_sector_rally", END)
    subgraph.add_edge("fetch_technical_signal", END)
    subgraph.add_edge("fetch_analyst_ratings", END)
    subgraph.add_edge("fetch_sell_the_news", END)

    return subgraph.compile()


def fetch_geopolitics_node(state: SemiconductorState) -> dict:
    return {"geopolitics": get_geopolitics.invoke({})}

def fetch_news_sentiment_node(state: SemiconductorState) -> dict:
    return {"news_sentiment": get_news_sentiment.invoke({"ticker": state["ticker"]})}

def fetch_capital_rotation_node(state: SemiconductorState) -> dict:
    return {"capital_rotation": get_capital_rotation.invoke({})}

def fetch_competitor_contagion_node(state: SemiconductorState) -> dict:
    return {"competitor_contagion": get_competitor_contagion.invoke({"ticker": state["ticker"]})}

def fetch_beta_node(state: SemiconductorState) -> dict:
    return {"beta": get_beta.invoke({"ticker": state["ticker"]})}

def fetch_supply_chain_node(state: SemiconductorState) -> dict:
    return {"supply_chain": get_supply_chain.invoke({"ticker": state["ticker"]})}


def build_external_subgraph():
    subgraph = StateGraph(SemiconductorState)
    subgraph.add_node("fetch_geopolitics", fetch_geopolitics_node)
    subgraph.add_node("fetch_news_sentiment", fetch_news_sentiment_node)
    subgraph.add_node("fetch_capital_rotation", fetch_capital_rotation_node)
    subgraph.add_node("fetch_competitor_contagion", fetch_competitor_contagion_node)
    subgraph.add_node("fetch_beta", fetch_beta_node)
    subgraph.add_node("fetch_supply_chain", fetch_supply_chain_node)

    subgraph.add_edge(START, "fetch_geopolitics")
    subgraph.add_edge(START, "fetch_news_sentiment")
    subgraph.add_edge(START, "fetch_capital_rotation")
    subgraph.add_edge(START, "fetch_competitor_contagion")
    subgraph.add_edge(START, "fetch_beta")
    subgraph.add_edge(START, "fetch_supply_chain")
    subgraph.add_edge("fetch_geopolitics", END)
    subgraph.add_edge("fetch_news_sentiment", END)
    subgraph.add_edge("fetch_capital_rotation", END)
    subgraph.add_edge("fetch_competitor_contagion", END)
    subgraph.add_edge("fetch_beta", END)
    subgraph.add_edge("fetch_supply_chain", END)

    return subgraph.compile()