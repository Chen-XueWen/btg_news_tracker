from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.config import Settings
from app.services.brave_search import search_brave_news
from app.services.scorer import score_news
from app.services.summarizer import summarize_news, summarize_sources


class NewsAgentState(TypedDict, total=False):
    topic: str
    scoring_metrics: list[dict[str, str]]
    articles: list[dict[str, Any]]
    summary: str


def build_news_agent(settings: Settings):
    graph = StateGraph(NewsAgentState)

    async def search_node(state: NewsAgentState) -> NewsAgentState:
        topic = state["topic"]
        articles = await search_brave_news(
            topic=topic,
            api_key=settings.brave_api_key,
            endpoint=settings.brave_endpoint,
            count=10,
        )
        return {"articles": articles}

    async def summarize_sources_node(state: NewsAgentState) -> NewsAgentState:
        enriched_articles = await summarize_sources(
            topic=state["topic"],
            articles=state.get("articles", []),
            openai_api_key=settings.openai_api_key,
            model=settings.model,
        )
        return {"articles": enriched_articles}

    async def summarize_node(state: NewsAgentState) -> NewsAgentState:
        summary = await summarize_news(
            topic=state["topic"],
            articles=state.get("articles", []),
            openai_api_key=settings.openai_api_key,
            model=settings.model,
        )
        return {"summary": summary}

    async def score_node(state: NewsAgentState) -> NewsAgentState:
        source_scores = await score_news(
            topic=state["topic"],
            summary=state.get("summary", ""),
            articles=state.get("articles", []),
            scoring_metrics=state.get("scoring_metrics", []),
            openai_api_key=settings.openai_api_key,
            model=settings.model,
        )
        source_score_by_url = {
            row["url"]: row.get("metric_scores", []) for row in source_scores if row.get("url")
        }
        scored_articles: list[dict[str, Any]] = []
        for article in state.get("articles", []):
            enriched = dict(article)
            article_url = article.get("url")
            if article_url in source_score_by_url:
                enriched["source_metric_scores"] = source_score_by_url[article_url]
            scored_articles.append(enriched)

        return {"articles": scored_articles}

    graph.add_node("search", search_node)
    graph.add_node("summarize_sources", summarize_sources_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("score", score_node)

    graph.set_entry_point("search")
    graph.add_edge("search", "summarize_sources")
    graph.add_edge("summarize_sources", "summarize")
    graph.add_edge("summarize", "score")
    graph.add_edge("score", END)

    return graph.compile()
