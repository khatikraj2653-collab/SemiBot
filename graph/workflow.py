import os

import streamlit as st
from langgraph.graph import StateGraph, START, END
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.state import SemiconductorState
from graph.nodes import generate_prediction
from graph.subgraphs import build_macro_subgraph, build_fundamental_subgraph, build_market_subgraph, build_external_subgraph

# One-time at import: purge any stale error rows left in the SQLite factor
# cache from before we started skipping error caching, so old "Cannot specify
# ',' with 's'" / "Too Many Requests" etc. don't keep being served.
try:
    from tools.cache_utils import purge_error_cache
    _purged = purge_error_cache()
    if _purged:
        print(f"[cache] purged {_purged} stale error rows", flush=True)
except Exception as _e:
    print(f"[cache] purge skipped: {_e}", flush=True)

@st.cache_resource(show_spinner=False)
def build_graph():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'semibot_checkpoints.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = StateGraph(SemiconductorState)

    graph.add_node("fetch_macro", build_macro_subgraph())
    graph.add_node("fetch_fundamental", build_fundamental_subgraph())
    graph.add_node("fetch_market", build_market_subgraph())
    graph.add_node("fetch_external", build_external_subgraph())
    graph.add_node("generate_prediction", generate_prediction)

    graph.add_edge(START, "fetch_macro")
    graph.add_edge(START, "fetch_fundamental")
    graph.add_edge(START, "fetch_market")
    graph.add_edge(START, "fetch_external")
    graph.add_edge("fetch_macro", "generate_prediction")
    graph.add_edge("fetch_fundamental", "generate_prediction")
    graph.add_edge("fetch_market", "generate_prediction")
    graph.add_edge("fetch_external", "generate_prediction")
    graph.add_edge("generate_prediction", END)

    return graph.compile(checkpointer=checkpointer)

app = build_graph()  # cached — only runs the heavy build the first time