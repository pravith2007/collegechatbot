import io
import time
import logging
import hashlib
import urllib.robotparser
from urllib.parse import urlparse, urljoin, urldefrag
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from config import (
    CRAWL_USER_AGENT,
    REQUEST_TIMEOUT_SECONDS,
    REQUEST_DELAY_SECONDS,
    ALLOWED_DOMAINS,
    DISALLOWED_URL_PATTERNS,
    MAX_PAGES_PER_SYNC,
    APPROVED_SEED_URLS
)

logger = logging.getLogger("kec_scraper")

class WebsiteCollector:
    """Automated website collector for official public Kongu Engineering College web content."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CRAWL_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ta;q=0.8",
        })
        self.robot_parser = urllib.robotparser.RobotFileParser()
        self._robots_loaded = False

    def load_robots_txt(self, base_url: str = "https://kongu.ac.in/"):
        """Loads and respects robots.txt from the website."""
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            resp = self.session.get(robots_url, timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                self.robot_parser.parse(resp.text.splitlines())
                self._robots_loaded = True
                logger.info("Successfully fetched and parsed robots.txt from KEC website.")
            else:
                logger.warning(f"Robots.txt returned status {resp.status_code}; defaulting to permissive check.")
                self.robot_parser.allow_all = True
                self._robots_loaded = True
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt ({e}); defaulting to permissive check.")
            self.robot_parser.allow_all = True
            self._robots_loaded = True

    def is_url_permitted(self, url: str) -> bool:
        """Enforces domain constraints, security blacklists, and robots.txt."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False

            # Check domain
            netloc = parsed.netloc.lower()
            if not any(domain == netloc or netloc.endswith("." + domain) for domain in ALLOWED_DOMAINS):
                return False

            # Check sensitive or login-protected portal patterns
            url_lower = url.lower()
            for pattern in DISALLOWED_URL_PATTERNS:
                if pattern in url_lower:
                    logger.debug(f"Skipping disallowed/private portal path: {url}")
                    return False

            # Check robots.txt
            if self._robots_loaded and not self.robot_parser.can_fetch(CRAWL_USER_AGENT, url):
                logger.info(f"Skipping URL disallowed by robots.txt: {url}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking URL permission for {url}: {e}")
            return False

    def normalize_url(self, url: str) -> str:
        """Removes fragment anchors and normalizes path."""
        url, _ = urldefrag(url)
        return url.strip()

    def calculate_hash(self, text: str) -> str:
        """Generates a SHA-256 hash of the cleaned text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def extract_text_from_html(self, html_content: str, url: str) -> Tuple[str, str]:
        """Extracts title and cleans noise from HTML."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else url

        # Remove irrelevant elements (scripts, styles, navigations, footers)
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        # Extract clean text with structured spacing
        text_lines = []
        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "div", "span"]):
            text = element.get_text(separator=" ", strip=True)
            if len(text) > 15:  # Filter out trivial micro-snippets
                text_lines.append(text)

        cleaned_text = "\n\n".join(dict.fromkeys(text_lines))  # Deduplicate consecutive lines
        return title, cleaned_text

    def extract_text_from_pdf(self, pdf_bytes: bytes, url: str) -> Tuple[str, str]:
        """Extracts text from downloaded public PDF files."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages[:20]):  # Cap at first 20 pages for relevance
                t = page.extract_text()
                if t and t.strip():
                    pages_text.append(t.strip())
            
            title = f"Document: {url.split('/')[-1]}"
            full_text = "\n\n".join(pages_text)
            return title, full_text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF at {url}: {e}")
            return f"PDF: {url.split('/')[-1]}", ""

    def discover_links(self, html_content: str, base_url: str) -> Set[str]:
        """Extracts permitted internal links from HTML content."""
        soup = BeautifulSoup(html_content, "html.parser")
        discovered = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            full_url = self.normalize_url(urljoin(base_url, href))
            if self.is_url_permitted(full_url):
                # Filter extensions
                path_lower = urlparse(full_url).path.lower()
                if path_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".tar", ".exe", ".css", ".js")):
                    continue
                discovered.add(full_url)

        return discovered

    def fetch_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Safely fetches a single URL, handles timeouts, respects rate limit, and extracts content."""
        if not self.is_url_permitted(url):
            return None

        time.sleep(REQUEST_DELAY_SECONDS)  # Polite crawling delay

        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch {url} (HTTP {resp.status_code})")
                return {
                    "url": url,
                    "success": False,
                    "status_code": resp.status_code,
                    "error": f"HTTP status {resp.status_code}"
                }

            content_type = resp.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                title, text = self.extract_text_from_pdf(resp.content, url)
                doc_type = "pdf"
                discovered_links = set()
            else:
                title, text = self.extract_text_from_html(resp.text, url)
                doc_type = "html"
                discovered_links = self.discover_links(resp.text, url)

            if not text.strip():
                return {
                    "url": url,
                    "success": False,
                    "error": "No readable text extracted"
                }

            content_hash = self.calculate_hash(text)

            return {
                "url": url,
                "title": title or "Kongu Engineering College",
                "text": text,
                "content_hash": content_hash,
                "doc_type": doc_type,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "discovered_links": list(discovered_links),
                "success": True,
                "word_count": len(text.split())
            }

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching {url}")
            return {"url": url, "success": False, "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching {url}: {e}")
            return {"url": url, "success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error while fetching {url}: {e}")
            return {"url": url, "success": False, "error": str(e)}

    def collect_website(self, seed_urls: Optional[List[str]] = None, max_pages: int = MAX_PAGES_PER_SYNC) -> List[Dict[str, Any]]:
        """Collects pages starting from seed URLs and BFS discovers internal links up to max_pages."""
        if not self._robots_loaded:
            self.load_robots_txt()

        seeds = [self.normalize_url(u) for u in (seed_urls or APPROVED_SEED_URLS)]
        queue = list(seeds)
        visited: Set[str] = set()
        collected_documents: List[Dict[str, Any]] = []

        logger.info(f"Starting website collection with {len(seeds)} seed URLs (Max pages: {max_pages})")

        while queue and len(collected_documents) < max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue

            visited.add(current_url)
            logger.info(f"Crawling ({len(collected_documents)+1}/{max_pages}): {current_url}")

            doc = self.fetch_url(current_url)
            if doc and doc.get("success"):
                collected_documents.append(doc)
                # Enqueue new links
                for new_link in doc.get("discovered_links", []):
                    if new_link not in visited and new_link not in queue:
                        queue.append(new_link)
            elif doc:
                collected_documents.append(doc)

        logger.info(f"Website collection completed. Fetched {len(collected_documents)} pages.")
        return collected_documents
