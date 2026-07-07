from typing import TypedDict, Annotated, Literal
import operator

class SemiconductorState(TypedDict):
    # Input
    ticker: str
    
    # Macroeconomic factors
    cpi: str
    ppi: str
    fed_rate: str
    usd_index: str
    
    # Fundamental factors
    pe_ratio: str
    market_cap: str
    earnings_guidance: str
    insider_selling: str
    
    # Market intelligence factors 
    sector_rally: str
    technical_signal: str
    analyst_ratings: str
    sell_the_news: str
    
    # External signal factors
    geopolitics: str
    supply_chain: str
    news_sentiment: str
    capital_rotation: str
    competitor_contagion: str
    beta: str
    
    # Final output
    prediction: str