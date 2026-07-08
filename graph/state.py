from typing import TypedDict, Annotated, Literal
import operator

class SemiconductorState(TypedDict):
    # Input
    ticker: Annotated[str, lambda old, new: new]
    
    # Macroeconomic factors
    cpi: Annotated[str, lambda old, new: new]
    ppi: Annotated[str, lambda old, new: new]
    fed_rate: Annotated[str, lambda old, new: new]
    usd_index: Annotated[str, lambda old, new: new]
    
    # Fundamental factors
    pe_ratio: Annotated[str, lambda old, new: new]
    market_cap: Annotated[str, lambda old, new: new]
    earnings_guidance: Annotated[str, lambda old, new: new]
    insider_selling: Annotated[str, lambda old, new: new]
    
    # Market intelligence factors 
    sector_rally: Annotated[str, lambda old, new: new]
    technical_signal: Annotated[str, lambda old, new: new]
    analyst_ratings: Annotated[str, lambda old, new: new]
    sell_the_news: Annotated[str, lambda old, new: new]
    
    # External signal factors
    geopolitics: Annotated[str, lambda old, new: new]
    supply_chain: Annotated[str, lambda old, new: new]
    news_sentiment: Annotated[str, lambda old, new: new]
    capital_rotation: Annotated[str, lambda old, new: new]
    competitor_contagion: Annotated[str, lambda old, new: new]
    beta: Annotated[str, lambda old, new: new]
    
    # Final output
    prediction: Annotated[str, lambda old, new: new]
    scores: Annotated[dict, lambda old, new: new] 