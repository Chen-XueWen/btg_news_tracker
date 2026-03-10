from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SECRETS_DIR = REPO_ROOT / "secrets"


def _read_secret_file(file_name: str) -> str:
    path = SECRETS_DIR / file_name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class Settings:
    brave_api_key: str
    openai_api_key: str
    slack_webhook_url: str
    public_api_base_url: str
    model: str = "gpt-5-mini"
    brave_endpoint: str = "https://api.search.brave.com/res/v1/web/search"



def load_settings() -> Settings:
    brave_api_key = os.getenv("BRAVE_API_KEY") or _read_secret_file("bravesearchapi.key")
    openai_api_key = os.getenv("OPENAI_API_KEY") or _read_secret_file("openai.key")
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL") or _read_secret_file("slackwebhook.key")
    public_api_base_url = os.getenv("PUBLIC_API_BASE_URL", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    return Settings(
        brave_api_key=brave_api_key,
        openai_api_key=openai_api_key,
        slack_webhook_url=slack_webhook_url,
        public_api_base_url=public_api_base_url,
        model=model,
    )
