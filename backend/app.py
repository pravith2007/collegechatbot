import os
import logging
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import HOST, PORT, ADMIN_API_KEY
from storage import storage
from rag_pipeline import rag_pipeline
from scheduler import sync_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kec_flask_app")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Start the background sync scheduler (non-blocking)
sync_scheduler.start()

def require_admin_auth(f):
    """Decorator ensuring administrator authentication via X-Admin-Key or Bearer token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-Admin-Key")
        if not key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                key = auth_header[7:].strip()

        if not key or key.strip() != ADMIN_API_KEY:
            logger.warning(f"Unauthorized admin access attempt from {request.remote_addr}")
            return jsonify({"error": "Unauthorized. Invalid or missing Administrator API Key."}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint displaying total knowledge sources, ChromaDB chunks, and scheduler status."""
    total_docs = len(storage.get_all_documents())
    try:
        total_chunks = rag_pipeline.collection.count()
    except Exception:
        total_chunks = 0

    return jsonify({
        "status": "healthy",
        "service": "KEC AI Assistant Flask Backend",
        "version": "2.1.0",
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "scheduler_running": sync_scheduler.scheduler.running
    })

@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    """
    Main conversational RAG endpoint for students and parents.
    Retrieves evidence from ChromaDB, validates relevance, and generates grounded Tamil or English answers.
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("message") or data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "Message content is required"}), 400

    result = rag_pipeline.answer_question(query)

    # Format response compatible with both frontend interfaces
    return jsonify({
        "response": result["answer"],
        "answer": result["answer"],
        "sources": result["sources"],
        "is_tamil": result["is_tamil"],
        "confidence": result["confidence"],
        "hits_count": len(result["sources"])
    })

@app.route("/api/admin/sync-status", methods=["GET"])
@app.route("/api/admin/sync/status", methods=["GET"])
@require_admin_auth
def get_sync_status():
    """
    Returns synchronization metrics: last success, next scheduled run, pages processed/changed, and errors.
    """
    state = storage.get_sync_state()
    history = storage.get_sync_history(limit=10)
    all_docs = storage.get_all_documents()
    try:
        total_chunks = rag_pipeline.collection.count()
    except Exception:
        total_chunks = state.get("total_chunks", 0)

    return jsonify({
        "last_successful_sync": state.get("last_successful_sync"),
        "last_attempted_sync": state.get("last_attempted_sync"),
        "sync_status": state.get("status", "idle"),
        "status": state.get("status", "idle"),
        "pages_processed": state.get("pages_checked", 0),
        "pages_changed": state.get("pages_changed", 0),
        "chunks_updated": state.get("chunks_updated", 0),
        "pages_failed": state.get("pages_failed", 0),
        "next_scheduled_run": state.get("next_scheduled_sync"),
        "total_chunks": total_chunks,
        "total_registered_sources": len(all_docs),
        "sync_state": state,
        "history": history
    })

@app.route("/api/admin/sync-knowledge", methods=["POST"])
@app.route("/api/admin/sync/trigger", methods=["POST"])
@require_admin_auth
def trigger_sync_knowledge():
    """Manually triggers immediate KEC website scraping, KONGU.txt updating, and ChromaDB re-indexing."""
    result = sync_scheduler.trigger_manual_sync()
    return jsonify(result)

@app.route("/api/admin/sync/schedule", methods=["POST"])
@require_admin_auth
def update_schedule():
    """Configures the background synchronization interval in minutes."""
    data = request.get_json(silent=True) or {}
    minutes = data.get("interval_minutes")

    if not minutes or not isinstance(minutes, int) or minutes < 1:
        return jsonify({"error": "interval_minutes must be an integer >= 1"}), 400

    try:
        sync_scheduler.set_interval_minutes(minutes)
        return jsonify({
            "success": True,
            "message": f"Sync interval set to {minutes} minutes.",
            "interval_minutes": minutes,
            "next_scheduled_run": storage.get_sync_state().get("next_scheduled_sync")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/admin/sources", methods=["GET"])
@require_admin_auth
def get_sources_list():
    """Lists indexed sources with their content hashes and last fetched dates."""
    docs = storage.get_all_documents()
    return jsonify({
        "total": len(docs),
        "sources": [
            {
                "url": d.get("url"),
                "title": d.get("title"),
                "content_hash": d.get("content_hash"),
                "last_fetched": d.get("last_fetched") or d.get("retrieved_at"),
                "chunks_count": len(d.get("chunk_ids", [])),
                "doc_type": d.get("doc_type", "html")
            }
            for d in docs.values()
        ]
    })

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
