"""Pydantic schemas for Groww Weekly Review Pulse (Phase 0 stubs)."""

from __future__ import annotations

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Review(BaseModel):
    """Normalized Play Store review (v1: source is always play)."""

    id: str = Field(..., description="Opaque local id (not store username)")
    source: Literal["play"] = "play"
    rating: float | None = Field(
        default=None,
        description="Star rating e.g. 1–5; null if missing",
    )
    title: str | None = None
    text: str = Field(..., description="Review body")
    date: Date = Field(..., description="Review date (ISO-8601 date)")
    language: str | None = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("review text must be non-empty")
        return cleaned


class Theme(BaseModel):
    """Clustered theme summary (at most 5 themes per run)."""

    id: str
    label: str
    review_count: int = Field(..., ge=0)
    avg_rating: float | None = None
    summary: str = Field(
        default="",
        description="Short internal summary (not the stakeholder pulse)",
    )
    sample_ids: list[str] = Field(default_factory=list)


class PulseDraft(BaseModel):
    """Stakeholder one-page weekly pulse (compliance-oriented shape)."""

    week_ending: Date
    themes: list[str] = Field(
        ...,
        min_length=0,
        max_length=3,
        description="Top themes shown in the note (exactly 3 when data allows)",
    )
    quotes: list[str] = Field(
        ...,
        min_length=0,
        max_length=3,
        description="Verbatim review snippets (exactly 3 when data allows)",
    )
    actions: list[str] = Field(
        ...,
        min_length=0,
        max_length=3,
        description="Concrete next steps grounded in themes",
    )
    body: str = Field(..., description="Full pulse markdown/plain text")
    word_count: int = Field(..., ge=0, description="Word count of body")

    @field_validator("word_count")
    @classmethod
    def within_scannable_limit(cls, value: int) -> int:
        # Soft documentation of ≤250 constraint; hard enforcement in Phase 2 gates
        if value > 250:
            raise ValueError("pulse body must be ≤250 words")
        return value
