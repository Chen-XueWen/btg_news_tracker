from __future__ import annotations

from openai import AsyncOpenAI


def _build_source_block(articles: list[dict[str, str | None]]) -> str:
    lines: list[str] = []
    for idx, article in enumerate(articles, start=1):
        title = article.get("title") or "Untitled"
        url = article.get("url") or ""
        source = article.get("source") or "Unknown source"
        published = article.get("published") or "Unknown time"
        description = article.get("description") or ""
        lines.append(
            f"[{idx}] {title}\n"
            f"Source: {source} | Published: {published}\n"
            f"URL: {url}\n"
            f"Snippet: {description}"
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
        "You are a news analyst. Summarize the latest developments using only the provided sources. "
        "The search window is the last 7 days.\n\n"
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
        temperature=0.3,
    )
    return response.output_text.strip()
