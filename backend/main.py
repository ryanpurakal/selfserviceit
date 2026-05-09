"""FastAPI app exposing the self-service IT assistant."""

from __future__ import annotations

import logging
import os

# These env vars MUST be set before chromadb / transformers are imported below.
# - TOKENIZERS_PARALLELISM avoids a HuggingFace `tokenizers` fork warning
#   ("leaked semaphore objects to clean up at shutdown") when uvicorn --reload
#   tears down the worker.
# - ANONYMIZED_TELEMETRY belt-and-braces alongside our Settings() flag below.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# ChromaDB 0.5.x ships a PostHog telemetry client whose `capture()` signature
# is incompatible with posthog>=4. Even with telemetry disabled the noisy
# error logs leak through, so silence that specific logger.
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from contextlib import asynccontextmanager
from pathlib import Path

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from analytics import AnalyticsStore
from embeddings import ingest_directory
from llm import generate_answer
from models import (
    AnalyticsResponse,
    AnswerResponse,
    DeflectionFeedback,
    EscalationRequest,
    EscalationResponse,
    IngestionResponse,
    Question,
    Source,
)
from retrieval import calculate_confidence, get_related_topics, semantic_search

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("it-assistant")

# ---------------------------------------------------------------------------
# Paths and persistent stores
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
DOCS_DIR = Path(os.environ.get("DOCS_DIR", DATA_DIR / "docs"))
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", DATA_DIR / "chroma_db"))
ANALYTICS_PATH = Path(os.environ.get("ANALYTICS_PATH", DATA_DIR / "analytics.json"))
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION", "it_docs")

DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False, allow_reset=True),
)
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "l2"},
)

analytics = AnalyticsStore(ANALYTICS_PATH)


# ---------------------------------------------------------------------------
# Lifespan: auto-ingest the bundled docs on first run
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI):
    if collection.count() == 0 and DOCS_DIR.exists():
        logger.info("Empty collection detected, auto-ingesting %s", DOCS_DIR)
        try:
            stats = ingest_directory(str(DOCS_DIR), collection)
            logger.info("Initial ingestion: %s", stats)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Initial ingestion failed: %s", exc)
    else:
        logger.info(
            "ChromaDB ready with %d chunks in collection %r",
            collection.count(),
            COLLECTION_NAME,
        )
    yield


app = FastAPI(
    title="Trumid Self-Service IT Assistant",
    version="0.1.0",
    description=(
        "RAG-powered IT support that deflects common tickets and escalates "
        "the rest with full context preserved."
    ),
    lifespan=lifespan,
)

# Frontend is served separately (Vite dev server on :5173 or any static host).
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "indexed_chunks": collection.count(),
        "docs_dir": str(DOCS_DIR),
    }


@app.post("/embed", response_model=IngestionResponse)
async def embed(reset: bool = False) -> IngestionResponse:
    """(Re)ingest every supported file in `data/docs`."""

    if reset:
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
        except Exception:  # pragma: no cover - defensive
            pass
        global collection
        collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "l2"},
        )

    if not DOCS_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Docs dir not found: {DOCS_DIR}")

    stats = ingest_directory(str(DOCS_DIR), collection)
    return IngestionResponse(**stats)


@app.post("/ask", response_model=AnswerResponse)
async def ask(question: Question) -> AnswerResponse:
    if collection.count() == 0:
        raise HTTPException(
            status_code=409,
            detail="Knowledge base is empty. POST /embed to ingest documentation.",
        )

    results = semantic_search(question.query, collection, top_k=5)
    llm_result = generate_answer(question.query, results)
    confidence = calculate_confidence(results)
    related = get_related_topics(
        question.query,
        collection,
        exclude_sources={r["source"] for r in results[:2]},
    )

    question_id = analytics.record_question(
        query=question.query,
        confidence=confidence,
        sources=[r["source"] for r in results],
        used_llm=llm_result.used_llm,
    )

    return AnswerResponse(
        question_id=question_id,
        answer=llm_result.text,
        sources=[
            Source(
                text=r["text"],
                source=r["source"],
                relevance=r["score"],
                chunk_id=r["chunk_id"],
            )
            for r in results
        ],
        confidence=confidence,
        related_topics=related,
        used_llm=llm_result.used_llm,
    )


@app.post("/feedback")
async def feedback(payload: DeflectionFeedback) -> dict:
    found = analytics.record_feedback(payload.question_id, payload.deflected)
    if not found:
        raise HTTPException(status_code=404, detail="Unknown question_id")
    return {"ok": True}


@app.post("/escalate", response_model=EscalationResponse)
async def escalate(payload: EscalationRequest) -> EscalationResponse:
    record = analytics.record_escalation(
        question_id=payload.question_id,
        original_question=payload.original_question,
        attempted_solutions=payload.attempted_solutions,
        user_feedback=payload.user_feedback,
        user_email=payload.user_email,
    )
    return EscalationResponse(
        ticket_id=record["ticket_id"],
        message="Ticket created. The IT team will follow up with the context preserved.",
        created_at=record["created_at"],
    )


@app.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics() -> AnalyticsResponse:
    return AnalyticsResponse(**analytics.snapshot())


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=True,
    )
