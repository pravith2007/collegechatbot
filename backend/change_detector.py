import logging
from typing import Dict, Any, List, Tuple
from storage import storage

logger = logging.getLogger("kec_change_detector")

class ChangeDetector:
    """Detects new, modified, and unchanged documents based on SHA-256 content hashes."""

    @staticmethod
    def classify_documents(collected_docs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Classifies incoming collected documents into:
        - unchanged: hash matches existing stored document -> skip embedding/indexing
        - modified: hash is different -> reindex with atomic chunk swap
        - new: url does not exist in registry -> chunk & index
        - failed: document fetch failed -> track for error reporting
        """
        results = {
            "unchanged": [],
            "modified": [],
            "new": [],
            "failed": []
        }

        for doc in collected_docs:
            if not doc.get("success"):
                results["failed"].append(doc)
                continue

            url = doc["url"]
            new_hash = doc["content_hash"]
            existing = storage.get_document(url)

            if existing is None:
                logger.info(f"[NEW DOCUMENT] Discovered: {url}")
                results["new"].append(doc)
            elif existing.get("content_hash") == new_hash:
                logger.debug(f"[UNCHANGED] Content hash matched for: {url}")
                results["unchanged"].append(doc)
            else:
                logger.info(f"[MODIFIED] Content hash changed for: {url} ({existing.get('content_hash')[:8]} -> {new_hash[:8]})")
                doc["previous_chunk_ids"] = existing.get("chunk_ids", [])
                results["modified"].append(doc)

        logger.info(
            f"Classification summary: "
            f"{len(results['new'])} new, "
            f"{len(results['modified'])} modified, "
            f"{len(results['unchanged'])} unchanged, "
            f"{len(results['failed'])} failed."
        )
        return results
