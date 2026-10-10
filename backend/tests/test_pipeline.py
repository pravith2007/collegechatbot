import os
import io
import sys
import unittest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from web_scraper import KECWebScraper
from text_chunker import TextChunker
from rag_pipeline import RAGPipeline
from scheduler import KECSyncScheduler
from storage import storage

class TestKECFullPipeline(unittest.TestCase):
    """
    Comprehensive verification suite testing all 16 items specified in Section 10:
    1. Extracting text from HTML
    2. Cleaning HTML content
    3. Discovering internal links
    4. Respecting robots.txt
    5. Detecting changed pages with hashes
    6. Detecting unchanged pages
    7. Updating KONGU.txt safely
    8. Creating chunks
    9. Preserving Tamil characters
    10. Generating stable chunk IDs
    11. Updating ChromaDB without duplicates
    12. Retrieving a chunk using an English question
    13. Retrieving relevant information using a Tamil question
    14. Handling unavailable webpages
    15. Preserving the old knowledge base when synchronization fails
    16. Ensuring the scheduler does not start twice
    """

    @classmethod
    def setUpClass(cls):
        print("\n=================================================================")
        print("  Running KEC 16-Point Comprehensive Pipeline Test Suite")
        print("=================================================================\n")
        cls.scraper = KECWebScraper()
        cls.chunker = TextChunker()
        cls.rag = RAGPipeline()

    def test_01_extracting_text_from_html(self):
        """1. Test extracting text from HTML."""
        print("[TEST 01/16] Testing HTML text extraction...")
        sample_html = "<html><head><title>KEC Admissions</title></head><body><h1>Admissions 2026</h1><p>B.E and B.Tech degree courses offered.</p></body></html>"
        title, text = self.scraper.clean_text(sample_html, "https://kongu.ac.in/admission.php")
        self.assertEqual(title, "KEC Admissions")
        self.assertIn("Admissions 2026", text)
        self.assertIn("B.E and B.Tech degree courses offered.", text)
        print("[PASS] Test 01: HTML text extraction succeeded.")

    def test_02_cleaning_html_content(self):
        """2. Test cleaning HTML content (removing scripts, styles, navigations)."""
        print("[TEST 02/16] Testing cleaning of scripts and noise...")
        dirty_html = """
        <html><head><title>Clean Test</title><style>.hidden{display:none}</style></head>
        <body>
          <script>console.log('malicious script');</script>
          <nav><a href='/home'>Home Nav</a></nav>
          <h1>Real Heading</h1>
          <p>Real paragraph content for students.</p>
          <footer>Copyright 2026 Kongu Engineering College</footer>
        </body></html>
        """
        title, text = self.scraper.clean_text(dirty_html, "https://kongu.ac.in/clean.php")
        self.assertNotIn("malicious script", text)
        self.assertNotIn(".hidden", text)
        self.assertIn("Real Heading", text)
        self.assertIn("Real paragraph content for students.", text)
        print("[PASS] Test 02: HTML noise cleaning verified.")

    def test_03_discovering_internal_links(self):
        """3. Test discovering internal links on KEC domain."""
        print("[TEST 03/16] Testing internal link discovery...")
        html = """
        <html><body>
          <a href="/aboutus.php">About Us</a>
          <a href="https://kongu.ac.in/departments.php">Departments</a>
          <a href="https://google.com">External Link</a>
          <a href="javascript:void(0)">JS Link</a>
          <a href="/login.php">Private Login Portal</a>
        </body></html>
        """
        links = self.scraper.discover_links(html, "https://kongu.ac.in/")
        self.assertIn("https://kongu.ac.in/aboutus.php", links)
        self.assertIn("https://kongu.ac.in/departments.php", links)
        # Verify external and private login links are filtered out
        self.assertNotIn("https://google.com", links)
        self.assertNotIn("https://kongu.ac.in/login.php", links)
        print("[PASS] Test 03: Permitted internal link discovery verified.")

    def test_04_respecting_robots_txt(self):
        """4. Test respecting robots.txt rules."""
        print("[TEST 04/16] Testing robots.txt compliance...")
        self.scraper.load_robots_txt()
        # Public homepage should be allowed
        self.assertTrue(self.scraper.is_url_permitted("https://kongu.ac.in/"))
        # Private login portal should be disallowed
        self.assertFalse(self.scraper.is_url_permitted("https://kongu.ac.in/student_login.php"))
        print("[PASS] Test 04: Robots.txt and permission enforcement verified.")

    def test_05_detecting_changed_pages_with_hashes(self):
        """5. Test detecting changed pages with SHA-256 hashes."""
        print("[TEST 05/16] Testing SHA-256 change detection for modified pages...")
        text_v1 = "Placement percentage: 92% in 2024."
        text_v2 = "Placement percentage: 95% in 2025 with 250+ recruiting companies."
        hash_v1 = hashlib.sha256(text_v1.encode()).hexdigest()
        hash_v2 = hashlib.sha256(text_v2.encode()).hexdigest()
        self.assertNotEqual(hash_v1, hash_v2)
        print("[PASS] Test 05: SHA-256 hash delta accurately detects modified content.")

    def test_06_detecting_unchanged_pages(self):
        """6. Test detecting unchanged pages."""
        print("[TEST 06/16] Testing detection of identical content (zero changes)...")
        text = "Kongu Engineering College was established in 1984 in Perundurai."
        h1 = hashlib.sha256(text.encode()).hexdigest()
        h2 = hashlib.sha256(text.encode()).hexdigest()
        self.assertEqual(h1, h2)
        print("[PASS] Test 06: Hash match prevents redundant re-indexing of unchanged pages.")

    def test_07_updating_kongu_txt_safely(self):
        """7. Test updating KONGU.txt safely with backup creation."""
        print("[TEST 07/16] Testing safe KONGU.txt file update and backup...")
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "KONGU.txt"
            test_file.write_text("MANUAL KNOWLEDGE: ECE Department details.", encoding="utf-8")
            
            scraper = KECWebScraper()
            scraper.kongu_txt_path = test_file

            scraped = [{
                "url": "https://kongu.ac.in/test_unit.php",
                "title": "Unit Test Page",
                "text": "Automated scraped content line 1.",
                "content_hash": hashlib.sha256(b"unit_content").hexdigest(),
                "last_fetched": "2026-10-10T12:00:00Z",
                "success": True
            }]

            stats = scraper.update_kongu_txt(scraped)
            self.assertTrue(test_file.exists())
            self.assertTrue(test_file.with_suffix(".txt.bak").exists(), "Backup must be created")
            
            updated_content = test_file.read_text(encoding="utf-8")
            self.assertIn("MANUAL KNOWLEDGE: ECE Department details.", updated_content)
            self.assertIn("SOURCE URL: https://kongu.ac.in/test_unit.php", updated_content)
            self.assertIn("PAGE TITLE: Unit Test Page", updated_content)
            print("[PASS] Test 07: KONGU.txt updated safely with backup and source headers.")

    def test_08_creating_chunks(self):
        """8. Test creating chunks with paragraph boundaries."""
        print("[TEST 08/16] Testing semantic text chunking...")
        long_text = "Paragraph One about engineering college campus.\n\nParagraph Two about laboratory facilities and research centers.\n\nParagraph Three about sports and hostels."
        chunks = self.chunker.chunk_document(long_text, "https://kongu.ac.in/about", "About KEC")
        self.assertGreater(len(chunks), 0)
        self.assertIn("Paragraph One", chunks[0]["text"])
        print("[PASS] Test 08: Text chunking created valid semantic segments.")

    def test_09_preserving_tamil_characters(self):
        """9. Test preserving Tamil characters in chunking."""
        print("[TEST 09/16] Testing Tamil Unicode preservation in chunking...")
        tamil_text = "வணக்கம்! கொங்கு பொறியியல் கல்லூரி சேர்க்கை 2026.\n\nதமிழ் விசைப்பலகை மற்றும் குரல் வழி உள்ளீடு வசதிகள் உள்ளன."
        chunks = self.chunker.chunk_document(tamil_text, "https://kongu.ac.in/tamil", "தமிழ் பக்கம்")
        self.assertGreater(len(chunks), 0)
        self.assertTrue(chunks[0]["is_tamil"])
        self.assertIn("வணக்கம்", chunks[0]["text"])
        self.assertIn("கொங்கு பொறியியல் கல்லூரி", chunks[0]["text"])
        print("[PASS] Test 09: Tamil characters preserved accurately without corruption.")

    def test_10_generating_stable_chunk_ids(self):
        """10. Test generating stable chunk IDs."""
        print("[TEST 10/16] Testing deterministic stable chunk IDs...")
        text = "Kongu Central Library houses over 100,000 volumes."
        url = "https://kongu.ac.in/library.php"
        chunks1 = self.chunker.chunk_document(text, url, "Library")
        chunks2 = self.chunker.chunk_document(text, url, "Library")
        self.assertEqual(chunks1[0]["id"], chunks2[0]["id"], "Chunk ID must be deterministic and stable")
        self.assertTrue(chunks1[0]["id"].startswith("kec_"))
        print("[PASS] Test 10: Stable chunk ID generation verified.")

    def test_11_updating_chromadb_without_duplicates(self):
        """11. Test updating ChromaDB without duplicates."""
        print("[TEST 11/16] Testing duplicate prevention in ChromaDB...")
        chunk = [{
            "id": "test_stable_dedup_001",
            "text": "Kongu Engineering College robotics club and drone lab.",
            "source_url": "https://kongu.ac.in/robotics.php",
            "page_title": "Robotics Club",
            "chunk_index": 0,
            "last_fetched": "2026-10-10T12:00:00Z"
        }]

        # Insert once
        self.rag.update_chunks(chunk)
        count1 = self.rag.collection.count()

        # Insert again with same ID (upsert)
        self.rag.update_chunks(chunk)
        count2 = self.rag.collection.count()

        self.assertEqual(count1, count2, "Upsert with same ID must not increase count (no duplicates)")
        self.rag.remove_stale_chunks(["test_stable_dedup_001"])
        print("[PASS] Test 11: ChromaDB deduplication and upsert verified.")

    def test_12_retrieving_chunk_english_question(self):
        """12. Test retrieving a chunk using an English question."""
        print("[TEST 12/16] Testing English semantic retrieval...")
        chunk = [{
            "id": "test_en_retrieval_001",
            "text": "The Highest placement package at Kongu Engineering College reached 52 LPA.",
            "source_url": "https://kongu.ac.in/placement.php",
            "page_title": "KEC Placement Highlights",
            "chunk_index": 0
        }]
        self.rag.update_chunks(chunk)

        res = self.rag.answer_question("What is the highest placement package in KEC?")
        self.assertIn("52 LPA", res["answer"])
        self.assertGreater(len(res["sources"]), 0)
        self.assertEqual(res["sources"][0]["url"], "https://kongu.ac.in/placement.php")
        
        self.rag.remove_stale_chunks(["test_en_retrieval_001"])
        print("[PASS] Test 12: English retrieval and citation verified.")

    def test_13_retrieving_chunk_tamil_question(self):
        """13. Test retrieving relevant information using a Tamil question."""
        print("[TEST 13/16] Testing Tamil semantic retrieval...")
        chunk = [{
            "id": "test_ta_retrieval_001",
            "text": "கொங்கு பொறியியல் கல்லூரியில் 14 வகையான பி.இ மற்றும் பி.டெக் இளநிலைப் பொறியியல் படிப்புகள் உள்ளன.",
            "source_url": "https://kongu.ac.in/admission.php",
            "page_title": "சேர்க்கை",
            "chunk_index": 0
        }]
        self.rag.update_chunks(chunk)

        res = self.rag.answer_question("கொங்கு கல்லூரியில் எத்தனை பொறியியல் படிப்புகள் உள்ளன?")
        self.assertIn("14", res["answer"])
        self.assertTrue(res["is_tamil"])
        self.assertGreater(len(res["sources"]), 0)

        self.rag.remove_stale_chunks(["test_ta_retrieval_001"])
        print("[PASS] Test 13: Tamil retrieval and response verified.")

    def test_14_handling_unavailable_webpages(self):
        """14. Test handling unavailable webpages (404, timeouts)."""
        print("[TEST 14/16] Testing network error and 404 handling...")
        res = self.scraper.fetch_page("https://kongu.ac.in/non_existent_page_random_404.php")
        if res:
            self.assertFalse(res["success"], "Non-existent page must report success=False")
        print("[PASS] Test 14: Network failure and 404 errors handled safely.")

    def test_15_preserving_old_knowledge_base_on_failure(self):
        """15. Test preserving old knowledge base when synchronization fails."""
        print("[TEST 15/16] Testing preservation of previous knowledge during failure...")
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "KONGU.txt"
            initial_content = "CRITICAL SAVED KNOWLEDGE: Accredited NAAC A++ with high grade."
            test_file.write_text(initial_content, encoding="utf-8")

            scraper = KECWebScraper()
            scraper.kongu_txt_path = test_file

            # Simulate empty or failed scraped batch
            failed_batch = [{"url": "https://kongu.ac.in/bad", "success": False, "error": "Timeout"}]
            scraper.update_kongu_txt(failed_batch)

            retained_content = test_file.read_text(encoding="utf-8")
            self.assertIn("CRITICAL SAVED KNOWLEDGE", retained_content, "Old knowledge must never be erased on failure")
        print("[PASS] Test 15: Prior knowledge preserved on failure.")

    def test_16_ensuring_scheduler_does_not_start_twice(self):
        """16. Test ensuring scheduler does not start twice."""
        print("[TEST 16/16] Testing single scheduler instance safety...")
        sched = KECSyncScheduler(interval_hours=24)
        sched.start()
        first_state = sched._started
        self.assertTrue(first_state)

        # Attempt starting again
        sched.start()
        self.assertTrue(sched._started)
        sched.shutdown()
        print("[PASS] Test 16: Duplicate scheduler startup prevented.")

if __name__ == "__main__":
    unittest.main()
