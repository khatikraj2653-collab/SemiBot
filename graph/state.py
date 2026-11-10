from typing import TypedDict, Annotated, Literal
import operator

# Each factor is set by exactly one subgraph in a parallel fan-out. When a
# subgraph finishes, LangGraph emits every field it holds — including empty
# strings for the factors the OTHER subgraphs owned. Plain "last write wins"
# then overwrites real data with those empties, which leaves generate_prediction
# with only one subgraph's factors populated (reproduced in GoldBot CI
# 2026-11-10 against the same graph shape as this one). Keeping the first
# non-empty write prevents that without needing output-key filters on every
# subgraph.
def _keep_non_empty_str(old: str, new: str) -> str:
    return new if new else (old or "")


def _keep_non_empty_dict(old: dict, new: dict) -> dict:
    return new if new else (old or {})


class SemiconductorState(TypedDict):
    # Input
    ticker: Annotated[str, _keep_non_empty_str]

    # Macroeconomic factors
    cpi: Annotated[str, _keep_non_empty_str]
    ppi: Annotated[str, _keep_non_empty_str]
    fed_rate: Annotated[str, _keep_non_empty_str]
    usd_index: Annotated[str, _keep_non_empty_str]

    # Fundamental factors
    pe_ratio: Annotated[str, _keep_non_empty_str]
    market_cap: Annotated[str, _keep_non_empty_str]
    earnings_guidance: Annotated[str, _keep_non_empty_str]
    insider_selling: Annotated[str, _keep_non_empty_str]

    # Market intelligence factors
    sector_rally: Annotated[str, _keep_non_empty_str]
    technical_signal: Annotated[str, _keep_non_empty_str]
    analyst_ratings: Annotated[str, _keep_non_empty_str]
    sell_the_news: Annotated[str, _keep_non_empty_str]

    # External signal factors
    geopolitics: Annotated[str, _keep_non_empty_str]
    supply_chain: Annotated[str, _keep_non_empty_str]
    news_sentiment: Annotated[str, _keep_non_empty_str]
    capital_rotation: Annotated[str, _keep_non_empty_str]
    competitor_contagion: Annotated[str, _keep_non_empty_str]
    beta: Annotated[str, _keep_non_empty_str]

    # Final output
    prediction: Annotated[str, _keep_non_empty_str]
    scores: Annotated[dict, _keep_non_empty_dict]
