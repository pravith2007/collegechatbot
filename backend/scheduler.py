import os
import sys
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import DEFAULT_SYNC_INTERVAL_MINUTES
from storage import storage
from web_scraper import KECWebScraper
from text_chunker import TextChunker
from rag_pipeline import rag_pipeline

logger = logging.getLogger("kec_scheduler")

class KECSyncScheduler:
    """
    Automatic APScheduler integration for KEC knowledge base synchronization:
    - Scrapes official public webpages from kongu.ac.in
    - Updates KONGU.txt knowledge file safely with backups
    - Chunks text into JSONL and increments ChromaDB vector index
    - Configurable schedule (default: 24 hours / 1440 mins)
    - Concurrency lock prevents duplicate jobs
    - Safe startup for Flask (WERKZEUG_RUN_MAIN aware)
    """

    def __init__(self, interval_hours: int = 24):
        self.interval_minutes = interval_hours * 60
        self.scheduler = BackgroundScheduler()
        self.scraper = KECWebScraper()
        self.chunker = TextChunker()
        self.is_syncing = False
        self._lock = threading.Lock()
        self.job_id = "kec_auto_sync_job"
        self._started = False

    def start(self):
        """Starts the scheduler safely, preventing duplicate instances in Flask debug mode."""
        # Check if running under Flask reloader to avoid double scheduling
        if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
            logger.info("Skipping scheduler start in Werkzeug reloader master process.")
            return

        with self._lock:
            if self._started:
                logger.info("Scheduler already started.")
                return

            trigger = IntervalTrigger(minutes=self.interval_minutes)
            self.scheduler.add_job(
                self.run_sync,
                trigger=trigger,
                id=self.job_id,
                name="KEC 24-Hour Periodic Knowledge Sync",
                replace_existing=True
            )
            self.scheduler.start()
            self._started = True
            self._update_next_run_time()
            logger.info(f"KECSyncScheduler active (Interval: {self.interval_minutes} mins / {self.interval_minutes//60} hrs).")

    def shutdown(self):
        """Shuts down scheduler safely."""
        with self._lock:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                self._started = False
                logger.info("Scheduler successfully shut down.")

    def set_interval_minutes(self, minutes: int):
        """Reconfigures the synchronization interval."""
        if minutes < 1:
            raise ValueError("Interval must be at least 1 minute.")
        self.interval_minutes = minutes
        storage.update_sync_state(interval_minutes=minutes)

        if self.scheduler.running and self.scheduler.get_job(self.job_id):
            trigger = IntervalTrigger(minutes=minutes)
            self.scheduler.reschedule_job(self.job_id, trigger=trigger)
            self._update_next_run_time()
            logger.info(f"Rescheduled sync job to every {minutes} minutes.")

    def _update_next_run_time(self):
        job = self.scheduler.get_job(self.job_id) if self.scheduler.running else None
        if job and job.next_run_time:
            storage.update_sync_state(next_scheduled_sync=job.next_run_time.isoformat())
        else:
            calc_next = datetime.now(timezone.utc) + timedelta(minutes=self.interval_minutes)
            storage.update_sync_state(next_scheduled_sync=calc_next.isoformat())

    def trigger_manual_sync(self) -> Dict[str, Any]:
        """Manually launches synchronization in a non-blocking background thread."""
        with self._lock:
            if self.is_syncing:
                return {
                    "success": False,
                    "message": "A synchronization process is already running.",
                    "status": "running"
                }

        worker = threading.Thread(target=self.run_sync, args=(True,), daemon=True)
        worker.start()
        return {
            "success": True,
            "message": "Manual synchronization initiated in background.",
            "status": "running"
        }

    def run_sync(self, manual: bool = False) -> Dict[str, Any]:
        """
        Executes end-to-end synchronization:
        1. Polite crawl of official KEC pages
        2. Safe KONGU.txt file update with backups
        3. Text chunking with stable IDs
        4. Incremental ChromaDB embedding update
        """
        with self._lock:
            if self.is_syncing:
                logger.warning("Sync task triggered but already active. Skipping.")
                return {"success": False, "status": "running"}
            self.is_syncing = True

        start_time = datetime.now(timezone.utc)
        storage.update_sync_state(
            status="running",
            last_attempted_sync=start_time.isoformat(),
            last_error=None
        )
        logger.info(f"=== Starting KEC Knowledge Sync Cycle (Manual: {manual}) ===")

        run_summary = {
            "start_time": start_time.isoformat(),
            "manual": manual,
            "pages_processed": 0,
            "pages_changed": 0,
            "pages_new": 0,
            "pages_unchanged": 0,
            "pages_failed": 0,
            "chunks_updated": 0,
            "status": "running",
            "error": None
        }

        try:
            # 1. Scrape official webpages
            scraped_docs = self.scraper.crawl(max_pages=20)
            successful_docs = [d for d in scraped_docs if d.get("success")]
            failed_docs = [d for d in scraped_docs if not d.get("success")]

            run_summary["pages_processed"] = len(scraped_docs)
            run_summary["pages_failed"] = len(failed_docs)

            # 2. Update KONGU.txt safely
            txt_stats = self.scraper.update_kongu_txt(successful_docs)
            run_summary["pages_new"] = txt_stats["new_sources"]
            run_summary["pages_changed"] = txt_stats["updated_sources"]
            run_summary["pages_unchanged"] = txt_stats["unchanged_sources"]

            # 3. Chunk updated and new documents
            changed_or_new = [
                d for d in successful_docs 
                if storage.get_document(d["url"]) is None or 
                   storage.get_document(d["url"]).get("content_hash") != d["content_hash"]
            ]

            if changed_or_new:
                chunks = self.chunker.chunk_documents_and_save(changed_or_new)
                # 4. Upsert into ChromaDB
                rag_stats = rag_pipeline.update_chunks(chunks)
                run_summary["chunks_updated"] = rag_stats["inserted"]

                # Update registry
                for d in changed_or_new:
                    d_chunks = [ch["id"] for ch in chunks if ch.get("source_url") == d["url"]]
                    d["chunk_ids"] = d_chunks
                    storage.set_document(d["url"], d)
            else:
                logger.info("All collected documents are unchanged. ChromaDB re-indexing skipped.")

            end_time = datetime.now(timezone.utc)
            run_summary["end_time"] = end_time.isoformat()
            run_summary["duration_seconds"] = round((end_time - start_time).total_seconds(), 2)
            run_summary["status"] = "completed"

            storage.update_sync_state(
                status="completed",
                last_successful_sync=end_time.isoformat(),
                pages_checked=run_summary["pages_processed"],
                pages_changed=run_summary["pages_new"] + run_summary["pages_changed"],
                pages_failed=run_summary["pages_failed"],
                chunks_updated=run_summary["chunks_updated"],
                last_error=None
            )
            logger.info("=== KEC Knowledge Sync Cycle Completed Successfully ===")

        except Exception as e:
            logger.error(f"Error during synchronization run: {e}", exc_info=True)
            end_time = datetime.now(timezone.utc)
            run_summary["end_time"] = end_time.isoformat()
            run_summary["status"] = "error"
            run_summary["error"] = str(e)

            storage.update_sync_state(
                status="error",
                last_error=str(e),
                pages_failed=run_summary["pages_failed"] + 1
            )
        finally:
            self._update_next_run_time()
            storage.record_sync_run(run_summary)
            with self._lock:
                self.is_syncing = False

        return run_summary

# Singleton instance
sync_scheduler = KECSyncScheduler(interval_hours=24)
