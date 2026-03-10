from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI


DEFAULT_SCORE = 3.0


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _clamp_score(raw_score: float) -> float:
    return max(1.0, min(5.0, float(raw_score)))


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if not stripped:
        return {}

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        chunk = stripped[start : end + 1]
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            return {}

    return {}


def _default_metric_scores(scoring_metrics: list[dict[str, str]]) -> list[dict[str, str | float]]:
    return [
        {
            "variable": metric["variable"],
            "score": DEFAULT_SCORE,
        }
        for metric in scoring_metrics
    ]


def _fallback_source_scores(
    *,
    articles: list[dict[str, str | None]],
    scoring_metrics: list[dict[str, str]],
) -> list[dict[str, Any]]:
    defaults = _default_metric_scores(scoring_metrics)
    return [
        {
            "url": article.get("url") or "",
            "metric_scores": [dict(item) for item in defaults],
        }
        for article in articles
        if article.get("url")
    ]


async def score_news(
    *,
    topic: str,
    summary: str,
    articles: list[dict[str, str | None]],
    scoring_metrics: list[dict[str, str]],
    openai_api_key: str,
    model: str,
) -> list[dict[str, Any]]:
    if not scoring_metrics or not articles:
        return []

    if not openai_api_key:
        raise RuntimeError("OpenAI API key is missing.")

    client = AsyncOpenAI(api_key=openai_api_key)

    source_lines: list[str] = []
    for idx, article in enumerate(articles, start=1):
        title = article.get("title") or "Untitled"
        url = article.get("url") or ""
        snippet = article.get("mini_summary") or article.get("description") or ""
        source_lines.append(f"[{idx}] title={title} | url={url} | tldr={_normalize(snippet)}")
    source_block = "\n".join(source_lines)

    metrics_block = "\n".join(
        [
            f"- variable: {metric['variable']} | description: {metric['description']}"
            for metric in scoring_metrics
        ]
    )

    prompt = (
        "You are a scoring agent. For EACH source, score EACH user-defined metric.\n"
        "Use score range 1 to 5 (decimals allowed), where 5 is best.\n"
        "Return strict JSON only with this schema:\n"
        "{\n"
        '  "source_scores": [\n'
        "    {\"url\": string, \"metric_scores\": [{\"variable\": string, \"score\": number}]}\n"
        "  ]\n"
        "}\n"
        "Do not include rationale or explanation.\n\n"
        f"Topic:\n{topic}\n\n"
        f"Summary:\n{summary}\n\n"
        f"Sources:\n{source_block}\n\n"
        f"Metrics:\n{metrics_block}\n"
    )

    response = await client.responses.create(model=model, input=prompt)
    payload = _extract_json(response.output_text or "")
    rows = payload.get("source_scores") if isinstance(payload, dict) else None

    if not isinstance(rows, list):
        return _fallback_source_scores(articles=articles, scoring_metrics=scoring_metrics)

    metric_order = [metric["variable"] for metric in scoring_metrics]
    metric_lookup = {metric["variable"].strip().lower(): metric["variable"] for metric in scoring_metrics}

    article_urls = {article.get("url") for article in articles if article.get("url")}
    parsed_by_url: dict[str, dict[str, float]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        url = str(row.get("url", "")).strip()
        if not url or url not in article_urls:
            continue

        metric_rows = row.get("metric_scores")
        if not isinstance(metric_rows, list):
            continue

        parsed_metric_scores: dict[str, float] = {}
        for metric_row in metric_rows:
            if not isinstance(metric_row, dict):
                continue

            metric_name = _normalize(str(metric_row.get("variable", "")))
            metric_key = metric_name.lower()
            if metric_key not in metric_lookup:
                continue

            canonical_name = metric_lookup[metric_key]

            try:
                score = _clamp_score(float(metric_row.get("score", DEFAULT_SCORE)))
            except (TypeError, ValueError):
                score = DEFAULT_SCORE

            parsed_metric_scores[canonical_name] = score

        if parsed_metric_scores:
            parsed_by_url[url] = parsed_metric_scores

    source_scores: list[dict[str, Any]] = []
    for article in articles:
        url = article.get("url")
        if not url:
            continue

        parsed_scores = parsed_by_url.get(url, {})
        metric_scores = [
            {
                "variable": variable,
                "score": parsed_scores.get(variable, DEFAULT_SCORE),
            }
            for variable in metric_order
        ]

        source_scores.append(
            {
                "url": url,
                "metric_scores": metric_scores,
            }
        )

    return source_scores
