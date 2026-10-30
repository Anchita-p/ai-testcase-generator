"""Central settings. Any value can be overridden in the .env file."""
import os

from dotenv import load_dotenv

load_dotenv()

# Free API key from https://aistudio.google.com/apikey
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Model names (change here if Google renames a model)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3.5-flash-lite")
# Used automatically if the main model times out or is overloaded (empty = no fallback)
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-3.1-flash-lite")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

# Fail fast instead of hanging: the Gemini client defaults to 6 retries and no timeout
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "45"))   # seconds per attempt
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "1"))

# How the requirements document is cut into pieces ("chunks")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# How many chunks are retrieved for the selected feature
TOP_K = int(os.getenv("TOP_K", "6"))

# Limits for how many test cases can be requested at once
MIN_CASES = 3
MAX_CASES = 25
