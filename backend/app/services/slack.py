from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import httpx


class SlackSendError(RuntimeError):
    pass


def _parse_slack_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:  # pragma: no cover
        raise SlackSendError(f"Slack returned non-JSON response: {response.text}") from exc

    if not payload.get("ok", False):
        raise SlackSendError(f"Slack API error: {payload.get('error', 'unknown_error')}")

    return payload


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


async def send_video_to_slack(
    *,
    webhook_url: str,
    topic: str,
    video_id: str,
    video_url: str | None = None,
) -> None:
    if not webhook_url:
        raise SlackSendError("Slack webhook URL is missing.")

    text = f"Video generated for {topic} (id: {video_id})."
    if video_url:
        text += f" Watch/download: {video_url}"

    payload = {"text": text}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(webhook_url, json=payload)

    if response.status_code >= 400:
        raise SlackSendError(
            f"Slack webhook request failed with {response.status_code}: {response.text}"
        )

    if response.text.strip().lower() != "ok":
        raise SlackSendError(f"Slack webhook returned unexpected response: {response.text}")


async def upload_video_file_to_slack(
    *,
    bot_token: str,
    channel_id: str,
    file_bytes: bytes,
    filename: str,
    title: str,
    initial_comment: str,
) -> None:
    if not bot_token:
        raise SlackSendError("Slack bot token is missing.")
    if not channel_id:
        raise SlackSendError("Slack channel id is missing.")
    if not file_bytes:
        raise SlackSendError("Video file bytes are empty.")

    headers = {"Authorization": f"Bearer {bot_token}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: get signed upload URL + file id.
        upload_url_response = await client.post(
            "https://slack.com/api/files.getUploadURLExternal",
            headers=headers,
            data={"filename": filename, "length": str(len(file_bytes))},
        )
        upload_url_payload = _parse_slack_json(upload_url_response)
        upload_url = upload_url_payload.get("upload_url")
        file_id = upload_url_payload.get("file_id")
        if not upload_url or not file_id:
            raise SlackSendError("Slack did not return upload_url/file_id.")

        # Step 2: upload raw bytes to signed URL.
        raw_upload_response = await client.post(
            upload_url,
            content=file_bytes,
            headers={"Content-Type": "video/mp4"},
        )
        if raw_upload_response.status_code >= 400:
            raise SlackSendError(
                f"Slack raw upload failed with {raw_upload_response.status_code}: {raw_upload_response.text}"
            )

        # Step 3: complete upload and share to channel.
        complete_upload_response = await client.post(
            "https://slack.com/api/files.completeUploadExternal",
            headers=headers,
            data={
                "files": json.dumps([{"id": file_id, "title": title}]),
                "channel_id": channel_id,
                "initial_comment": initial_comment,
            },
        )
        _parse_slack_json(complete_upload_response)
