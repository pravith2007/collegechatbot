import os
import re
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("kec_text_chunker")

class TextChunker:
    """
    Intelligent bilingual text chunker with Tamil-safe word boundary preservation,
    stable chunk IDs, and JSONL persistence.
    """

    def __init__(
        self,
        chunk_size: int = 700,
        chunk_overlap: int = 120,
        output_file: Optional[Path] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        current_dir = Path(__file__).resolve().parent
        self.output_file = output_file or (current_dir / "data" / "chunks.jsonl")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def is_tamil(self, text: str) -> bool:
        """Checks if text contains Tamil Unicode characters."""
        return bool(re.search(r'[\u0B80-\u0BFF]', text))

    def split_into_semantic_units(self, text: str) -> List[str]:
        """Splits text on headings and paragraphs without breaking Tamil words."""
        # Split primarily on double newlines (paragraphs/headings)
        raw_paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
        units = []
        for p in raw_paragraphs:
            if len(p) <= self.chunk_size:
                units.append(p)
            else:
                # Split along sentence boundaries safely (period followed by space, or newline)
                sentences = re.split(r'(?<=[.!?\n])\s+', p)
                sub_unit = []
                sub_len = 0
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    if sub_len + len(s_clean) <= self.chunk_size:
                        sub_unit.append(s_clean)
                        sub_len += len(s_clean) + 1
                    else:
                        if sub_unit:
                            units.append(" ".join(sub_unit))
                        sub_unit = [s_clean]
                        sub_len = len(s_clean)
                if sub_unit:
                    units.append(" ".join(sub_unit))
        return units

    def chunk_document(
        self,
        text: str,
        source_url: str = "https://kongu.ac.in/",
        page_title: str = "Kongu Engineering College",
        last_fetched: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunks a single document into overlapping units with stable chunk IDs and metadata.
        """
        if not text or not text.strip():
            return []

        semantic_units = self.split_into_semantic_units(text)
        chunks: List[Dict[str, Any]] = []
        current_parts: List[str] = []
        current_len = 0

        # Create stable hash prefix from source URL and text hash
        url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:10]
        timestamp = last_fetched or datetime.now(timezone.utc).isoformat()

        for unit in semantic_units:
            unit_len = len(unit)
            if current_len + unit_len <= self.chunk_size:
                current_parts.append(unit)
                current_len += unit_len + 2
            else:
                if current_parts:
                    chunk_text = "\n\n".join(current_parts).strip()
                    if len(chunk_text) > 30:
                        chunk_idx = len(chunks)
                        stable_id = f"kec_{url_hash}_{chunk_idx}"
                        chunks.append({
                            "id": stable_id,
                            "text": chunk_text,
                            "source_url": source_url,
                            "page_title": page_title,
                            "chunk_index": chunk_idx,
                            "last_fetched": timestamp,
                            "is_tamil": self.is_tamil(chunk_text)
                        })

                # Carry over overlap if possible
                if current_parts and self.chunk_overlap > 0:
                    overlap_unit = current_parts[-1]
                    if len(overlap_unit) < self.chunk_overlap:
                        current_parts = [overlap_unit, unit]
                        current_len = len(overlap_unit) + unit_len + 2
                    else:
                        current_parts = [unit]
                        current_len = unit_len
                else:
                    current_parts = [unit]
                    current_len = unit_len

        if current_parts:
            chunk_text = "\n\n".join(current_parts).strip()
            if len(chunk_text) > 30:
                chunk_idx = len(chunks)
                stable_id = f"kec_{url_hash}_{chunk_idx}"
                chunks.append({
                    "id": stable_id,
                    "text": chunk_text,
                    "source_url": source_url,
                    "page_title": page_title,
                    "chunk_index": chunk_idx,
                    "last_fetched": timestamp,
                    "is_tamil": self.is_tamil(chunk_text)
                })

        return chunks

    def chunk_documents_and_save(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Chunks multiple documents and writes them to persistent JSONL.
        """
        all_chunks = []
        for doc in documents:
            text = doc.get("text") or doc.get("content") or ""
            url = doc.get("url") or doc.get("source_url") or "https://kongu.ac.in/"
            title = doc.get("title") or doc.get("page_title") or "KEC Document"
            fetched = doc.get("last_fetched") or doc.get("fetched")

            doc_chunks = self.chunk_document(
                text=text,
                source_url=url,
                page_title=title,
                last_fetched=fetched
            )
            all_chunks.extend(doc_chunks)

        # Write to JSONL safely
        temp_file = self.output_file.with_suffix(".jsonl.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                for ch in all_chunks:
                    f.write(json.dumps(ch, ensure_ascii=False) + "\n")
            temp_file.replace(self.output_file)
            logger.info(f"Persisted {len(all_chunks)} chunks to {self.output_file}")
        except Exception as e:
            logger.error(f"Failed to persist chunks to JSONL: {e}")
            if temp_file.exists():
                temp_file.unlink()

        return all_chunks

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    chunker = TextChunker()
    sample = "வணக்கம்! கொங்கு பொறியியல் கல்லூரி சேர்க்கை பற்றிய தகவல்.\n\nUG படிப்புகள் மற்றும் PG படிப்புகள் உள்ளன."
    res = chunker.chunk_document(sample, "https://kongu.ac.in/admission.php", "சேர்க்கை")
    print(f"Generated {len(res)} chunks. Sample ID: {res[0]['id']}")
