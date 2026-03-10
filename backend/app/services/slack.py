from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class SlackSendError(RuntimeError):
    pass


def _truncate(text: str, max_chars: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "…"


def _build_blocks(
    *,
    topic: str,
    summary: str,
    articles: list[dict[str, Any]],
    generated_at: datetime,
) -> list[dict]:
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "BTG News Tracker", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Topic:* {topic}\n*Generated:* {generated_at.isoformat()}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary*\n{_truncate(summary, 2800)}",
            },
        },
        {"type": "divider"},
    ]

    if not articles:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "No qualifying sources were found."},
            }
        )
    else:
        for idx, article in enumerate(articles[:10], start=1):
            title = _truncate(article.get("title") or "Untitled", 140)
            url = article.get("url") or ""
            mini_summary = article.get("mini_summary") or article.get("description") or "No summary"
            mini_summary = _truncate(mini_summary, 300)
            source = article.get("source") or "Unknown source"
            published = article.get("published") or article.get("published_at") or "Unknown time"
            metric_scores = article.get("source_metric_scores") or []
            metric_score_line = ""
            if isinstance(metric_scores, list) and metric_scores:
                formatted_scores = []
                for metric in metric_scores:
                    if not isinstance(metric, dict):
                        continue
                    variable = str(metric.get("variable", "Metric")).strip()
                    try:
                        score = float(metric.get("score", 0))
                    except (TypeError, ValueError):
                        score = 0.0
                    formatted_scores.append(f"{variable}: {score:.2f}/5")
                if formatted_scores:
                    metric_score_line = "\n*Scores:* " + " | ".join(formatted_scores)

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{idx}. <{url}|{title}>*{metric_score_line}\n{mini_summary}",
                    },
                }
            )
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"{source} | {published}",
                        }
                    ],
                }
            )

    return blocks


async def send_news_to_slack(
    *,
    webhook_url: str,
    topic: str,
    summary: str,
    articles: list[dict[str, Any]],
    generated_at: datetime,
) -> None:
    if not webhook_url:
        raise SlackSendError("Slack webhook URL is missing.")

    payload = {
        "text": f"BTG News Tracker update for {topic}",
        "blocks": _build_blocks(
            topic=topic,
            summary=summary,
            articles=articles,
            generated_at=generated_at,
        ),
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(webhook_url, json=payload)

    if response.status_code >= 400:
        raise SlackSendError(
            f"Slack webhook request failed with {response.status_code}: {response.text}"
        )

    if response.text.strip().lower() != "ok":
        raise SlackSendError(f"Slack webhook returned unexpected response: {response.text}")
