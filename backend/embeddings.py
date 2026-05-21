"""Document loading, chunking, and embedding pipeline.

Default embedding backend is `sentence-transformers/all-MiniLM-L6-v2` so the
prototype runs with zero external API keys. If `OPENAI_API_KEY` is set,
`text-embedding-3-small` is used instead for higher quality retrieval.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------

class EmbeddingBackend:
    """Common interface for embedding providers."""

    name: str = "base"
    dimension: int = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class SentenceTransformerBackend(EmbeddingBackend):
    """Local, free embedding model. ~80MB download on first use."""

    name = "sentence-transformers/all-MiniLM-L6-v2"
    dimension = 384

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vectors.tolist()


class OpenAIBackend(EmbeddingBackend):
    """OpenAI text-embedding-3-small. Requires OPENAI_API_KEY."""

    name = "text-embedding-3-small"
    dimension = 1536

    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI()

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Batch in groups of 100 to stay well under request limits.
        out: list[list[float]] = []
        batch_size = 100
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            resp = self._client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            out.extend(item.embedding for item in resp.data)
        return out


@lru_cache(maxsize=1)
def get_backend() -> EmbeddingBackend:
    """Return the active embedding backend, picking OpenAI if available."""

    if os.environ.get("OPENAI_API_KEY"):
        try:
            backend = OpenAIBackend()
            logger.info("Using OpenAI embedding backend (%s)", backend.name)
            return backend
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to init OpenAI backend, falling back: %s", exc)

    backend = SentenceTransformerBackend()
    logger.info("Using local embedding backend (%s)", backend.name)
    return backend


# ---------------------------------------------------------------------------
# Document ingestion
# ---------------------------------------------------------------------------

SUPPORTED_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
SUPPORTED_PDF_SUFFIXES = {".pdf"}


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def load_documents(docs_dir: str) -> list[dict]:
    """Load every supported file under `docs_dir` (recursive)."""

    base = Path(docs_dir)
    if not base.exists():
        logger.warning("Docs directory not found: %s", base)
        return []

    documents: list[dict] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        try:
            if suffix in SUPPORTED_TEXT_SUFFIXES:
                content = path.read_text(encoding="utf-8")
            elif suffix in SUPPORTED_PDF_SUFFIXES:
                content = _read_pdf(path)
            else:
                continue
        except Exception as exc:
            logger.warning("Skipping %s (%s)", path, exc)
            continue

        if not content.strip():
            continue

        documents.append(
            {
                "content": content,
                "source": path.name,
                "path": str(path.relative_to(base)),
                "title": _derive_title(content, path.name),
            }
        )

    return documents


def _derive_title(content: str, fallback: str) -> str:
    """Pull the first markdown H1 if present; else use the filename."""

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return Path(fallback).stem.replace("_", " ").replace("-", " ").title()


def chunk_documents(documents: Iterable[dict]) -> list[dict]:
    """Split documents into semantic chunks using markdown-aware separators."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks: list[dict] = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for idx, chunk in enumerate(splits):
            cleaned = chunk.strip()
            if len(cleaned) < 40:
                # Skip near-empty chunks (e.g. dangling headers).
                continue
            chunks.append(
                {
                    "text": cleaned,
                    "source": doc["source"],
                    "path": doc["path"],
                    "title": doc["title"],
                    "chunk_id": f"{doc['source']}::chunk_{idx}",
                }
            )
    return chunks


def embed_and_store(chunks: list[dict], collection) -> int:
    """Embed and persist chunks. Returns the number of items stored."""

    if not chunks:
        return 0

    backend = get_backend()
    texts = [c["text"] for c in chunks]
    embeddings = backend.embed(texts)

    collection.upsert(
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "source": c["source"],
                "path": c["path"],
                "title": c["title"],
                "chunk_id": c["chunk_id"],
            }
            for c in chunks
        ],
        ids=[c["chunk_id"] for c in chunks],
    )
    logger.info("Stored %d chunks via %s", len(chunks), backend.name)
    return len(chunks)


def ingest_directory(
    docs_path: str,
    collection_name: str,
    chroma_client,
    *,
    reset: bool = False,
) -> dict:
    """End-to-end: load, chunk, embed, and persist a docs directory into a collection."""

    if reset:
        try:
            chroma_client.delete_collection(collection_name)
        except Exception:  # pragma: no cover - collection may not exist
            pass

    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "l2"},
    )

    documents = load_documents(docs_path)
    chunks = chunk_documents(documents)
    indexed = embed_and_store(chunks, collection)
    return {
        "collection_name": collection_name,
        "documents_loaded": len(documents),
        "chunks_created": len(chunks),
        "chunks_indexed": indexed,
        "sources": sorted({d["source"] for d in documents}),
    }
