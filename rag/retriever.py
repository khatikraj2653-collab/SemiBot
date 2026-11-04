import os
import streamlit as st
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

@st.cache_resource(show_spinner=False)
def _build_retriever():
    """Loads the FAISS vector store and returns a retriever.
    Cached across reruns / sessions so it only loads once per server."""
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vectorstore = FAISS.load_local(
            os.path.join(BASE_DIR, "data", "faiss_index"),
            embeddings,
            allow_dangerous_deserialization=True
        )
        return vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3}
        )
    except Exception as e:
        print(f"Warning: Could not load FAISS index: {e}")
        print("Run build_vectorstore.py first to create the index.")
        return None

def load_retriever():
    """Public entrypoint used by callers; delegates to cached builder."""
    return _build_retriever()

# Initialize retriever at module level (hits the cache after first call)
retriever = load_retriever()
