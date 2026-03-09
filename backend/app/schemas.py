from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NewsRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)


class Article(BaseModel):
    title: str
    url: str
    description: str | None = None
    source: str | None = None
    published: str | None = None


class NewsResponse(BaseModel):
    topic: str
    summary: str
    articles: list[Article]
    generated_at: datetime
