import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.1")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
EMBEDDING_DIMENSIONS = 3072 




# ─────────────────────────── Azure Blob Storage ─────────────────────
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "")


# ─────────────────────────── Azure AI Search ────────────────────────
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY", "")
SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "tvsragbot")

# Field names inside your index — adjust to match your index definition

ID_FIELD = "id"
CONTENT_FIELD = "chunk"
VECTOR_FIELD = "text_vector"
SEMANTIC_CONFIG_NAME = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG") or None  # None = plain hybrid (BM25 + vector)

# ─────────────────────────── Retrieval tuning ───────────────────────
TOP_K = 8                 # chunks passed to the final response node
KNN_NEIGHBOURS = 50       # vector candidates before hybrid fusion
MIN_RESULTS = 3           # below this, retrieval relaxes the metadata filters
FACET_MAX_VALUES = 50   
MAX_CHARS_PER_CHUNK = 4000

# ─────────────────────────── Chat history ───────────────────────────
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "chat_history.json")
HISTORY_TURNS_USED = 3    # last N turns fed to the LLMs
HISTORY_MAX_STORED = 50   # turns kept per session on disk


COMPANIES = {
    "insurancedekho": {
        "display_name": "InsuranceDekho",
        "entity_names": ["InsuranceDekho"],
        "description": "InsuranceDekho — insurance distribution / insurtech platform (TVS Capital portfolio company).",
    },
    "yubi": {
        "display_name": "Yubi",
        "entity_names": ["Yubi"],
        "description": "Yubi (formerly CredAvenue) — debt marketplace / credit platform (TVS Capital portfolio company).",
    },
}
