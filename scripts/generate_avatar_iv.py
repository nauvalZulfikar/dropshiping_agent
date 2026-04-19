"""
Generate Avatar IV video from custom photo using HeyGen v3 API.
Usage: python scripts/generate_avatar_iv.py
"""
import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import httpx

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
BASE = "https://api.heygen.com"
MAX_ATTEMPTS = 2

OUTPUT_DIR = Path(__file__).parent.parent / "samples"

# Config
PHOTO_PATH = Path(__file__).parent.parent / "Avatar" / "avatar cewek ID.jpeg"
OUTPUT_FILE = OUTPUT_DIR / "sample_skincare_cewe_v2.mp4"
VOICE_ID = "8507f6910b7e409b85f0f2bdb4d637a6"  # Calm Cinta - Excited (Indonesian female)
MOTION_PROMPT = "Friendly smile, slight head movements, casual hand wave at greeting, gentle nod when explaining, looking directly at camera like talking to a friend"

SCRIPT = """Kulit lo sering kusam habis seharian di luar?

Coba serum ini, satu tetes aja udah kerasa lembab.
Pagi pake sebelum sunscreen, malem pake sebelum tidur.

Seminggu aja udah keliatan beda. Glowing tanpa ribet.
Cek link di bio ya!"""


def headers():
    return {"X-Api-Key": HEYGEN_API_KEY}


def json_headers():
    return {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"}


async def upload_photo(photo_path: Path) -> str:
    """Upload photo to HeyGen, return asset_id."""
    print(f"  Uploading photo: {photo_path.name} ({photo_path.stat().st_size / 1024:.0f} KB)")
    async with httpx.AsyncClient(timeout=60) as client:
        with open(photo_path, "rb") as f:
            resp = await client.post(
                f"{BASE}/v3/assets",
                headers=headers(),
                files={"file": (photo_path.name, f, "image/jpeg")},
            )
        data = resp.json()

    if resp.status_code != 200 or not data.get("data"):
        raise RuntimeError(f"Upload failed: {json.dumps(data, indent=2)}")

    asset_id = data["data"]["asset_id"]
    print(f"  Asset ID: {asset_id}")
    return asset_id


async def create_avatar(asset_id: str) -> str:
    """Create photo avatar from uploaded asset, return avatar_id."""
    print("  Creating photo avatar...")
    payload = {
        "type": "photo",
        "name": "Cewek ID - Skincare",
        "file": {
            "type": "asset_id",
            "asset_id": asset_id,
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{BASE}/v3/avatars",
            headers=json_headers(),
            json=payload,
        )
        data = resp.json()

    if resp.status_code not in (200, 201) or not data.get("data"):
        raise RuntimeError(f"Create avatar failed: {json.dumps(data, indent=2)}")

    d = data["data"]
    avatar_item = d.get("avatar_item", {})
    avatar_id = avatar_item.get("id", "")
    if not avatar_id:
        raise RuntimeError(f"No avatar_id in response: {json.dumps(data, indent=2)}")
    print(f"  Avatar ID: {avatar_id}")
    print(f"  Status: {avatar_item.get('status')} — waiting for processing...")

    # Poll until avatar is ready
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(30):  # max 5 min
            await asyncio.sleep(10)
            resp = await client.get(f"{BASE}/v3/avatars/{avatar_id}", headers=headers())
            adata = resp.json().get("data", {})
            status = adata.get("status", "unknown")
            print(f"  [{(i+1)*10}s] Avatar status: {status}")
            if status in ("completed", "active", "ready"):
                break
            if status == "failed":
                raise RuntimeError(f"Avatar processing failed: {adata}")
        else:
            # Try anyway — some avatars don't update status cleanly
            print("  Avatar processing timeout — attempting video generation anyway...")

    return avatar_id


async def generate_video(avatar_id: str) -> str:
    """Submit Avatar IV video generation, return video_id."""
    print("  Submitting Avatar IV video generation...")
    payload = {
        "type": "avatar",
        "avatar_id": avatar_id,
        "script": SCRIPT,
        "voice_id": VOICE_ID,
        "title": "Skincare Promo - Cewe ID v2",
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "expressiveness": "high",
        "motion_prompt": MOTION_PROMPT,
        "output_format": "mp4",
        "background": {
            "type": "color",
            "value": "#faf5f0",
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{BASE}/v3/videos",
            headers=json_headers(),
            json=payload,
        )
        data = resp.json()

    if not data.get("data"):
        raise RuntimeError(f"Generate failed: {json.dumps(data, indent=2)}")

    video_id = data["data"]["video_id"]
    print(f"  Video ID: {video_id}")
    return video_id


async def poll_status(video_id: str) -> dict:
    """Poll video status until completed/failed."""
    print("  Polling status every 10s...")
    elapsed = 0
    max_wait = 600
    async with httpx.AsyncClient(timeout=30) as client:
        while elapsed < max_wait:
            await asyncio.sleep(10)
            elapsed += 10
            resp = await client.get(
                f"{BASE}/v3/videos/{video_id}",
                headers=headers(),
            )
            data = resp.json().get("data", {})
            status = data.get("status", "unknown")
            print(f"  [{elapsed}s] Status: {status}")

            if status == "completed":
                return data
            if status == "failed":
                raise RuntimeError(f"Video failed: {data.get('error', 'unknown')}")

    raise RuntimeError(f"Timed out after {max_wait}s")


async def download(url: str, path: Path):
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(url)
        path.write_bytes(resp.content)


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("HeyGen Avatar IV — Cewek Skincare")
    print("=" * 60)
    print(f"Photo:  {PHOTO_PATH}")
    print(f"Voice:  Gadis - Natural (Indonesian female)")
    print(f"Output: {OUTPUT_FILE}")
    print(f"\nScript:\n{SCRIPT}")
    print("=" * 60)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n[Attempt {attempt}/{MAX_ATTEMPTS}]")
        try:
            # Step 1: Upload photo
            asset_id = await upload_photo(PHOTO_PATH)

            # Step 2: Create avatar
            avatar_id = await create_avatar(asset_id)

            # Step 3: Generate video
            video_id = await generate_video(avatar_id)

            # Step 4: Poll
            result = await poll_status(video_id)
            video_url = result.get("video_url", "")
            duration = result.get("duration", 0)

            print(f"\n  Video ready!")
            print(f"  URL: {video_url[:80]}...")
            print(f"  Duration: {duration}s")

            # Step 5: Download
            print(f"  Downloading to {OUTPUT_FILE}...")
            await download(video_url, OUTPUT_FILE)
            size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
            print(f"  Downloaded: {size_mb:.1f} MB")

            # Save metadata
            meta = {
                "video_id": video_id,
                "avatar_id": avatar_id,
                "asset_id": asset_id,
                "script": SCRIPT,
                "voice_id": VOICE_ID,
                "voice_name": "Calm Cinta - Excited",
                "motion_prompt": MOTION_PROMPT,
                "photo": str(PHOTO_PATH),
                "engine": "Avatar IV",
                "expressiveness": "high",
                "resolution": "720p",
                "aspect_ratio": "9:16",
                "duration_seconds": duration,
                "file_size_mb": round(size_mb, 2),
                "generated_at": datetime.now().isoformat(),
            }
            meta_path = OUTPUT_DIR / "metadata_skincare.json"
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
            print(f"  Metadata: {meta_path}")
            print("\nDone!")
            return

        except RuntimeError as e:
            print(f"  ERROR: {e}")
            if attempt == MAX_ATTEMPTS:
                print("\nMax attempts reached. Stopping.")
                sys.exit(1)

    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
