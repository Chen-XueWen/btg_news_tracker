from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.config import Settings
from app.services.brave_search import search_brave_news
from app.services.summarizer import summarize_news, summarize_sources


class NewsAgentState(TypedDict, total=False):
    topic: str
    articles: list[dict[str, str | None]]
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

    graph.add_node("search", search_node)
    graph.add_node("summarize_sources", summarize_sources_node)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("search")
    graph.add_edge("search", "summarize_sources")
    graph.add_edge("summarize_sources", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
