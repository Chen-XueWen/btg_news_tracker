from __future__ import annotations

import asyncio

from openai import AsyncOpenAI


def _normalize_line(text: str) -> str:
    return " ".join(text.split()).strip()


async def _summarize_single_source(
    *,
    client: AsyncOpenAI,
    model: str,
    topic: str,
    article: dict[str, str | None],
) -> str:
    prompt = (
        "Create one concise mini-summary for a single news source. "
        "Use only the provided metadata/snippet and avoid speculation. "
        "Keep it under 35 words and one sentence.\n\n"
        f"Topic: {topic}\n"
        f"Title: {article.get('title') or 'Untitled'}\n"
        f"Source: {article.get('source') or 'Unknown source'}\n"
        f"Published: {article.get('published') or article.get('published_at') or 'Unknown'}\n"
        f"URL: {article.get('url') or ''}\n"
        f"Snippet: {article.get('description') or ''}\n"
    )

    response = await client.responses.create(model=model, input=prompt)
    text = _normalize_line(response.output_text or "")
    if text:
        return text

    fallback = article.get("description") or article.get("title") or "No summary available"
    return _normalize_line(fallback)


async def summarize_sources(
    *,
    topic: str,
    articles: list[dict[str, str | None]],
    openai_api_key: str,
    model: str,
) -> list[dict[str, str | None]]:
    if not openai_api_key:
        raise RuntimeError("OpenAI API key is missing.")

    if not articles:
        return []

    client = AsyncOpenAI(api_key=openai_api_key)
    semaphore = asyncio.Semaphore(4)

    async def enrich(index: int, article: dict[str, str | None]):
        async with semaphore:
            mini_summary = await _summarize_single_source(
                client=client,
                model=model,
                topic=topic,
                article=article,
            )
        enriched = dict(article)
        enriched["mini_summary"] = mini_summary
        return index, enriched

    tasks = [enrich(i, article) for i, article in enumerate(articles)]
    enriched_results = await asyncio.gather(*tasks)
    enriched_results.sort(key=lambda item: item[0])

    return [article for _, article in enriched_results]


def _build_source_block(articles: list[dict[str, str | None]]) -> str:
    lines: list[str] = []
    for idx, article in enumerate(articles, start=1):
        title = article.get("title") or "Untitled"
        url = article.get("url") or ""
        source = article.get("source") or "Unknown source"
        published = article.get("published") or article.get("published_at") or "Unknown time"
        description = article.get("description") or ""
        mini_summary = article.get("mini_summary") or ""
        lines.append(
            f"[{idx}] {title}\n"
            f"Source: {source} | Published: {published}\n"
            f"URL: {url}\n"
            f"Snippet: {description}\n"
            f"tldr: {mini_summary}"
        )
    return "\n\n".join(lines)


async def summarize_news(
    *,
    topic: str,
    articles: list[dict[str, str | None]],
    openai_api_key: str,
    model: str,
) -> str:
    if not openai_api_key:
        raise RuntimeError("OpenAI API key is missing.")

    if not articles:
        return (
            f"No relevant web results were found in the last 7 days for '{topic}'. "
            "Try a broader topic."
        )

    client = AsyncOpenAI(api_key=openai_api_key)
    source_block = _build_source_block(articles)

    prompt = (
        "You are a news analyst. Produce a global synthesis from the source mini-summaries and snippets. "
        "Use only the provided sources and stay factual.\n\n"
        f"Topic: {topic}\n\n"
        "Sources:\n"
        f"{source_block}\n\n"
        "Return:\n"
        "1) A concise 4-6 sentence summary of the most important developments.\n"
        "2) 3 bullet points for notable signals or trends.\n"
        "3) A final line: 'Sources reviewed: N'.\n"
        "Keep it factual and avoid speculation."
    )

    response = await client.responses.create(
        model=model,
        input=prompt,
    )
    return response.output_text.strip()
