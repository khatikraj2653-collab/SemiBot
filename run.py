import os
import sys

# Windows' default console encoding (cp1252/"charmap") can't print many
# Unicode characters (emoji, special symbols) that show up in fetched news
# text, API errors, etc. Any print() hitting one of those crashes with
# UnicodeEncodeError, which bubbles up as a fake "Analysis failed" error.
# Force UTF-8 with a safe fallback so print() never crashes the app again.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = "SemiBot"

from streamlit.web import cli as stcli

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "frontend/app.py"]
    sys.exit(stcli.main())