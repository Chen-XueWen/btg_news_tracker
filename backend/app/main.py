from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import build_news_agent
from app.config import load_settings
from app.schemas import Article, NewsRequest, NewsResponse
from app.services.brave_search import BraveSearchError
from app.services.slack import SlackSendError, send_news_to_slack


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
