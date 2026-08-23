# SemiBot

18-factor agentic RAG system for semiconductor equity prediction, built with LangGraph and retrieval-augmented generation over market and fundamentals data.

**Live app:** https://semibot-raj.streamlit.app/

## Stack
- Streamlit (frontend)
- LangGraph (agent orchestration)
- RAG pipeline over semiconductor sector data
- SQLite (checkpointing / factor cache)

## Run locally
```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```
