from __future__ import annotations

from typing import Any

import httpx


class BraveSearchError(RuntimeError):
    pass


async def search_brave_news(
    *,
    topic: str,
    api_key: str,
    endpoint: str,
    count: int = 10,
) -> list[dict[str, str | None]]:
    if not api_key:
        raise BraveSearchError("Brave Search API key is missing.")

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": f"{topic} news",
        "freshness": "pw",  # past week
        "count": count,
        "text_decorations": False,
        "country": "us",
        "search_lang": "en",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(endpoint, headers=headers, params=params)

    if response.status_code >= 400:
        raise BraveSearchError(
            f"Brave Search request failed with {response.status_code}: {response.text}"
        )

    payload: dict[str, Any] = response.json()
    raw_results = payload.get("web", {}).get("results", [])

    normalized: list[dict[str, str | None]] = []
    for result in raw_results:
        if not result.get("url") or not result.get("title"):
            continue
        normalized.append(
            {
                "title": result.get("title"),
                "url": result.get("url"),
                "description": result.get("description"),
                "source": (result.get("meta_url") or {}).get("hostname"),
                "published": result.get("age") or result.get("page_age"),
            }
        )

    return normalized
