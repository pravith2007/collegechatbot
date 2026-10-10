import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import chromadb
import requests

from config import (
    CHROMA_DIR,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODELS,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    TOP_K_RESULTS
)

logger = logging.getLogger("kec_rag_pipeline")

class RAGPipeline:
    """
    Complete multilingual RAG pipeline for KEC AI Assistant:
    - Persistent ChromaDB vector storage
    - Stable incremental chunk indexing without duplicates
    - Semantic similarity retrieval for Tamil and English queries
    - Relevance validation and zero-hallucination grounded answering
    - Multi-provider LLM support (Ollama local model, OpenAI, or grounded synthesizer)
    """

    def __init__(self, chroma_path: Optional[Path] = None):
        self.chroma_path = chroma_path or Path(CHROMA_DIR)
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(self.chroma_path))
        self.collection_name = "kec_knowledge_base"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Connected to persistent ChromaDB at {self.chroma_path} (Collection: {self.collection_name})")

    def is_tamil(self, text: str) -> bool:
        """Determines if query or text contains Tamil characters."""
        return bool(re.search(r'[\u0B80-\u0BFF]', text))

    def update_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Inserts or updates chunks incrementally in ChromaDB.
        Guarantees that duplicate chunks are prevented and source metadata is preserved.
        """
        if not chunks:
            return {"inserted": 0, "total": self.collection.count()}

        doc_texts = []
        ids = []
        metadatas = []

        for ch in chunks:
            chunk_id = ch["id"]
            text = ch["text"]
            doc_texts.append(text)
            ids.append(chunk_id)
            metadatas.append({
                "source_url": ch.get("source_url", "https://kongu.ac.in/"),
                "page_title": (ch.get("page_title") or "KEC Document")[:200],
                "chunk_index": ch.get("chunk_index", 0),
                "last_fetched": ch.get("last_fetched", "")
            })

        # Upsert into ChromaDB in batches to prevent memory spikes
        batch_size = 50
        inserted_count = 0
        for i in range(0, len(ids), batch_size):
            b_ids = ids[i : i + batch_size]
            b_texts = doc_texts[i : i + batch_size]
            b_meta = metadatas[i : i + batch_size]
            try:
                self.collection.upsert(
                    documents=b_texts,
                    ids=b_ids,
                    metadatas=b_meta
                )
                inserted_count += len(b_ids)
            except Exception as e:
                logger.error(f"Error upserting chunk batch {i}-{i+len(b_ids)}: {e}")

        total_in_db = self.collection.count()
        logger.info(f"Successfully upserted {inserted_count} chunks. Collection total: {total_in_db}")
        return {"inserted": inserted_count, "total": total_in_db}

    def remove_stale_chunks(self, chunk_ids_to_remove: List[str]):
        """Safely deletes outdated or removed chunk IDs from ChromaDB."""
        if chunk_ids_to_remove:
            try:
                self.collection.delete(ids=chunk_ids_to_remove)
                logger.info(f"Deleted {len(chunk_ids_to_remove)} stale chunks from ChromaDB.")
            except Exception as e:
                logger.error(f"Failed to delete stale chunks: {e}")

    def retrieve_relevant_chunks(self, query: str, top_k: int = TOP_K_RESULTS) -> List[Dict[str, Any]]:
        """
        Retrieves top-k semantically relevant chunks with distance scores and relevance validation.
        """
        if not query.strip():
            return []

        try:
            total_docs = self.collection.count()
            if total_docs == 0:
                logger.warning("ChromaDB collection is empty.")
                return []

            k = min(top_k, total_docs)
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )

            hits = []
            if results and results.get("documents") and results["documents"][0]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

                for text, meta, dist in zip(docs, metas, distances):
                    similarity = max(0.0, 1.0 - dist)
                    hits.append({
                        "text": text,
                        "metadata": meta,
                        "distance": dist,
                        "similarity_score": round(similarity, 4),
                        "source_url": meta.get("source_url", "https://kongu.ac.in/"),
                        "page_title": meta.get("page_title", "Kongu Engineering College")
                    })

            # Filter out chunks that exceed cosine distance threshold
            valid_hits = [h for h in hits if h["distance"] <= 1.55]
            return valid_hits if valid_hits else hits[:2] if (hits and hits[0]["distance"] <= 1.70) else []
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []

    def answer_question(self, query: str) -> Dict[str, Any]:
        """
        End-to-end question answering pipeline:
        Retrieval -> Relevance Validation -> Grounded LLM/Synthesizer -> Citations
        """
        query_text = query.strip()
        is_tamil = self.is_tamil(query_text)
        hits = self.retrieve_relevant_chunks(query_text, top_k=TOP_K_RESULTS)

        # Insufficient evidence fallback
        if not hits:
            if is_tamil:
                fallback = (
                    "மன்னிக்கவும், தாங்கள் கேட்ட தகவல் கொங்கு பொறியியல் கல்லூரியின் "
                    "தற்போதைய அதிகாரப்பூர்வ ஆவணங்களில் கிடைக்கவில்லை.\n\n"
                    "📞 கல்லூரி அலுவலக உதவி எண்: 04257-226600 / 04257-226688\n"
                    "🌐 கல்லூரி இணையதளம்: https://kongu.ac.in/\n"
                    "✉️ மின்னஞ்சல்: info@kongu.edu"
                )
            else:
                fallback = (
                    "I could not find reliable information for your query in the current official "
                    "Kongu Engineering College knowledge base.\n\n"
                    "📞 Official College Helpline: 04257-226600 / 04257-226688\n"
                    "🌐 College Website: https://kongu.ac.in/\n"
                    "✉️ Email: info@kongu.edu"
                )
            return {
                "answer": fallback,
                "sources": [],
                "is_tamil": is_tamil,
                "confidence": 0.0
            }

        # Build citations list
        sources = []
        seen_urls = set()
        context_blocks = []

        for idx, h in enumerate(hits):
            url = h["source_url"]
            title = h["page_title"]
            text = h["text"]
            context_blocks.append(f"[Source {idx+1}: {title} ({url})]\n{text}")

            if url not in seen_urls:
                seen_urls.add(url)
                snippet = text[:180].replace("\n", " ").strip() + "..."
                sources.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })

        context_str = "\n\n---\n\n".join(context_blocks)

        # 1. Try Google Gemini API (Primary LLM)
        answer = self._generate_gemini(query_text, context_str, is_tamil)
        # 2. Try local Ollama model (qwen2.5:3b / llama3)
        if not answer:
            answer = self._generate_ollama(query_text, context_str, is_tamil)
        # 3. Try OpenAI if configured
        if not answer:
            answer = self._generate_openai(query_text, context_str, is_tamil)
        # 4. Use grounded local synthesizer
        if not answer:
            answer = self._generate_local_grounded(query_text, hits, is_tamil)

        return {
            "answer": answer,
            "sources": sources,
            "is_tamil": is_tamil,
            "confidence": hits[0]["similarity_score"] if hits else 0.5
        }

    def _generate_gemini(self, query: str, context: str, is_tamil: bool) -> Optional[str]:
        """Calls Google Gemini API using the provided API key with automatic model fallback."""
        if not GEMINI_API_KEY:
            return None

        if is_tamil:
            lang_instruction = (
                "பயனர் தமிழில் அல்லது Tanglish-ல் கேட்டுள்ளார். "
                "கொங்கு பொறியியல் கல்லூரியின் (KEC) அதிகாரப்பூர்வ AI உதவியாளராக "
                "முழுமையான, மரியாதையான மற்றும் தெளிவான தமிழில் (fluent Tamil) பதிலளிக்கவும். "
                "முக்கியமான தொழில்நுட்ப பெயர்கள் மற்றும் எண்களை (எ.கா: B.E/B.Tech, கட்டணம், 04257-226688) தெளிவாக குறிப்பிடவும்."
            )
        else:
            lang_instruction = (
                "The user asked in English. Respond as the official AI Assistant for Kongu Engineering College (KEC) "
                "in clear, professional, friendly, and structured English."
            )

        system_instruction = (
            "You are the official Bilingual AI Assistant for Kongu Engineering College (KEC), Perundurai, Erode, Tamil Nadu.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Base your answer strictly and accurately on the provided verified College Evidence below. Never fabricate cutoff marks, courses, or fake fees.\n"
            "2. If contact numbers (e.g., 04257-226688 / 04257-226600), email (info@kongu.edu), official website links (https://kongu.ac.in/), or Google Maps location links are in the evidence, preserve and highlight them.\n"
            "3. Structure your response cleanly using bullet points, bold headers, and appropriate emojis (🎓, 🏛️, 📍, 📞, 🌐, 💼, 🏆).\n"
            "4. Be polite, direct, concise, and helpful to students, parents, and visitors.\n"
            f"{lang_instruction}"
        )

        prompt = (
            f"{system_instruction}\n\n"
            f"--- VERIFIED COLLEGE EVIDENCE ---\n"
            f"{context}\n\n"
            f"--- USER QUESTION ---\n"
            f"{query}\n\n"
            f"--- OFFICIAL ASSISTANT ANSWER ---"
        )

        candidate_models = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]

        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1024
                }
            }
            try:
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                        text = candidates[0]["content"]["parts"][0].get("text", "").strip()
                        if text:
                            logger.info(f"Successfully generated response with Gemini ({model}).")
                            return text
                elif res.status_code in (429, 503):
                    logger.warning(f"Gemini model {model} returned {res.status_code} (busy/rate limit), trying next fallback...")
                    continue
                else:
                    logger.warning(f"Gemini API returned status {res.status_code} on {model}: {res.text[:150]}")
            except Exception as e:
                logger.warning(f"Error calling Gemini model {model}: {e}")
                continue

        return None

    def _generate_ollama(self, query: str, context: str, is_tamil: bool) -> Optional[str]:
        """Calls local Ollama model if running."""
        try:
            url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            lang_prompt = "Respond in fluent Tamil." if is_tamil else "Respond in English."
            prompt = (
                f"You are the official AI Assistant for Kongu Engineering College (KEC).\n"
                f"Answer the question based strictly on the verified evidence below. Never fabricate facts.\n"
                f"{lang_prompt}\n\n"
                f"Evidence:\n{context}\n\n"
                f"Question: {query}\n"
                f"Answer:"
            )
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2}
            }
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                text = res.json().get("response", "").strip()
                if text:
                    logger.info("Generated response with Ollama LLM.")
                    return text
        except Exception:
            pass
        return None

    def _generate_openai(self, query: str, context: str, is_tamil: bool) -> Optional[str]:
        """Calls OpenAI API if API key is provided."""
        if not OPENAI_API_KEY:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            system = (
                "You are the official bilingual assistant for Kongu Engineering College (KEC). "
                "Answer using only the provided college evidence. "
                "Never invent fees, cutoff marks, or faculty names. "
                "Preserve Google Maps links if present in the text."
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ]
            payload = {
                "model": OPENAI_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 500
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                ans = res.json()["choices"][0]["message"]["content"].strip()
                if ans:
                    logger.info("Generated response with OpenAI.")
                    return ans
        except Exception as e:
            logger.warning(f"OpenAI error: {e}")
        return None

    def _generate_local_grounded(self, query: str, hits: List[Dict[str, Any]], is_tamil: bool) -> str:
        """Grounded synthesis formatting verified evidence facts and Google Maps links."""
        top_hit = hits[0]
        text = top_hit["text"].strip()

        # Extract Google Maps links
        maps = re.findall(r'https?://(?:maps\.app\.goo\.gl|www\.google\.com/maps)[^\s)]+', text)
        maps_str = ""
        if maps:
            maps_str = f"\n\n📍 **Google Maps நேரடி வழிகாட்டல்:** {maps[0]}" if is_tamil else f"\n\n📍 **Google Maps Location:** {maps[0]}"

        # Extract phone contacts
        phones = re.findall(r'04257-\d{6}', text)
        phone_str = ""
        if phones:
            phone_str = f"\n📞 தொடர்பு: {phones[0]}" if is_tamil else f"\n📞 Contact: {phones[0]}"

        header = "🎓 **கொங்கு பொறியியல் கல்லூரி (KEC) அதிகாரப்பூர்வ தகவல்:**\n\n" if is_tamil else "🎓 **Kongu Engineering College (KEC) Official Information:**\n\n"
        
        # Clean paragraphs
        paras = [p for p in text.split("\n\n") if len(p.strip()) > 20]
        body = "\n\n".join(paras[:3]) if len(paras) > 3 else text

        return f"{header}{body}{maps_str}{phone_str}"

# Singleton pipeline instance
rag_pipeline = RAGPipeline()
