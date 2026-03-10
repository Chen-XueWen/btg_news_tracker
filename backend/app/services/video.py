from __future__ import annotations

import re
from typing import Any

import httpx


class VideoGenerationError(RuntimeError):
    pass


def _truncate_summary(text: str, max_chars: int = 900) -> str:
    clean = " ".join(text.split()).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "…"


def build_video_prompt(*, topic: str, summary: str) -> str:
    summary_text = _truncate_summary(summary)
    return (
        f"Create a short news explainer video about '{topic}' with synchronized narration. "
        "Visual style: modern broadcast graphics package with abstract motion graphics, maps, charts, and text overlays. "
        "Narration style: confident professional news anchor. "
        "Do not depict or imitate any real person, politician, celebrity, or public figure. "
        "Do not show faces or body likenesses. Avoid graphic violence and explicit imagery. "
        "Use this narration script exactly:\n"
        f"{summary_text}"
    )


def _safe_error_text(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body)
    except Exception:  # pragma: no cover
        return response.text


def _normalize_video_job(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id"),
        "status": payload.get("status"),
        "model": payload.get("model"),
        "progress": payload.get("progress"),
        "seconds": payload.get("seconds"),
        "size": payload.get("size"),
        "error": payload.get("error"),
    }


def _validate_size(size: str) -> str:
    if not re.fullmatch(r"\d+x\d+", size):
        raise VideoGenerationError("Invalid video size format. Use WIDTHxHEIGHT, e.g. 1280x720.")
    return size


async def create_video_job(
    *,
    api_key: str,
    prompt: str,
    model: str = "sora-2",
    seconds: int = 8,
    size: str = "1280x720",
) -> dict[str, Any]:
    if not api_key:
        raise VideoGenerationError("OpenAI API key is missing.")

    _validate_size(size)

    if seconds < 1 or seconds > 20:
        raise VideoGenerationError("Video seconds must be between 1 and 20.")

    files = {
        "prompt": (None, prompt),
        "model": (None, model),
        "seconds": (None, str(seconds)),
        "size": (None, size),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/videos",
            headers=headers,
            files=files,
        )

    if response.status_code >= 400:
        raise VideoGenerationError(
            f"Video creation failed with {response.status_code}: {_safe_error_text(response)}"
        )

    payload = response.json()
    return _normalize_video_job(payload)


async def get_video_job(*, api_key: str, video_id: str) -> dict[str, Any]:
    if not api_key:
        raise VideoGenerationError("OpenAI API key is missing.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"https://api.openai.com/v1/videos/{video_id}", headers=headers)

    if response.status_code >= 400:
        raise VideoGenerationError(
            f"Video status fetch failed with {response.status_code}: {_safe_error_text(response)}"
        )

    payload = response.json()
    return _normalize_video_job(payload)


async def download_video_content(*, api_key: str, video_id: str) -> bytes:
    if not api_key:
        raise VideoGenerationError("OpenAI API key is missing.")

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            f"https://api.openai.com/v1/videos/{video_id}/content",
            headers=headers,
            follow_redirects=True,
        )

    if response.status_code >= 400:
        raise VideoGenerationError(
            f"Video download failed with {response.status_code}: {_safe_error_text(response)}"
        )

    return response.content
