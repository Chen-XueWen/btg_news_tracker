from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.main as main_module
from app.config import Settings
from app.services.slack import SlackSendError


class StubAgent:
    async def ainvoke(self, payload: dict):
        return {
            "summary": "Quantum update summary.",
            "articles": [
                {
                    "title": "Example Quantum Story",
                    "url": "https://example.com/quantum-story",
                    "description": "Example description",
                    "source": "example.com",
                    "published": "2 hours ago",
                    "published_at": "2026-03-10T10:00:00+00:00",
                    "mini_summary": "Key update from the source.",
                    "source_metric_scores": [
                        {"variable": "Source Credibility", "score": 4.2}
                    ],
                }
            ],
        }


def _configure_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    brave_key: str = "test-brave",
    openai_key: str = "test-openai",
    webhook_url: str = "https://example.com/webhook",
    bot_token: str = "test-slack-bot",
    channel_id: str = "C123",
) -> None:
    monkeypatch.setenv("BRAVE_API_KEY", brave_key)
    monkeypatch.setenv("OPENAI_API_KEY", openai_key)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", webhook_url)
    monkeypatch.setenv("SLACK_BOT_TOKEN", bot_token)
    monkeypatch.setenv("SLACK_CHANNEL_ID", channel_id)


def _patch_default_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "build_news_agent", lambda settings: StubAgent())

    async def fake_send_news_to_slack(**kwargs):
        return None

    monkeypatch.setattr(main_module, "send_news_to_slack", fake_send_news_to_slack)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    _configure_env(monkeypatch)
    _patch_default_runtime(monkeypatch)

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_news_happy_path_returns_summary_and_articles(client: TestClient):
    payload = {
        "topic": "Quantum Computing",
        "scoring_metrics": [
            {
                "variable": "Source Credibility",
                "description": "Higher score for trusted and consistent sources.",
            }
        ],
    }

    response = client.post("/api/news", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "Quantum Computing"
    assert isinstance(body["summary"], str) and body["summary"]
    assert isinstance(body["articles"], list) and len(body["articles"]) == 1


def test_news_validation_rejects_short_topic(client: TestClient):
    response = client.post("/api/news", json={"topic": "Q", "scoring_metrics": []})
    assert response.status_code == 422


def test_news_missing_brave_key_returns_500(monkeypatch: pytest.MonkeyPatch):
    _configure_env(monkeypatch, brave_key="")
    _patch_default_runtime(monkeypatch)
    monkeypatch.setattr(
        main_module,
        "load_settings",
        lambda: Settings(
            brave_api_key="",
            openai_api_key="test-openai",
            slack_webhook_url="https://example.com/webhook",
            slack_bot_token="test-slack-bot",
            slack_channel_id="C123",
            public_api_base_url="",
            model="gpt-5-mini",
            brave_endpoint="https://api.search.brave.com/res/v1/web/search",
        ),
    )

    with TestClient(main_module.app) as test_client:
        response = test_client.post(
            "/api/news",
            json={"topic": "Quantum Computing", "scoring_metrics": []},
        )

    assert response.status_code == 500
    assert "Missing Brave API key" in response.json().get("detail", "")


def test_video_create_returns_normalized_job(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def fake_build_video_prompt(**kwargs):
        return "Short narration script"

    async def fake_create_video_job(**kwargs):
        return {
            "id": "vid-123",
            "status": "queued",
            "model": "sora-2",
            "progress": 0,
            "seconds": 12,
            "size": "1280x720",
            "error": None,
        }

    monkeypatch.setattr(main_module, "build_video_prompt", fake_build_video_prompt)
    monkeypatch.setattr(main_module, "create_video_job", fake_create_video_job)

    response = client.post(
        "/api/videos",
        json={
            "topic": "Quantum Computing",
            "summary": "This is a sufficiently long summary text for video generation.",
            "seconds": 12,
            "size": "1280x720",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "vid-123"
    assert body["status"] == "queued"


def test_video_completed_uses_webhook_fallback_once(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    calls = {"webhook": 0}

    async def fake_get_video_job(*, api_key: str, video_id: str):
        return {
            "id": video_id,
            "status": "completed",
            "model": "sora-2",
            "progress": 100,
            "seconds": 12,
            "size": "1280x720",
            "error": None,
        }

    async def fake_download_video_content(*, api_key: str, video_id: str):
        return b"mp4-bytes"

    async def fake_upload_video_file_to_slack(**kwargs):
        raise SlackSendError("upload failed")

    async def fake_send_video_to_slack(**kwargs):
        calls["webhook"] += 1

    monkeypatch.setattr(main_module, "get_video_job", fake_get_video_job)
    monkeypatch.setattr(main_module, "download_video_content", fake_download_video_content)
    monkeypatch.setattr(main_module, "upload_video_file_to_slack", fake_upload_video_file_to_slack)
    monkeypatch.setattr(main_module, "send_video_to_slack", fake_send_video_to_slack)

    main_module.app.state.video_topics["vid-1"] = "Quantum Computing"

    first = client.get("/api/videos/vid-1")
    second = client.get("/api/videos/vid-1")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["webhook"] == 1


def test_video_content_download_header(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def fake_download_video_content(*, api_key: str, video_id: str):
        return b"video-content"

    monkeypatch.setattr(main_module, "download_video_content", fake_download_video_content)

    response = client.get("/api/videos/vid-xyz/content?download=true")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("video/mp4")
    assert "attachment; filename=\"news-vid-xyz.mp4\"" in response.headers.get(
        "content-disposition", ""
    )
