from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from openai import AsyncOpenAI


class VideoGenerationError(RuntimeError):
    pass


ALLOWED_VIDEO_SECONDS = (4, 8, 12)
logger = logging.getLogger(__name__)

def _normalize_line(text: str) -> str:
    return " ".join(text.split()).strip()


def _target_word_budget(seconds: int) -> int:
    # ~2.2 words/second is a practical voiceover pacing target.
    return max(8, min(32, round(seconds * 2.2)))


def _truncate_words(text: str, max_words: int) -> str:
    words = _normalize_line(text).split(" ")
    if len(words) <= max_words:
        return " ".join(words).strip()
    return " ".join(words[:max_words]).rstrip(" ,;:.") + "."


def _fallback_script(*, summary: str, seconds: int) -> str:
    word_budget = _target_word_budget(seconds)
    compact = _normalize_line(summary)
    if not compact:
        return "No major updates were available in this cycle."
    return _truncate_words(compact, word_budget)


async def _distill_summary_for_voiceover(
    *,
    topic: str,
    summary: str,
    seconds: int,
    openai_api_key: str,
    model: str,
) -> str:
    fallback = _fallback_script(summary=summary, seconds=seconds)
    if not openai_api_key:
        return fallback

    word_budget = _target_word_budget(seconds)
    prompt = (
        "Rewrite the news summary into a short narration script for a video.\n"
        f"- Topic: {topic}\n"
        f"- Duration: {seconds} seconds\n"
        f"- Maximum words: {word_budget}\n"
        "- Keep only key facts and concrete outcomes.\n"
        "- No bullet points, no markdown, no list numbering.\n"
        "- Output one compact paragraph only.\n\n"
        f"Summary:\n{summary}\n"
    )

    client = AsyncOpenAI(api_key=openai_api_key)
    try:
        response = await client.responses.create(model=model, input=prompt)
    except Exception:
        return fallback

    distilled = _normalize_line(response.output_text or "")
    if not distilled:
        return fallback

    distilled_script = _truncate_words(distilled, word_budget)
    logger.info(
        "Distilled narration script ready. topic=%r seconds=%s words=%s script=%r",
        topic,
        seconds,
        len(distilled_script.split()),
        distilled_script,
    )
    return distilled_script


async def build_video_prompt(
    *,
    topic: str,
    summary: str,
    seconds: int,
    openai_api_key: str,
    model: str = "gpt-5-mini",
) -> str:
    summary_text = await _distill_summary_for_voiceover(
        topic=topic,
        summary=summary,
        seconds=seconds,
        openai_api_key=openai_api_key,
        model=model,
    )
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
    seconds: int = 12,
    size: str = "1280x720",
) -> dict[str, Any]:
    if not api_key:
        raise VideoGenerationError("OpenAI API key is missing.")

    _validate_size(size)

    if seconds not in ALLOWED_VIDEO_SECONDS:
        raise VideoGenerationError("Video seconds must be one of: 4, 8, 12 for sora-2.")

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

    async with httpx.AsyncClient(timeout=120.0) as client:
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

    async with httpx.AsyncClient(timeout=60.0) as client:
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

    async with httpx.AsyncClient(timeout=300.0) as client:
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
