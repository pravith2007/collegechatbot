import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
REGISTRY_PATH = DATA_DIR / "sync_registry.json"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")

# Server Config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Security / Admin Config
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "kec_admin_secure_2026")

# Scraping & Website Config
TARGET_BASE_URL = "https://kongu.ac.in/"
ALLOWED_DOMAINS = ["kongu.ac.in", "www.kongu.ac.in", "kongu.edu", "www.kongu.edu"]

# Seed URLs representing official public KEC portals
APPROVED_SEED_URLS = [
    "https://kongu.ac.in/",
    "https://kongu.ac.in/aboutus.php",
    "https://kongu.ac.in/departments.php",
    "https://kongu.ac.in/facilities.php",
    "https://kongu.ac.in/placement.php",
    "https://kongu.ac.in/admission.php",
    "https://kongu.ac.in/contactus.php",
    "https://kongu.ac.in/autonomous.php",
    "https://kongu.ac.in/research.php",
    "https://kongu.ac.in/coe.php",
]

# Sensitive / login protected prefixes to never crawl
DISALLOWED_URL_PATTERNS = [
    "login",
    "portal",
    "student_login",
    "staff_login",
    "admin",
    "cpanel",
    "webmail",
    "result_login",
    "payment",
    "payonline",
    "attendance",
    "intranet",
    "auth",
]

# Crawler Politeness & Limits
CRAWL_USER_AGENT = "KEC-Chatbot-Sync-Bot/1.0 (+https://kongu.ac.in/)"
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "12"))
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "1.0"))
MAX_PAGES_PER_SYNC = int(os.getenv("MAX_PAGES_PER_SYNC", "30"))

# Scheduler Config
DEFAULT_SYNC_INTERVAL_MINUTES = int(os.getenv("DEFAULT_SYNC_INTERVAL_MINUTES", "60"))

# LLM & Embedding Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# RAG Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "4"))
