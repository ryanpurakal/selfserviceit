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

# Each assistant searches its own Chroma collection.
COLLECTION_SOURCES: dict[str, Path] = {
    "it_docs": DOCS_DIR / "it",
    "onboarding_docs": DOCS_DIR / "onboarding",
}
ALLOWED_COLLECTIONS = frozenset(COLLECTION_SOURCES)

DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False, allow_reset=True),
)

analytics = AnalyticsStore(ANALYTICS_PATH)


def get_collection(name: str):
    if name not in ALLOWED_COLLECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown collection_name {name!r}. Allowed: {sorted(ALLOWED_COLLECTIONS)}",
        )
    return chroma_client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "l2"},
    )


def _ingest_all(*, reset: bool = False) -> list[dict]:
    stats: list[dict] = []
    for collection_name, docs_path in COLLECTION_SOURCES.items():
        if not docs_path.exists():
            logger.warning("Docs path not found, skipping %s: %s", collection_name, docs_path)
            continue
        stats.append(
            ingest_directory(
                str(docs_path),
                collection_name,
                chroma_client,
                reset=reset,
            )
        )
    return stats


# ---------------------------------------------------------------------------
# Lifespan: auto-ingest the bundled docs on first run
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        for collection_name in COLLECTION_SOURCES:
            coll = get_collection(collection_name)
            if coll.count() == 0:
                docs_path = COLLECTION_SOURCES[collection_name]
                if docs_path.exists():
                    logger.info(
                        "Empty collection %r detected, auto-ingesting %s",
                        collection_name,
                        docs_path,
                    )
                    stats = ingest_directory(
                        str(docs_path),
                        collection_name,
                        chroma_client,
                    )
                    logger.info("Initial ingestion for %s: %s", collection_name, stats)
            else:
                logger.info(
                    "ChromaDB ready: %r has %d chunks",
                    collection_name,
                    coll.count(),
                )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Initial ingestion failed: %s", exc)
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
    collections = {
        name: get_collection(name).count() for name in COLLECTION_SOURCES
    }
    return {
        "status": "ok",
        "indexed_chunks": sum(collections.values()),
        "collections": collections,
        "docs_dir": str(DOCS_DIR),
    }


@app.post("/embed", response_model=IngestionResponse)
async def embed(
    reset: bool = False,
    collection_name: str | None = None,
) -> IngestionResponse:
    """(Re)ingest documentation. Ingests all collections unless `collection_name` is set."""

    if collection_name is not None:
        if collection_name not in ALLOWED_COLLECTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown collection_name {collection_name!r}",
            )
        docs_path = COLLECTION_SOURCES[collection_name]
        if not docs_path.exists():
            raise HTTPException(status_code=404, detail=f"Docs dir not found: {docs_path}")
        stats = ingest_directory(
            str(docs_path),
            collection_name,
            chroma_client,
            reset=reset,
        )
        return IngestionResponse(**stats)

    if not DOCS_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Docs dir not found: {DOCS_DIR}")

    all_stats = _ingest_all(reset=reset)
    if not all_stats:
        raise HTTPException(status_code=404, detail="No document collections found to ingest")

    combined = {
        "collection_name": "all",
        "documents_loaded": sum(s["documents_loaded"] for s in all_stats),
        "chunks_created": sum(s["chunks_created"] for s in all_stats),
        "chunks_indexed": sum(s["chunks_indexed"] for s in all_stats),
        "sources": sorted({src for s in all_stats for src in s["sources"]}),
    }
    return IngestionResponse(**combined)


@app.post("/ask", response_model=AnswerResponse)
async def ask(question: Question) -> AnswerResponse:
    collection_name = question.collection_name or "it_docs"
    collection = get_collection(collection_name)

    if collection.count() == 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Knowledge base {collection_name!r} is empty. "
                "POST /embed to ingest documentation."
            ),
        )

    results = semantic_search(
        question.query,
        collection,
        collection_name=collection_name,
        top_k=5,
    )
    llm_result = generate_answer(question.query, results)
    confidence = calculate_confidence(results)
    related = get_related_topics(
        question.query,
        collection,
        collection_name=collection_name,
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
