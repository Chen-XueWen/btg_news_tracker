from __future__ import annotations

import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.agent.graph import build_news_agent
from app.config import load_settings
from app.schemas import Article, NewsRequest, NewsResponse, VideoGenerateRequest, VideoJobResponse
from app.services.brave_search import BraveSearchError
from app.services.slack import (
    SlackSendError,
    send_news_to_slack,
    send_video_to_slack,
    upload_video_file_to_slack,
)
from app.services.video import (
    VideoGenerationError,
    build_video_prompt,
    create_video_job,
    download_video_content,
    get_video_job,
)


app = FastAPI(title="BTG News Tracker API", version="0.1.0")
logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BACKEND_DIR / "logs"
APP_LOG_FILE = LOGS_DIR / "app.log"


def _setup_file_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()

    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == APP_LOG_FILE:
            return

    file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root_logger.addHandler(file_handler)


def _normalize_progress(raw_progress: Any) -> float | None:
    if raw_progress is None:
        return None
    try:
        return float(raw_progress)
    except (TypeError, ValueError):
        return None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    _setup_file_logging()
    settings = load_settings()
    app.state.settings = settings
    app.state.agent = build_news_agent(settings)
    app.state.video_topics = {}
    app.state.notified_video_ids = set()
    app.state.video_status_snapshots = {}
    app.state.video_poll_counts = {}
    logger.info(
        "Startup complete. openai_key=%s brave_key=%s slack_webhook=%s slack_bot=%s",
        bool(settings.openai_api_key),
        bool(settings.brave_api_key),
        bool(settings.slack_webhook_url),
        bool(settings.slack_bot_token),
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/news", response_model=NewsResponse)
async def news(payload: NewsRequest) -> NewsResponse:
    settings = app.state.settings

    if not settings.brave_api_key:
        raise HTTPException(status_code=500, detail="Missing Brave API key.")
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key.")
    if not settings.slack_webhook_url:
        raise HTTPException(status_code=500, detail="Missing Slack webhook URL.")

    try:
        result = await app.state.agent.ainvoke(
            {
                "topic": payload.topic,
                "scoring_metrics": [metric.model_dump() for metric in payload.scoring_metrics],
            }
        )
    except BraveSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}") from exc

    articles = [Article(**item) for item in result.get("articles", [])]
    summary = result.get("summary", "")
    generated_at = datetime.now(timezone.utc)

    response_payload = NewsResponse(
        topic=payload.topic,
        summary=summary,
        articles=articles,
        generated_at=generated_at,
    )

    try:
        await send_news_to_slack(
            webhook_url=settings.slack_webhook_url,
            topic=response_payload.topic,
            summary=response_payload.summary,
            articles=[article.model_dump() for article in response_payload.articles],
            generated_at=response_payload.generated_at,
        )
    except SlackSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return response_payload


@app.post("/api/videos", response_model=VideoJobResponse)
async def create_video(payload: VideoGenerateRequest) -> VideoJobResponse:
    settings = app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key.")

    logger.info(
        "Video generation requested. topic=%r seconds=%s size=%s",
        payload.topic,
        payload.seconds,
        payload.size,
    )

    logger.info(
        "Distilling summary for video narration script. topic=%r seconds=%s",
        payload.topic,
        payload.seconds,
    )
    prompt = await build_video_prompt(
        topic=payload.topic,
        summary=payload.summary,
        seconds=payload.seconds,
        openai_api_key=settings.openai_api_key,
        model=settings.model,
    )
    logger.info("Video prompt ready after distillation. topic=%r", payload.topic)
    try:
        job = await create_video_job(
            api_key=settings.openai_api_key,
            prompt=prompt,
            model="sora-2",
            seconds=payload.seconds,
            size=payload.size,
        )
    except VideoGenerationError as exc:
        logger.warning("Video generation request failed. topic=%r error=%s", payload.topic, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    video_id = str(job.get("id") or "")
    if video_id:
        app.state.video_topics[video_id] = payload.topic
        app.state.video_poll_counts[video_id] = 0

    logger.info(
        "Video job created. id=%s status=%s progress=%s seconds=%s",
        video_id or "unknown",
        job.get("status"),
        _normalize_progress(job.get("progress")),
        job.get("seconds"),
    )
    return VideoJobResponse(**job)


@app.get("/api/videos/{video_id}", response_model=VideoJobResponse)
async def get_video(video_id: str) -> VideoJobResponse:
    settings = app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key.")

    try:
        job = await get_video_job(api_key=settings.openai_api_key, video_id=video_id)
    except VideoGenerationError as exc:
        logger.warning("Video status fetch failed. id=%s error=%s", video_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    status = str(job.get("status") or "").lower()
    progress = _normalize_progress(job.get("progress"))
    snapshot = (status, progress)
    previous_snapshot = app.state.video_status_snapshots.get(video_id)
    poll_count = app.state.video_poll_counts.get(video_id, 0) + 1
    app.state.video_poll_counts[video_id] = poll_count
    app.state.video_status_snapshots[video_id] = snapshot

    # Log on status/progress transitions, plus a heartbeat every ~1 minute (12 * 5s polls).
    if previous_snapshot != snapshot:
        logger.info(
            "Video job update. id=%s status=%s progress=%s poll=%s",
            video_id,
            status or "unknown",
            progress,
            poll_count,
        )
    elif poll_count % 12 == 0:
        logger.info(
            "Video job heartbeat. id=%s status=%s progress=%s poll=%s",
            video_id,
            status or "unknown",
            progress,
            poll_count,
        )

    if status in {"failed", "cancelled"}:
        logger.warning(
            "Video job terminal status. id=%s status=%s error=%s",
            video_id,
            status,
            job.get("error"),
        )

    should_notify = (
        status == "completed"
        and bool(settings.slack_webhook_url)
        and video_id not in app.state.notified_video_ids
    )
    if should_notify:
        topic = app.state.video_topics.get(video_id, "News Summary")
        base = settings.public_api_base_url.rstrip("/")
        video_url = f"{base}/api/videos/{video_id}/content" if base else None
        try:
            if settings.slack_bot_token and settings.slack_channel_id:
                logger.info("Uploading completed video to Slack file API. id=%s topic=%r", video_id, topic)
                video_bytes = await download_video_content(
                    api_key=settings.openai_api_key,
                    video_id=video_id,
                )
                await upload_video_file_to_slack(
                    bot_token=settings.slack_bot_token,
                    channel_id=settings.slack_channel_id,
                    file_bytes=video_bytes,
                    filename=f"news-{video_id}.mp4",
                    title=f"{topic} Summary Video",
                    initial_comment=f"Video generated for {topic} (id: {video_id}).",
                )
                logger.info("Slack file upload succeeded. id=%s bytes=%s", video_id, len(video_bytes))
            else:
                logger.info("Sending completed video webhook notification to Slack. id=%s", video_id)
                await send_video_to_slack(
                    webhook_url=settings.slack_webhook_url,
                    topic=topic,
                    video_id=video_id,
                    video_url=video_url,
                )
                logger.info("Slack webhook notification succeeded. id=%s", video_id)
            app.state.notified_video_ids.add(video_id)
        except (SlackSendError, VideoGenerationError) as exc:
            logger.warning("Primary Slack notify path failed. id=%s error=%s", video_id, exc)
            # Fallback to webhook text/link notification if file upload fails.
            try:
                await send_video_to_slack(
                    webhook_url=settings.slack_webhook_url,
                    topic=topic,
                    video_id=video_id,
                    video_url=video_url,
                )
                logger.info("Fallback Slack webhook notification succeeded. id=%s", video_id)
            except SlackSendError:
                logger.exception("Fallback Slack webhook notification failed. id=%s", video_id)
                pass
            app.state.notified_video_ids.add(video_id)

    return VideoJobResponse(**job)


@app.get("/api/videos/{video_id}/content")
async def download_video(video_id: str, download: bool = Query(default=False)) -> Response:
    settings = app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key.")

    logger.info("Video content request received. id=%s download=%s", video_id, download)
    try:
        content = await download_video_content(api_key=settings.openai_api_key, video_id=video_id)
    except VideoGenerationError as exc:
        logger.warning("Video content download failed. id=%s error=%s", video_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="news-{video_id}.mp4"'

    logger.info("Video content served. id=%s bytes=%s download=%s", video_id, len(content), download)
    return Response(content=content, media_type="video/mp4", headers=headers)
