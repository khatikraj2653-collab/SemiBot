import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import SemiconductorState
from graph.nodes import (
    fetch_macro_factors,
    fetch_fundamental_factors,
    fetch_market_factors,
    fetch_external_factors,
    generate_prediction
)

def build_graph():
    """Builds and compiles the semiconductor analysis LangGraph workflow."""
    
    # Initialize MemorySaver for checkpointing
    checkpointer = MemorySaver()
    
    # Build graph
    graph = StateGraph(SemiconductorState)
    
    # Add nodes
    graph.add_node("fetch_macro", fetch_macro_factors)
    graph.add_node("fetch_fundamental", fetch_fundamental_factors)
    graph.add_node("fetch_market", fetch_market_factors)
    graph.add_node("fetch_external", fetch_external_factors)
    graph.add_node("generate_prediction", generate_prediction)
    
    # Add edges
    graph.add_edge(START, "fetch_macro")
    graph.add_edge(START, "fetch_fundamental")
    graph.add_edge(START, "fetch_market")
    graph.add_edge(START, "fetch_external")
    graph.add_edge("fetch_macro", "generate_prediction")
    graph.add_edge("fetch_fundamental", "generate_prediction")
    graph.add_edge("fetch_market", "generate_prediction")
    graph.add_edge("fetch_external", "generate_prediction")
    graph.add_edge("generate_prediction", END)
    
    # Compile with checkpointer
    app = graph.compile(checkpointer=checkpointer)
    
    return app

# Initialize graph at module level
app = build_graph() 