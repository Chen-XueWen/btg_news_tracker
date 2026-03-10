from __future__ import annotations

from datetime import datetime, timezone

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    settings = load_settings()
    app.state.settings = settings
    app.state.agent = build_news_agent(settings)
    app.state.video_topics = {}
    app.state.notified_video_ids = set()


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

    prompt = build_video_prompt(topic=payload.topic, summary=payload.summary)
    try:
        job = await create_video_job(
            api_key=settings.openai_api_key,
            prompt=prompt,
            model="sora-2",
            seconds=payload.seconds,
            size=payload.size,
        )
    except VideoGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if job.get("id"):
        app.state.video_topics[job["id"]] = payload.topic

    return VideoJobResponse(**job)


@app.get("/api/videos/{video_id}", response_model=VideoJobResponse)
async def get_video(video_id: str) -> VideoJobResponse:
    settings = app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key.")

    try:
        job = await get_video_job(api_key=settings.openai_api_key, video_id=video_id)
    except VideoGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    status = str(job.get("status") or "").lower()
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
            else:
                await send_video_to_slack(
                    webhook_url=settings.slack_webhook_url,
                    topic=topic,
                    video_id=video_id,
                    video_url=video_url,
                )
            app.state.notified_video_ids.add(video_id)
        except (SlackSendError, VideoGenerationError):
            # Fallback to webhook text/link notification if file upload fails.
            try:
                await send_video_to_slack(
                    webhook_url=settings.slack_webhook_url,
                    topic=topic,
                    video_id=video_id,
                    video_url=video_url,
                )
            except SlackSendError:
                pass
            app.state.notified_video_ids.add(video_id)

    return VideoJobResponse(**job)


@app.get("/api/videos/{video_id}/content")
async def download_video(video_id: str, download: bool = Query(default=False)) -> Response:
    settings = app.state.settings
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="Missing OpenAI API key.")

    try:
        content = await download_video_content(api_key=settings.openai_api_key, video_id=video_id)
    except VideoGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="news-{video_id}.mp4"'

    return Response(content=content, media_type="video/mp4", headers=headers)
