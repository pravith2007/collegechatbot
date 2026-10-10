import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import HOST, PORT, ADMIN_API_KEY
from storage import storage
from rag_engine import rag_engine
from scheduler import scheduler
from auth import verify_admin_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kec_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for initializing RAG seed knowledge and background scheduler."""
    logger.info("Initializing KEC AI Assistant Backend Service...")
    # 1. Pre-seed verified knowledge base into ChromaDB and storage registry
    rag_engine.seed_initial_knowledge(force=False)
    # 2. Start the background synchronization scheduler
    scheduler.start()
    yield
    # Cleanup on shutdown
    logger.info("Shutting down KEC AI Assistant Backend Service...")
    scheduler.shutdown()

app = FastAPI(
    title="KEC AI Assistant - RAG & Website Synchronization Backend",
    description="Automated public website data collector, change detection, ChromaDB RAG, and admin sync scheduler.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits localhost:7000, localhost:5173, etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request / Response Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question in Tamil, English, or Tanglish")
    history: Optional[List[Dict[str, Any]]] = Field(default=[], description="Prior conversation context")

class CitationSource(BaseModel):
    title: str
    url: str
    snippet: str

class ChatResponse(BaseModel):
    response: str
    sources: List[CitationSource]
    is_tamil: bool
    hits_count: int

class IntervalUpdateRequest(BaseModel):
    interval_minutes: int = Field(..., ge=1, le=10080, description="Interval in minutes (1 to 7 days)")

# Public Endpoints
@app.get("/api/health")
def health_check():
    """Health check endpoint showing collection stats and system status."""
    total_docs = len(storage.get_all_documents())
    try:
        total_chunks = rag_engine.collection.count()
    except Exception:
        total_chunks = 0

    return {
        "status": "healthy",
        "service": "KEC AI Assistant Backend",
        "version": "2.0.0",
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "scheduler_running": scheduler.scheduler.running
    }

@app.post("/api/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    """
    Main RAG Chatbot endpoint:
    Retrieves semantically relevant chunks from persistent ChromaDB,
    synthesizes a grounded answer, formats citations, and ensures zero hallucination.
    """
    query = request.message.strip()
    is_tamil = rag_engine.is_tamil_query(query)

    # 1. Retrieve top matching evidence chunks
    hits = rag_engine.query(query, top_k=4)

    # 2. Synthesize grounded answer
    answer, sources = rag_engine.generate_grounded_answer(query, hits)

    return ChatResponse(
        response=answer,
        sources=[CitationSource(**s) for s in sources],
        is_tamil=is_tamil,
        hits_count=len(hits)
    )

# Protected Administrative Endpoints
@app.get("/api/admin/sync/status", dependencies=[Depends(verify_admin_key)])
def get_sync_status():
    """Returns the current synchronization status, scheduling intervals, and recent sync runs."""
    state = storage.get_sync_state()
    history = storage.get_sync_history(limit=10)
    all_docs = storage.get_all_documents()

    return {
        "sync_state": state,
        "total_registered_sources": len(all_docs),
        "history": history
    }

@app.post("/api/admin/sync/trigger", dependencies=[Depends(verify_admin_key)])
def trigger_sync():
    """Manually triggers an immediate synchronization cycle."""
    result = scheduler.trigger_manual_sync()
    return result

@app.post("/api/admin/sync/schedule", dependencies=[Depends(verify_admin_key)])
def update_sync_schedule(body: IntervalUpdateRequest):
    """Configures the automatic synchronization interval in minutes."""
    try:
        scheduler.set_interval(body.interval_minutes)
        return {
            "success": True,
            "message": f"Synchronization interval updated to {body.interval_minutes} minutes.",
            "interval_minutes": body.interval_minutes,
            "next_scheduled_sync": storage.get_sync_state().get("next_scheduled_sync")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/admin/sources", dependencies=[Depends(verify_admin_key)])
def list_sources(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Lists indexed sources with their content hashes, retrieval timestamps, and chunk counts."""
    docs = storage.get_all_documents()
    items = list(docs.values())
    paginated = items[offset : offset + limit]

    return {
        "total": len(items),
        "limit": limit,
        "offset": offset,
        "sources": [
            {
                "url": d.get("url"),
                "title": d.get("title"),
                "content_hash": d.get("content_hash"),
                "retrieved_at": d.get("retrieved_at"),
                "chunks_count": len(d.get("chunk_ids", [])),
                "doc_type": d.get("doc_type", "html")
            }
            for d in paginated
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
