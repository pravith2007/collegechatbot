import json
import logging
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Any, Optional, List
from config import REGISTRY_PATH, DEFAULT_SYNC_INTERVAL_MINUTES

logger = logging.getLogger("kec_storage")

class SyncStorage:
    """Thread-safe persistent storage for document registry and sync states."""
    
    def __init__(self, file_path: Path = REGISTRY_PATH):
        self.file_path = file_path
        self._lock = Lock()
        self._data: Dict[str, Any] = {
            "documents": {},  # url -> { url, title, content_hash, retrieved_at, chunk_ids, doc_type, word_count }
            "sync_state": {
                "status": "idle",  # idle | running | completed | error
                "last_successful_sync": None,
                "next_scheduled_sync": None,
                "interval_minutes": DEFAULT_SYNC_INTERVAL_MINUTES,
                "pages_checked": 0,
                "pages_changed": 0,
                "pages_failed": 0,
                "total_chunks": 0,
                "last_error": None,
                "active_job_id": None
            },
            "sync_history": []
        }
        self._load()

    def _load(self):
        with self._lock:
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if "documents" in loaded:
                            self._data["documents"] = loaded["documents"]
                        if "sync_state" in loaded:
                            self._data["sync_state"].update(loaded["sync_state"])
                        if "sync_history" in loaded:
                            self._data["sync_history"] = loaded["sync_history"]
                    logger.info(f"Loaded {len(self._data['documents'])} registered documents from {self.file_path}")
                except Exception as e:
                    logger.error(f"Error reading registry file {self.file_path}: {e}")
            else:
                self._save_unlocked()

    def _save_unlocked(self):
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.file_path)
        except Exception as e:
            logger.error(f"Failed to persist sync registry: {e}")

    def get_document(self, url: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._data["documents"].get(url)

    def get_all_documents(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._data["documents"])

    def set_document(self, url: str, doc_data: Dict[str, Any]):
        with self._lock:
            self._data["documents"][url] = doc_data
            self._recalculate_total_chunks()
            self._save_unlocked()

    def remove_document(self, url: str):
        with self._lock:
            if url in self._data["documents"]:
                del self._data["documents"][url]
                self._recalculate_total_chunks()
                self._save_unlocked()

    def _recalculate_total_chunks(self):
        total = sum(len(d.get("chunk_ids", [])) for d in self._data["documents"].values())
        self._data["sync_state"]["total_chunks"] = total

    def get_sync_state(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data["sync_state"])

    def update_sync_state(self, **kwargs):
        with self._lock:
            self._data["sync_state"].update(kwargs)
            self._save_unlocked()

    def record_sync_run(self, run_summary: Dict[str, Any]):
        with self._lock:
            # Keep the latest 50 history entries
            history = self._data.get("sync_history", [])
            history.insert(0, run_summary)
            self._data["sync_history"] = history[:50]
            self._save_unlocked()

    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._data["sync_history"][:limit])

# Global instance
storage = SyncStorage()
