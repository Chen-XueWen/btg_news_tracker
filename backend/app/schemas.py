from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScoringMetricInput(BaseModel):
    variable: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=400)


class NewsRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    scoring_metrics: list[ScoringMetricInput] = Field(default_factory=list, max_length=5)


class SourceMetricScore(BaseModel):
    variable: str
    score: float = Field(ge=1, le=5)


class Article(BaseModel):
    title: str
    url: str
    description: str | None = None
    source: str | None = None
    published: str | None = None
    published_at: str | None = None
    mini_summary: str | None = None
    source_metric_scores: list[SourceMetricScore] = Field(default_factory=list)


class NewsResponse(BaseModel):
    topic: str
    summary: str
    articles: list[Article]
    generated_at: datetime


class VideoGenerateRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    summary: str = Field(min_length=20, max_length=8000)
    seconds: Literal[4, 8, 12] = 12
    size: str = Field(default="1280x720")


class VideoJobResponse(BaseModel):
    id: str | None = None
    status: str | None = None
    model: str | None = None
    progress: float | None = None
    seconds: int | None = None
    size: str | None = None
    error: dict | str | None = None
