from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx


class BraveSearchError(RuntimeError):
    pass


_RELATIVE_AGE_RE = re.compile(
    r"(?P<num>\d+)\s+(?P<unit>minute|hour|day|week|month|year)s?\s+ago",
    re.IGNORECASE,
)
_DATE_FORMATS = (
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%m/%d/%Y",
)


def _parse_relative_age(value: str, now: datetime) -> datetime | None:
    text = value.strip().lower()
    if text == "yesterday":
        return now - timedelta(days=1)

    match = _RELATIVE_AGE_RE.search(text)
    if not match:
        return None

    num = int(match.group("num"))
    unit = match.group("unit").lower()
    if unit == "minute":
        return now - timedelta(minutes=num)
    if unit == "hour":
        return now - timedelta(hours=num)
    if unit == "day":
        return now - timedelta(days=num)
    if unit == "week":
        return now - timedelta(weeks=num)
    if unit == "month":
        return now - timedelta(days=30 * num)
    if unit == "year":
        return now - timedelta(days=365 * num)
    return None


def _parse_absolute_date(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None

    iso_candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    embedded = re.search(r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", text)
    if embedded:
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(embedded.group(1), fmt).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue

    return None


def _parse_published_at(result: dict[str, Any], now: datetime) -> datetime | None:
    for field in ("page_age", "age", "published", "updated"):
        raw = result.get(field)
        if not raw or not isinstance(raw, str):
            continue

        rel = _parse_relative_age(raw, now)
        if rel:
            return rel.astimezone(timezone.utc)

        abs_dt = _parse_absolute_date(raw)
        if abs_dt:
            return abs_dt.astimezone(timezone.utc)

    return None


def _canonicalize_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    scheme = (parsed.scheme or "https").lower()
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, host, path, "", "", ""))


def _title_key(title: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


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

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    payload: dict[str, Any] = response.json()
    raw_results = payload.get("web", {}).get("results", [])

    normalized: list[dict[str, Any]] = []
    for result in raw_results:
        if not result.get("url") or not result.get("title"):
            continue

        published_at = _parse_published_at(result, now)
        if not published_at:
            # Strict mode: keep only sources with parseable publish timestamps.
            continue
        if not (cutoff <= published_at <= now):
            # Strict mode: enforce actual 7-day window.
            continue

        raw_published = result.get("age") or result.get("page_age")
        normalized.append(
            {
                "title": result.get("title"),
                "url": result.get("url"),
                "description": result.get("description"),
                "source": (result.get("meta_url") or {}).get("hostname"),
                "published": raw_published or published_at.date().isoformat(),
                "published_at": published_at.isoformat(),
                "_published_dt": published_at,
                "_canonical_url": _canonicalize_url(result.get("url")),
                "_title_key": _title_key(result.get("title")),
            }
        )

    normalized.sort(key=lambda item: item["_published_dt"], reverse=True)

    deduped: list[dict[str, str | None]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for article in normalized:
        canonical_url = article["_canonical_url"]
        title_key = article["_title_key"]
        if canonical_url in seen_urls or title_key in seen_titles:
            continue

        seen_urls.add(canonical_url)
        seen_titles.add(title_key)

        deduped.append(
            {
                "title": article["title"],
                "url": article["url"],
                "description": article["description"],
                "source": article["source"],
                "published": article["published"],
                "published_at": article["published_at"],
            }
        )

        if len(deduped) >= 10:
            break

    return deduped
