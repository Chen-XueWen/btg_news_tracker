from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_secret_file(file_name: str) -> str:
    path = REPO_ROOT / file_name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class Settings:
    brave_api_key: str
    openai_api_key: str
    model: str = "gpt-5-mini"
    brave_endpoint: str = "https://api.search.brave.com/res/v1/web/search"



def load_settings() -> Settings:
    brave_api_key = os.getenv("BRAVE_API_KEY") or _read_secret_file("bravesearchapi.key")
    openai_api_key = os.getenv("OPENAI_API_KEY") or _read_secret_file("openai.key")
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    return Settings(
        brave_api_key=brave_api_key,
        openai_api_key=openai_api_key,
        model=model,
    )
