"""Lightweight JSON-backed analytics store.

Real production deployments would write to Postgres / a warehouse, but for a
prototype demo a single JSON file gives us persistence between restarts with
zero infrastructure.
"""

from __future__ import annotations

import json
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

# Conservative estimate based on Trumid's 50 tickets/day figure and typical
# tier-1 IT triage time. Easy to tune in the demo.
MINUTES_SAVED_PER_DEFLECTION = 12


class AnalyticsStore:
    """File-backed event store with in-memory caching."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._data: dict[str, list[dict[str, Any]]] = {
            "questions": [],
            "escalations": [],
        }
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
                self._data.setdefault("questions", [])
                self._data.setdefault("escalations", [])
            except json.JSONDecodeError:
                # Corrupt file - start fresh but back up the old one.
                backup = self._path.with_suffix(self._path.suffix + ".bak")
                self._path.rename(backup)

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, default=str), encoding="utf-8")
        tmp.replace(self._path)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_question(
        self,
        *,
        query: str,
        confidence: float,
        sources: list[str],
        used_llm: bool,
    ) -> str:
        question_id = uuid4().hex[:12]
        with self._lock:
            self._data["questions"].append(
                {
                    "id": question_id,
                    "query": query,
                    "confidence": confidence,
                    "sources": sources,
                    "used_llm": used_llm,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._flush()
        return question_id

    def record_feedback(self, question_id: str, deflected: bool) -> bool:
        with self._lock:
            for q in self._data["questions"]:
                if q["id"] == question_id:
                    q["status"] = "deflected" if deflected else "escalated"
                    q["resolved_at"] = datetime.now(timezone.utc).isoformat()
                    self._flush()
                    return True
        return False

    def record_escalation(
        self,
        *,
        question_id: str | None,
        original_question: str,
        attempted_solutions: list[str],
        user_feedback: str,
        user_email: str | None,
    ) -> dict[str, Any]:
        ticket_id = f"INC-{uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc)
        record = {
            "ticket_id": ticket_id,
            "question_id": question_id,
            "original_question": original_question,
            "attempted_solutions": attempted_solutions,
            "user_feedback": user_feedback,
            "user_email": user_email,
            "created_at": created_at.isoformat(),
        }
        with self._lock:
            self._data["escalations"].append(record)
            if question_id:
                for q in self._data["questions"]:
                    if q["id"] == question_id and q.get("status") == "pending":
                        q["status"] = "escalated"
                        q["resolved_at"] = created_at.isoformat()
                        break
            self._flush()
        return record

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            questions = list(self._data["questions"])
            escalations = list(self._data["escalations"])

        total = len(questions)
        deflected = sum(1 for q in questions if q["status"] == "deflected")
        escalated = sum(1 for q in questions if q["status"] == "escalated")
        pending = total - deflected - escalated

        decided = deflected + escalated
        deflection_rate = (deflected / decided) if decided else 0.0

        avg_conf = (
            sum(q["confidence"] for q in questions) / total if total else 0.0
        )

        counter: Counter[str] = Counter()
        deflection_per_query: dict[str, list[int]] = {}
        for q in questions:
            key = q["query"].strip().lower()
            counter[key] += 1
            deflection_per_query.setdefault(key, []).append(
                1 if q["status"] == "deflected" else 0 if q["status"] == "escalated" else -1
            )

        top_questions = []
        for key, count in counter.most_common(5):
            decisions = [d for d in deflection_per_query[key] if d != -1]
            rate = (sum(decisions) / len(decisions)) if decisions else 0.0
            top_questions.append(
                {"query": key, "count": count, "deflection_rate": round(rate, 3)}
            )

        recent_escalations = [
            {
                "ticket_id": e["ticket_id"],
                "original_question": e["original_question"],
                "created_at": e["created_at"],
                "user_email": e.get("user_email"),
            }
            for e in escalations[-5:][::-1]
        ]

        return {
            "total_questions": total,
            "deflected": deflected,
            "escalated": escalated,
            "pending": pending,
            "deflection_rate": round(deflection_rate, 3),
            "average_confidence": round(avg_conf, 3),
            "estimated_time_saved_minutes": deflected * MINUTES_SAVED_PER_DEFLECTION,
            "top_questions": top_questions,
            "recent_escalations": recent_escalations,
        }
