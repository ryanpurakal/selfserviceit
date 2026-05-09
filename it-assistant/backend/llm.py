"""LLM answer synthesis with graceful fallbacks.

Order of preference:
  1. Google Gemini (gemini-2.5-flash) if GOOGLE_API_KEY (or GEMINI_API_KEY) is set
  2. OpenAI GPT-4o-mini if OPENAI_API_KEY is set
  3. Deterministic template synthesis using the retrieved chunks directly

The template fallback keeps the prototype demoable without any API keys.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are Trumid's internal IT support assistant. Answer the employee's "
    "question using ONLY the provided documentation excerpts. Be concise, "
    "step-by-step, and friendly. If the answer is not contained in the "
    "documentation, say so explicitly and recommend opening a ticket. "
    "Format the response in clean Markdown using short paragraphs and "
    "numbered lists where appropriate. Cite sources inline as `[source]` "
    "when you use them."
)


@dataclass
class LLMResult:
    text: str
    used_llm: bool
    provider: str


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no documentation matched the query)"
    parts = []
    for chunk in chunks:
        source = chunk.get("source", "unknown")
        text = chunk.get("text", "").strip()
        parts.append(f"[Source: {source}]\n{text}")
    return "\n\n---\n\n".join(parts)


def _build_user_prompt(question: str, chunks: list[dict]) -> str:
    return (
        f"Documentation:\n{_format_context(chunks)}\n\n"
        f"Employee question: {question}\n\n"
        "Write the best possible answer."
    )


def _try_gemini(question: str, chunks: list[dict]) -> Optional[LLMResult]:
    # Google's docs use both names interchangeably; accept either.
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:  # pragma: no cover
        logger.warning("google-genai package not installed")
        return None

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=_build_user_prompt(question, chunks),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            return None
        return LLMResult(text=text, used_llm=True, provider="gemini")
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


def _try_openai(question: str, chunks: list[dict]) -> Optional[LLMResult]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:  # pragma: no cover
        return None

    try:
        client = OpenAI()
        completion = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(question, chunks)},
            ],
        )
        text = (completion.choices[0].message.content or "").strip()
        return LLMResult(text=text, used_llm=True, provider="openai")
    except Exception as exc:
        logger.warning("OpenAI call failed: %s", exc)
        return None


def _template_answer(question: str, chunks: list[dict]) -> LLMResult:
    """Deterministic, no-API-key fallback that still feels useful.

    Stitches the most relevant chunks into a structured Markdown answer with
    inline citations so the demo works offline.
    """

    if not chunks:
        body = (
            "I couldn't find anything in the knowledge base that matches your "
            "question. If this is blocking you, please open a ticket so the IT "
            "team can take a look."
        )
        return LLMResult(text=body, used_llm=False, provider="template")

    intro = (
        f"Here's what the IT knowledge base says about **{question.strip().rstrip('?')}**:"
    )

    bullets: list[str] = []
    seen_sources: set[str] = set()
    for chunk in chunks[:3]:
        snippet = chunk.get("text", "").strip().replace("\n", " ")
        if len(snippet) > 320:
            snippet = snippet[:317].rsplit(" ", 1)[0] + "..."
        source = chunk.get("source", "unknown")
        bullets.append(f"- {snippet} _[{source}]_")
        seen_sources.add(source)

    closing = (
        "\nIf this didn't fully resolve the issue, click **No, create a ticket** "
        "below and the IT team will follow up with the context preserved."
    )

    text = f"{intro}\n\n" + "\n".join(bullets) + "\n" + closing
    return LLMResult(text=text, used_llm=False, provider="template")


def generate_answer(question: str, context_chunks: list[dict]) -> LLMResult:
    """Synthesize an answer, preferring real LLMs but falling back gracefully."""

    for attempt in (_try_gemini, _try_openai):
        result = attempt(question, context_chunks)
        if result and result.text:
            return result

    return _template_answer(question, context_chunks)
