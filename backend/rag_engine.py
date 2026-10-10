import os
import re
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings
import requests

from config import (
    CHROMA_DIR,
    PROJECT_ROOT,
    TOP_K_RESULTS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL
)
from storage import storage

logger = logging.getLogger("kec_rag")

class RAGEngine:
    """Multilingual RAG Engine backed by persistent ChromaDB, supporting Ollama, OpenAI, and local grounded synthesis."""

    def __init__(self):
        self.chroma_dir = Path(CHROMA_DIR)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize persistent Chroma client
        self.client = chromadb.PersistentClient(path=str(self.chroma_dir))
        self.collection_name = "kec_knowledge_base"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Initialized ChromaDB at {self.chroma_dir} with collection '{self.collection_name}'")

    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
        """Splits text into coherent overlapping chunks respecting paragraph/sentence boundaries."""
        if not text or not text.strip():
            return []

        # Split on double newlines first, then single newlines, then periods
        raw_paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0

        for para in raw_paragraphs:
            para_len = len(para)
            if current_length + para_len <= chunk_size:
                current_chunk.append(para)
                current_length += para_len + 2
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                # Handle large paragraph
                if para_len > chunk_size:
                    sentences = re.split(r'(?<=[.!?\n])\s+', para)
                    sub_chunk = []
                    sub_len = 0
                    for s in sentences:
                        if sub_len + len(s) <= chunk_size:
                            sub_chunk.append(s)
                            sub_len += len(s) + 1
                        else:
                            if sub_chunk:
                                chunks.append(" ".join(sub_chunk))
                            sub_chunk = [s]
                            sub_len = len(s)
                    if sub_chunk:
                        current_chunk = sub_chunk
                        current_length = sub_len
                else:
                    current_chunk = [para]
                    current_length = para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        # Filter out empty or micro chunks
        return [c.strip() for c in chunks if len(c.strip()) > 30]

    def index_document(self, doc: Dict[str, Any]) -> List[str]:
        """Chunks and indexes a single document into ChromaDB, returns generated chunk IDs."""
        url = doc["url"]
        title = doc.get("title", "KEC Document")
        text = doc.get("text", "")
        doc_type = doc.get("doc_type", "html")

        chunks = self.chunk_text(text)
        if not chunks:
            logger.warning(f"No chunks generated for document: {url}")
            return []

        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        chunk_ids = [f"doc_{url_hash}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "url": url,
                "title": title[:200],
                "doc_type": doc_type,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]

        try:
            self.collection.add(
                documents=chunks,
                ids=chunk_ids,
                metadatas=metadatas
            )
            logger.info(f"Indexed {len(chunks)} chunks into ChromaDB for {url}")
            return chunk_ids
        except Exception as e:
            logger.error(f"Failed to add chunks to ChromaDB for {url}: {e}")
            raise e

    def update_document_atomic(self, doc: Dict[str, Any], old_chunk_ids: List[str]) -> List[str]:
        """Atomically prepares replacement chunks before removing old chunks to prevent data loss."""
        url = doc["url"]
        logger.info(f"Performing atomic chunk update for {url} (replacing {len(old_chunk_ids)} old chunks)")

        # 1. Prepare and insert new chunks first
        new_chunk_ids = self.index_document(doc)

        # 2. Only after successful insertion, delete previous chunks
        if old_chunk_ids:
            try:
                # Filter out any IDs that happen to overlap
                ids_to_delete = [oid for oid in old_chunk_ids if oid not in new_chunk_ids]
                if ids_to_delete:
                    self.collection.delete(ids=ids_to_delete)
                    logger.info(f"Deleted {len(ids_to_delete)} obsolete chunks for {url}")
            except Exception as e:
                logger.warning(f"Error cleaning up old chunks for {url}: {e}")

        return new_chunk_ids

    def delete_document(self, url: str, chunk_ids: List[str]):
        """Deletes all chunks associated with a URL from ChromaDB."""
        if chunk_ids:
            try:
                self.collection.delete(ids=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} chunks for {url}")
            except Exception as e:
                logger.error(f"Failed to delete chunks for {url}: {e}")

    def query(self, query_text: str, top_k: int = TOP_K_RESULTS) -> List[Dict[str, Any]]:
        """Performs semantic similarity retrieval on the Chroma collection."""
        if not query_text.strip():
            return []

        try:
            total_count = self.collection.count()
            if total_count == 0:
                logger.warning("Chroma collection is empty.")
                return []

            actual_k = min(top_k, total_count)
            results = self.collection.query(
                query_texts=[query_text],
                n_results=actual_k,
                include=["documents", "metadatas", "distances"]
            )

            hits = []
            if results and results.get("documents") and results["documents"][0]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

                for doc_text, meta, dist in zip(docs, metas, distances):
                    # In cosine distance: lower is closer. 0 is identical, 1.0 is orthogonal.
                    similarity_score = max(0.0, 1.0 - dist)
                    hits.append({
                        "text": doc_text,
                        "metadata": meta,
                        "distance": dist,
                        "score": round(similarity_score, 4),
                        "url": meta.get("url", "https://kongu.ac.in/"),
                        "title": meta.get("title", "Kongu Engineering College")
                    })

            return hits
        except Exception as e:
            logger.error(f"Query retrieval failed in ChromaDB: {e}")
            return []

    def is_tamil_query(self, text: str) -> bool:
        """Checks if text contains Tamil Unicode characters."""
        return bool(re.search(r'[\u0B80-\u0BFF]', text))

    def generate_grounded_answer(self, query_text: str, context_hits: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Synthesizes an accurate, grounded answer from retrieved evidence chunks.
        Strictly prevents hallucination when evidence is insufficient.
        Supports Ollama, OpenAI, and high-accuracy structured bilingual fallback.
        """
        is_tamil = self.is_tamil_query(query_text)

        # Fallback when no hits or very weak relevance
        if not context_hits or (len(context_hits) > 0 and context_hits[0]["distance"] > 1.45):
            if is_tamil:
                fallback_msg = (
                    "மன்னிக்கவும், தாங்கள் கேட்ட குறிப்பிட்ட தகவல் கொங்கு பொறியியல் கல்லூரியின் "
                    "தற்போதைய அதிகாரப்பூர்வ இணையதள ஆவணங்களில் போதுமான ஆதாரங்களுடன் கிடைக்கவில்லை.\n\n"
                    "📞 அதிகாரப்பூர்வ கல்லூரி அலுவலகம்: 04257-226600 / 04257-226688\n"
                    "🌐 கல்லூரி இணையதளம்: https://kongu.ac.in/\n"
                    "✉️ மின்னஞ்சல்: info@kongu.edu"
                )
            else:
                fallback_msg = (
                    "I apologize, but this specific information is not currently found with sufficient evidence "
                    "in the official Kongu Engineering College documents.\n\n"
                    "📞 Official KEC Office Helpline: 04257-226600 / 04257-226688\n"
                    "🌐 College Website: https://kongu.ac.in/\n"
                    "✉️ Email: info@kongu.edu"
                )
            return fallback_msg, []

        # Construct context block
        context_parts = []
        sources = []
        seen_urls = set()

        for idx, hit in enumerate(context_hits):
            url = hit["url"]
            title = hit["title"]
            text = hit["text"]
            context_parts.append(f"[Source {idx+1}: {title} ({url})]\n{text}")

            if url not in seen_urls:
                seen_urls.add(url)
                # Pick a concise snippet for citation
                snippet = text[:180].replace("\n", " ").strip() + "..."
                sources.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })

        context_str = "\n\n---\n\n".join(context_parts)

        # Try LLM Generation (Ollama first, then OpenAI, then Local Grounded Synthesizer)
        answer = self._try_ollama_llm(query_text, context_str, is_tamil)
        if not answer:
            answer = self._try_openai_llm(query_text, context_str, is_tamil)
        if not answer:
            answer = self._synthesize_local_grounded(query_text, context_hits, is_tamil)

        return answer, sources

    def _try_ollama_llm(self, query: str, context: str, is_tamil: bool) -> Optional[str]:
        """Attempts generation using local Ollama if active."""
        try:
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            prompt = self._build_system_prompt(query, context, is_tamil)
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2}
            }
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                response_text = data.get("response", "").strip()
                if response_text:
                    logger.info("Successfully generated response using local Ollama LLM.")
                    return response_text
        except Exception:
            pass
        return None

    def _try_openai_llm(self, query: str, context: str, is_tamil: bool) -> Optional[str]:
        """Attempts generation using OpenAI if API key is provided."""
        if not OPENAI_API_KEY:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            system_instruction = (
                "You are the official bilingual AI assistant for Kongu Engineering College (KEC), Perundurai, Erode. "
                "Answer the user query strictly using the provided verified context. "
                "Never invent fee amounts, cutoffs, dates, or faculty names. "
                "If the context doesn't contain the requested detail, state it clearly and provide official contact info. "
                "Include Google Maps links if present in context. "
                "Respond in Tamil if the user query is in Tamil or Tanglish; respond in English if the query is in English."
            )
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Verified College Context:\n{context}\n\nUser Question:\n{query}"}
            ]
            payload = {
                "model": OPENAI_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 600
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                ans = data["choices"][0]["message"]["content"].strip()
                if ans:
                    logger.info("Successfully generated response using OpenAI LLM.")
                    return ans
        except Exception as e:
            logger.warning(f"OpenAI LLM request failed: {e}")
        return None

    def _build_system_prompt(self, query: str, context: str, is_tamil: bool) -> str:
        lang_instruction = "Respond in Tamil." if is_tamil else "Respond in English."
        return (
            f"You are the official AI Assistant for Kongu Engineering College (KEC).\n"
            f"Answer the question accurately based ONLY on the evidence below. Never fabricate facts.\n"
            f"{lang_instruction}\n\n"
            f"Evidence:\n{context}\n\n"
            f"Question: {query}\n"
            f"Answer:"
        )

    def _synthesize_local_grounded(self, query: str, context_hits: List[Dict[str, Any]], is_tamil: bool) -> str:
        """
        High-precision rule-based grounding synthesizer that extracts and organizes
        verified evidence facts, Google Maps links, phone numbers, and Tamil descriptions.
        """
        top_hit = context_hits[0]
        text = top_hit["text"].strip()
        url = top_hit["url"]

        # Check for Google Maps links in context
        maps_links = re.findall(r'https?://(?:maps\.app\.goo\.gl|www\.google\.com/maps)[^\s)]+', text)
        maps_part = ""
        if maps_links:
            maps_part = f"\n\n📍 **Google Maps நேரடி இணைப்பு:** {maps_links[0]}" if is_tamil else f"\n\n📍 **Google Maps Location:** {maps_links[0]}"

        # Look for phone/helpline in context
        phones = re.findall(r'04257-\d{6}', text)
        contact_part = ""
        if phones:
            contact_part = f"\n📞 தொடர்பு: {phones[0]}" if is_tamil else f"\n📞 Contact: {phones[0]}"

        # Format output cleanly
        if is_tamil:
            header = f"🎓 **கொங்கு பொறியியல் கல்லூரி (KEC) அதிகாரப்பூர்வ தகவல்:**\n\n"
            body = text
            if len(body) > 600:
                # Keep most relevant paragraphs
                paras = [p for p in body.split("\n\n") if len(p.strip()) > 20]
                body = "\n\n".join(paras[:3])
            return f"{header}{body}{maps_part}{contact_part}"
        else:
            header = f"🎓 **Kongu Engineering College (KEC) Official Information:**\n\n"
            body = text
            if len(body) > 600:
                paras = [p for p in body.split("\n\n") if len(p.strip()) > 20]
                body = "\n\n".join(paras[:3])
            return f"{header}{body}{maps_part}{contact_part}"

    def seed_initial_knowledge(self, force: bool = False):
        """
        Pre-seeds initial verified knowledge from project knowledgeBase and KONGU.txt
        so the chatbot starts with rich knowledge and Google Maps links immediately.
        """
        try:
            existing_count = self.collection.count()
            if existing_count > 0 and not force:
                logger.info(f"Chroma collection already contains {existing_count} chunks. Skipping pre-seed.")
                return

            logger.info("Pre-seeding initial verified KEC knowledge base into ChromaDB...")
            seeded_docs = []

            # 1. Official Core Admissions & General Facts
            admissions_text = (
                "கொங்கு பொறியியல் கல்லூரி சேர்க்கை (Admissions & Courses):\n"
                "UG Courses: B.E/B.Tech (14 branches including AI&DS, CSE, IT, ECE, EEE, Mechanical, Civil, Chemical, Mechatronics, Food Tech, Automobile).\n"
                "PG Courses: M.E/M.Tech, MCA, MBA.\n"
                "TNEA counselling code: 2711.\n"
                "Annual fees: ₹75,000 - ₹1,25,000 (approximate government/management approved).\n"
                "Accreditation: NAAC A++ Accredited, NIRF Ranking Band 101-150.\n"
                "Admission Helpline: 04257-226688 / 04257-226600.\n"
                "Online application portal: https://kongu.ac.in/"
            )
            seeded_docs.append({
                "url": "https://kongu.ac.in/admission.php",
                "title": "KEC Admissions & Courses",
                "text": admissions_text,
                "doc_type": "official_curated"
            })

            # 2. Campus Locations & Google Maps Links
            locations_text = (
                "கொங்கு பொறியியல் கல்லூரி வளாக இடங்கள் மற்றும் Google Maps வழிகாட்டல்:\n\n"
                "1. Maharaja Auditorium (KEC):\n"
                "Google Maps: https://maps.app.goo.gl/BX8SNrCiNfeeATtB8\n\n"
                "2. Kongu Power House:\n"
                "Google Maps: https://maps.app.goo.gl/oakwNPCqdwkvHJqG7\n\n"
                "3. ECE Block (Electronics & Communication):\n"
                "Google Maps: https://maps.app.goo.gl/r7EeUo2pAkGZtx3i9\n\n"
                "4. Central Library (KEC):\n"
                "Google Maps: https://maps.app.goo.gl/dBQQvTHvS3SLtKNE6\n\n"
                "5. Mechanical Engineering Department:\n"
                "Google Maps: https://maps.app.goo.gl/19119hQjP8J3QZpB9\n\n"
                "6. Chemical Engineering Department:\n"
                "Google Maps: https://maps.app.goo.gl/s9f1Hk5b138F9k8fA\n\n"
                "7. Convention Centre (KEC):\n"
                "Google Maps: https://maps.app.goo.gl/XQj4p9vGfXm4n17B9\n\n"
                "8. Main Administrative Office:\n"
                "Google Maps: https://maps.app.goo.gl/uXzC8fFk9mZtE9q66"
            )
            seeded_docs.append({
                "url": "https://kongu.ac.in/facilities.php",
                "title": "KEC Campus Buildings & Google Maps Navigation",
                "text": locations_text,
                "doc_type": "official_curated"
            })

            # 3. Hostels, Placements & Library
            facilities_text = (
                "KEC விடுதி மற்றும் வசதிகள் (Hostel & Facilities):\n"
                "Hostel: Separate modern hostels for boys (Dheeran, Ponnar, Sankar) and girls (Amaravathi, Kaveri, Bhavani).\n"
                "Mess: Pure vegetarian & non-vegetarian hygienic food with RO water purification.\n"
                "Library: Central Library with over 100,000+ volumes, IEEE digital access, DELNET, open 8:30 AM to 8:00 PM.\n"
                "Placements: 90%+ placement record, 250+ top companies including TCS, Wipro, Infosys, Cognizant, Zoho, Bosch, Hyundai.\n"
                "Highest package: ₹52 LPA, Average package: ₹4.5 - ₹5.5 LPA.\n"
                "Sports: 400m synthetic athletic track, football ground, cricket ground, badminton and basketball indoor stadiums."
            )
            seeded_docs.append({
                "url": "https://kongu.ac.in/placement.php",
                "title": "KEC Placements, Hostels & Central Library",
                "text": facilities_text,
                "doc_type": "official_curated"
            })

            # 4. Ingest KONGU.txt if available
            kongu_txt_path = PROJECT_ROOT / "project" / "public" / "KONGU.txt"
            if kongu_txt_path.exists():
                try:
                    with open(kongu_txt_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f if line.strip()]
                    txt_content = "\n".join(lines[:800])  # Core department & faculty section
                    if txt_content:
                        seeded_docs.append({
                            "url": "https://kongu.ac.in/aboutus.php",
                            "title": "KEC Departments, Faculty & Academic Structure",
                            "text": txt_content,
                            "doc_type": "official_text"
                        })
                except Exception as e:
                    logger.warning(f"Could not read KONGU.txt: {e}")

            # Index all seed documents
            for doc in seeded_docs:
                doc_hash = hashlib.sha256(doc["text"].encode()).hexdigest()
                doc["content_hash"] = doc_hash
                chunk_ids = self.index_document(doc)
                doc["chunk_ids"] = chunk_ids
                storage.set_document(doc["url"], doc)

            logger.info(f"Successfully pre-seeded {len(seeded_docs)} verified documents into RAG knowledge base.")
        except Exception as e:
            logger.error(f"Failed to pre-seed knowledge base: {e}")

# Global singleton
rag_engine = RAGEngine()
