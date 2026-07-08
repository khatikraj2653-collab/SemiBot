import os
from dotenv import load_dotenv
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = "SemiBot"

from streamlit.web import cli as stcli
import sys

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "frontend/app.py"]
    sys.exit(stcli.main())