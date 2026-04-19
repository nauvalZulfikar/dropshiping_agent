"""
Generate a sample TikTok video using HeyGen API.
Usage: python scripts/generate_sample_video.py
"""
import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import httpx

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
HEYGEN_BASE_URL = "https://api.heygen.com"
OUTPUT_DIR = Path(__file__).parent.parent / "samples"
OUTPUT_FILE = OUTPUT_DIR / "sample_video.mp4"
MAX_ATTEMPTS = 2

# Script — conversational Indonesian, 15-30 seconds, about Fast Charger Type-C 65W
SCRIPT = """Eh, charger HP lo masih yang 10 watt? Kasian banget.

Gua pake fast charger 65 watt ini, tiga port, satu charger buat semua gadget.
HP, laptop, earbuds — semua keisi dalam 30 menit.

Ukurannya kecil banget, muat di kantong celana. Teknologi GaN, jadi ga panas.

Cuma 89 ribu. Link di bio ya!"""

AVATAR_ID = "Ren_sitting_sofacasual_front"
VOICE_ID = "6b956e6dac4343bab8d95979b2f68e71"
BG_COLOR = "#f5f5f0"


def headers():
    return {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"}


async def create_video() -> str:
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": AVATAR_ID,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": SCRIPT,
                    "voice_id": VOICE_ID,
                },
                "background": {
                    "type": "color",
                    "value": BG_COLOR,
                },
            }
        ],
        "dimension": {"width": 720, "height": 1280},
        "test": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{HEYGEN_BASE_URL}/v2/video/generate",
            headers=headers(),
            json=payload,
        )
        data = resp.json()

    if data.get("error"):
        raise RuntimeError(f"HeyGen create failed: {data['error']}")

    video_id = data.get("data", {}).get("video_id", "")
    if not video_id:
        raise RuntimeError(f"No video_id in response: {json.dumps(data, indent=2)}")

    return video_id


async def poll_status(video_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{HEYGEN_BASE_URL}/v1/video_status.get?video_id={video_id}",
            headers=headers(),
        )
        return resp.json().get("data", {})


async def download(url: str, path: Path):
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(url)
        path.write_bytes(resp.content)


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("HeyGen Sample Video Generator")
    print("=" * 60)
    print(f"\nAvatar: {AVATAR_ID}")
    print(f"Voice:  {VOICE_ID}")
    print(f"BG:     {BG_COLOR}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"\nScript:\n{SCRIPT}")
    print("=" * 60)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n[Attempt {attempt}/{MAX_ATTEMPTS}] Submitting to HeyGen...")

        try:
            video_id = await create_video()
            print(f"  Video ID: {video_id}")
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            if attempt == MAX_ATTEMPTS:
                print("\nMax attempts reached. Stopping.")
                sys.exit(1)
            continue

        # Poll
        print("  Polling status every 10s...")
        elapsed = 0
        max_wait = 600  # 10 minutes
        while elapsed < max_wait:
            await asyncio.sleep(10)
            elapsed += 10
            status = await poll_status(video_id)
            s = status.get("status", "unknown")
            print(f"  [{elapsed}s] Status: {s}")

            if s == "completed":
                video_url = status.get("video_url", "")
                duration = status.get("duration", 0)
                print(f"\n  Video ready!")
                print(f"  URL: {video_url}")
                print(f"  Duration: {duration}s")

                # Download
                print(f"  Downloading to {OUTPUT_FILE}...")
                await download(video_url, OUTPUT_FILE)
                size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
                print(f"  Downloaded: {size_mb:.1f} MB")

                # Save metadata
                meta = {
                    "video_id": video_id,
                    "script": SCRIPT,
                    "avatar_id": AVATAR_ID,
                    "voice_id": VOICE_ID,
                    "background_color": BG_COLOR,
                    "dimension": "720x1280",
                    "duration_seconds": duration,
                    "file_size_mb": round(size_mb, 2),
                    "generated_at": datetime.now().isoformat(),
                    "video_url": video_url,
                }
                meta_path = OUTPUT_DIR / "metadata.json"
                meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
                print(f"  Metadata saved to {meta_path}")
                print("\nDone!")
                return

            if s == "failed":
                err = status.get("error", "unknown")
                print(f"  FAILED: {err}")
                break

        else:
            print(f"\n  Timed out after {max_wait}s")

        if attempt == MAX_ATTEMPTS:
            print("\nMax attempts reached. Stopping.")
            sys.exit(1)

    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
