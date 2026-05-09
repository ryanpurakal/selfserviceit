"""Pydantic models for request/response payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Question(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


class Source(BaseModel):
    text: str
    source: str
    relevance: float
    chunk_id: str


class AnswerResponse(BaseModel):
    question_id: str
    answer: str
    sources: list[Source]
    confidence: float
    related_topics: list[str]
    used_llm: bool


class EscalationRequest(BaseModel):
    question_id: Optional[str] = None
    original_question: str
    attempted_solutions: list[str] = Field(default_factory=list)
    user_feedback: str = ""
    user_email: Optional[str] = None


class EscalationResponse(BaseModel):
    ticket_id: str
    message: str
    created_at: datetime


class DeflectionFeedback(BaseModel):
    question_id: str
    deflected: bool


class IngestionResponse(BaseModel):
    documents_loaded: int
    chunks_created: int
    chunks_indexed: int
    sources: list[str]


class TopQuestion(BaseModel):
    query: str
    count: int
    deflection_rate: float


class AnalyticsResponse(BaseModel):
    total_questions: int
    deflected: int
    escalated: int
    pending: int
    deflection_rate: float
    average_confidence: float
    estimated_time_saved_minutes: int
    top_questions: list[TopQuestion]
    recent_escalations: list[dict]
