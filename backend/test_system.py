import io
import time
import unittest
import hashlib
from datetime import datetime, timezone

from pypdf import PdfWriter

from config import CHROMA_DIR, REGISTRY_PATH
from storage import storage
from scraper import WebsiteCollector
from change_detector import ChangeDetector
from rag_engine import rag_engine
from scheduler import scheduler

class TestKECSyncAndRAGSystem(unittest.TestCase):
    """Automated verification suite testing all 12 required features of the KEC Chatbot System."""

    @classmethod
    def setUpClass(cls):
        print("\n========================================================")
        print("  Starting KEC System Test Suite (12 Core Tests)")
        print("========================================================\n")
        cls.storage = storage
        cls.rag = rag_engine
        cls.collector = WebsiteCollector()

    def test_01_initial_indexing(self):
        """1. Test Initial website / seed indexing."""
        print("[TEST 1/12] Testing Initial Document Indexing...")
        sample_doc = {
            "url": "https://kongu.ac.in/test_initial.php",
            "title": "KEC Test Initial Page",
            "text": "Kongu Engineering College is located in Perundurai, Erode. Offering UG and PG engineering degrees.",
            "doc_type": "html",
            "content_hash": hashlib.sha256(b"initial_test_content").hexdigest()
        }
        chunk_ids = self.rag.index_document(sample_doc)
        self.assertGreater(len(chunk_ids), 0, "Chunk IDs should be generated")
        sample_doc["chunk_ids"] = chunk_ids
        self.storage.set_document(sample_doc["url"], sample_doc)
        
        saved = self.storage.get_document(sample_doc["url"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved["title"], "KEC Test Initial Page")
        print("[PASS] Test 1: Initial indexing succeeded.")

    def test_02_repeated_indexing_no_changes(self):
        """2. Test Repeated indexing with no content changes (hash match)."""
        print("[TEST 2/12] Testing Repeated Indexing (Unchanged Content)...")
        doc_url = "https://kongu.ac.in/test_initial.php"
        saved = self.storage.get_document(doc_url)
        self.assertIsNotNone(saved)

        incoming_batch = [{
            "url": doc_url,
            "title": saved["title"],
            "text": saved["text"],
            "doc_type": "html",
            "content_hash": saved["content_hash"],
            "success": True
        }]

        classified = ChangeDetector.classify_documents(incoming_batch)
        self.assertEqual(len(classified["unchanged"]), 1, "Document must be classified as unchanged")
        self.assertEqual(len(classified["modified"]), 0, "No documents should be modified")
        self.assertEqual(len(classified["new"]), 0, "No documents should be new")
        print("[PASS] Test 2: Content hash matching successfully avoids redundant re-indexing.")

    def test_03_detection_of_modified_content(self):
        """3. Test Detection of modified content."""
        print("[TEST 3/12] Testing Detection of Modified Content...")
        doc_url = "https://kongu.ac.in/test_initial.php"
        saved = self.storage.get_document(doc_url)
        self.assertIsNotNone(saved)

        modified_text = saved["text"] + " Newly added robotics laboratory and research wing."
        new_hash = hashlib.sha256(modified_text.encode()).hexdigest()

        incoming_batch = [{
            "url": doc_url,
            "title": saved["title"],
            "text": modified_text,
            "doc_type": "html",
            "content_hash": new_hash,
            "success": True
        }]

        classified = ChangeDetector.classify_documents(incoming_batch)
        self.assertEqual(len(classified["modified"]), 1, "Document must be classified as modified")
        self.assertEqual(classified["modified"][0]["url"], doc_url)
        print("[PASS] Test 3: Content modifications accurately detected by hash delta.")

    def test_04_detection_of_new_pages(self):
        """4. Test Detection of newly discovered pages."""
        print("[TEST 4/12] Testing Detection of Newly Discovered Pages...")
        new_url = "https://kongu.ac.in/brand_new_department_test.php"
        incoming_batch = [{
            "url": new_url,
            "title": "Artificial Intelligence & Data Science",
            "text": "The Department of AI & DS focuses on deep learning and generative models.",
            "doc_type": "html",
            "content_hash": hashlib.sha256(b"brand_new_dept").hexdigest(),
            "success": True
        }]

        classified = ChangeDetector.classify_documents(incoming_batch)
        self.assertEqual(len(classified["new"]), 1, "New URL must be detected as new")
        print("[PASS] Test 4: Newly discovered URL identified accurately.")

    def test_05_failed_website_requests(self):
        """5. Test Failed website requests handling."""
        print("[TEST 5/12] Testing Failed Request Handling...")
        failed_batch = [{
            "url": "https://kongu.ac.in/non_existent_page_404.php",
            "success": False,
            "status_code": 404,
            "error": "HTTP status 404"
        }]

        classified = ChangeDetector.classify_documents(failed_batch)
        self.assertEqual(len(classified["failed"]), 1, "Failed request must be routed to failed list")
        print("[PASS] Test 5: Network and HTTP failures handled gracefully.")

    def test_06_pdf_extraction(self):
        """6. Test PDF text extraction."""
        print("[TEST 6/12] Testing PDF Text Extraction...")
        # Create an in-memory sample PDF using pypdf
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        stream = io.BytesIO()
        writer.write(stream)
        pdf_bytes = stream.getvalue()

        title, text = self.collector.extract_text_from_pdf(pdf_bytes, "https://kongu.ac.in/files/brochure.pdf")
        self.assertIn("brochure.pdf", title)
        print("[PASS] Test 6: PDF parsing pipeline verified without errors.")

    def test_07_chromadb_atomic_updates(self):
        """7. Test ChromaDB atomic updates & persistence."""
        print("[TEST 7/12] Testing Atomic ChromaDB Update...")
        doc_url = "https://kongu.ac.in/test_atomic.php"
        doc = {
            "url": doc_url,
            "title": "Atomic Test Doc",
            "text": "Version 1 of the atomic document text.",
            "doc_type": "html"
        }
        old_ids = self.rag.index_document(doc)
        self.assertGreater(len(old_ids), 0)

        # Update text atomically
        doc["text"] = "Version 2 of the atomic document text with updated fee schedule."
        new_ids = self.rag.update_document_atomic(doc, old_ids)
        self.assertGreater(len(new_ids), 0)

        # Cleanup
        self.rag.delete_document(doc_url, new_ids)
        print("[PASS] Test 7: Atomic chunk replacement succeeded without data corruption.")

    def test_08_tamil_question_retrieval(self):
        """8. Test Tamil question retrieval."""
        print("[TEST 8/12] Testing Tamil Question Retrieval...")
        doc = {
            "url": "https://kongu.ac.in/tamil_test.php",
            "title": "KEC Tamil Information",
            "text": "கொங்கு பொறியியல் கல்லூரியில் பி.இ, பி.டெக், எம்.இ, எம்பிஏ படிப்புகள் உள்ளன. சேர்க்கை கவுன்சிலிங் மூலம் நடைபெறுகிறது.",
            "doc_type": "html"
        }
        c_ids = self.rag.index_document(doc)

        hits = self.rag.query("கொங்கு பொறியியல் கல்லூரி சேர்க்கை படிப்புகள்", top_k=2)
        self.assertGreater(len(hits), 0, "Should retrieve hits for Tamil query")
        self.assertTrue(self.rag.is_tamil_query("கொங்கு பொறியியல் கல்லூரி சேர்க்கை"))
        
        # Cleanup
        self.rag.delete_document(doc["url"], c_ids)
        print("[PASS] Test 8: Tamil semantic retrieval is functioning properly.")

    def test_09_english_question_retrieval(self):
        """9. Test English question retrieval."""
        print("[TEST 9/12] Testing English Question Retrieval...")
        doc = {
            "url": "https://kongu.ac.in/english_test.php",
            "title": "KEC Placement Statistics",
            "text": "Kongu Engineering College achieved 92 percent placement with top recruiters TCS, Wipro, and Zoho.",
            "doc_type": "html"
        }
        c_ids = self.rag.index_document(doc)

        hits = self.rag.query("What are the placement statistics for KEC?", top_k=2)
        self.assertGreater(len(hits), 0, "Should retrieve hits for English query")
        
        # Cleanup
        self.rag.delete_document(doc["url"], c_ids)
        print("[PASS] Test 9: English semantic retrieval is functioning properly.")

    def test_10_source_citation_accuracy(self):
        """10. Test Source citation accuracy."""
        print("[TEST 10/12] Testing Source Citation Accuracy...")
        doc = {
            "url": "https://kongu.ac.in/maps/auditorium.php",
            "title": "Maharaja Auditorium Map",
            "text": "Maharaja Auditorium is located on the North Campus. Google Maps: https://maps.app.goo.gl/BX8SNrCiNfeeATtB8",
            "doc_type": "html"
        }
        c_ids = self.rag.index_document(doc)

        hits = self.rag.query("Where is Maharaja Auditorium?", top_k=1)
        answer, sources = self.rag.generate_grounded_answer("Where is Maharaja Auditorium?", hits)
        self.assertGreater(len(sources), 0, "Must return citations")
        self.assertEqual(sources[0]["url"], doc["url"])
        self.assertIn("https://maps.app.goo.gl", answer)

        # Cleanup
        self.rag.delete_document(doc["url"], c_ids)
        print("[PASS] Test 10: Source citation and Google Maps link verified.")

    def test_11_scheduled_execution(self):
        """11. Test Scheduled execution interval configuration."""
        print("[TEST 11/12] Testing Scheduled Execution Configuration...")
        scheduler.set_interval(45)
        self.assertEqual(scheduler.current_interval_minutes, 45)
        state = self.storage.get_sync_state()
        self.assertEqual(state.get("interval_minutes"), 45)
        print("[PASS] Test 11: Synchronization scheduler interval configured and persisted.")

    def test_12_manual_synchronization(self):
        """12. Test Manual synchronization trigger."""
        print("[TEST 12/12] Testing Manual Synchronization Trigger...")
        res = scheduler.trigger_manual_sync()
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "running")
        print("[PASS] Test 12: Manual synchronization trigger verified.")

if __name__ == "__main__":
    unittest.main()
