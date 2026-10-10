import sys
from pathlib import Path

# Ensure backend directory is in python module search path
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from web_scraper import run_cli_update

if __name__ == "__main__":
    run_cli_update(max_pages=10)
