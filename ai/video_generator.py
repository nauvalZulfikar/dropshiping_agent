"""
UGC Video Generator — HeyGen API.
Generate AI avatar videos from scripts for affiliate content.
"""
import asyncio
import os

import httpx

from core.celery_app import celery_app
from core.logger import logger

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
HEYGEN_BASE_URL = "https://api.heygen.com"

# Avatar presets per niche
NICHE_AVATARS = {
    "gadget":         {"avatar_id": "Aditya_public_2",   "voice_id": "6b956e6dac4343bab8d95979b2f68e71"},
    "gadget_tools":   {"avatar_id": "Aditya_public_2",   "voice_id": "6b956e6dac4343bab8d95979b2f68e71"},
    "aksesori hp":    {"avatar_id": "Jinwoo_public_2",   "voice_id": "784ed53b093f4b778ea114a2cc551b8d"},
    "skincare":       {"avatar_id": "Ann_Casual_Front_public", "voice_id": "fdeb03e3681d462cb08a9ba7d7a50392"},
    "fashion wanita": {"avatar_id": "Ann_Casual_Front_public", "voice_id": "fdeb03e3681d462cb08a9ba7d7a50392"},
    "peralatan dapur": {"avatar_id": "Ann_Casual_Front_public", "voice_id": "8507f6910b7e409b85f0f2bdb4d637a6"},
    "suplemen":       {"avatar_id": "Aditya_public_5",   "voice_id": "b32b7aae004c4e1792b0da7684a806ab"},
}

DEFAULT_AVATAR = {"avatar_id": "Aditya_public_2", "voice_id": "6b956e6dac4343bab8d95979b2f68e71"}


def _headers() -> dict:
    return {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
    }


async def list_avatars() -> list[dict]:
    """List available HeyGen avatars."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{HEYGEN_BASE_URL}/v2/avatars",
            headers=_headers(),
        )
        data = resp.json()
    return data.get("data", {}).get("avatars", [])


async def create_video(
    script: str,
    niche: str = "gadget_tools",
    avatar_id: str | None = None,
    voice_id: str | None = None,
    aspect_ratio: str = "9:16",
    background_color: str = "#1a1a2e",
) -> dict:
    """
    Submit video generation request to HeyGen.
    Returns: {"video_id": "...", "status": "processing"}
    """
    preset = NICHE_AVATARS.get(niche, DEFAULT_AVATAR)
    avatar = avatar_id or preset["avatar_id"]
    voice = voice_id or preset["voice_id"]

    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": voice,
                },
                "background": {
                    "type": "color",
                    "value": background_color,
                },
            }
        ],
        "dimension": {"width": 720, "height": 1280} if aspect_ratio == "9:16" else {"width": 1280, "height": 720},
        "aspect_ratio": None,
        "test": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{HEYGEN_BASE_URL}/v2/video/generate",
            headers=_headers(),
            json=payload,
        )
        data = resp.json()

    if data.get("error"):
        logger.error("heygen_create_failed", error=data["error"])
        return {"error": data["error"]}

    video_id = data.get("data", {}).get("video_id", "")
    logger.info("heygen_video_submitted", video_id=video_id)
    return {"video_id": video_id, "status": "processing"}


async def check_video_status(video_id: str) -> dict:
    """
    Check video generation status.
    Returns: {"status": "completed"|"processing"|"failed", "video_url": "...", "duration": N}
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{HEYGEN_BASE_URL}/v1/video_status.get?video_id={video_id}",
            headers=_headers(),
        )
        data = resp.json()

    video_data = data.get("data", {})
    return {
        "status": video_data.get("status", "unknown"),
        "video_url": video_data.get("video_url", ""),
        "duration": video_data.get("duration", 0),
        "error": video_data.get("error"),
    }


async def wait_for_video(video_id: str, poll_interval: int = 10, max_wait: int = 600) -> dict:
    """Poll until video is ready or timeout."""
    elapsed = 0
    while elapsed < max_wait:
        status = await check_video_status(video_id)
        if status["status"] == "completed":
            return status
        if status["status"] == "failed":
            return status
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    return {"status": "timeout", "error": f"Timed out after {max_wait}s"}


async def download_video(video_url: str, output_path: str) -> str:
    """Download completed video to local file."""
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(video_url)
        with open(output_path, "wb") as f:
            f.write(resp.content)
    return output_path
