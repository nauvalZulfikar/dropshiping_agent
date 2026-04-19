import { NextRequest, NextResponse } from "next/server";

const HEYGEN_API = "https://api.heygen.com";
const HEYGEN_KEY = process.env.HEYGEN_API_KEY || "";

export async function POST(request: NextRequest) {
  if (!HEYGEN_KEY) {
    return NextResponse.json({ error: "HEYGEN_API_KEY not set" }, { status: 500 });
  }

  const body = await request.json();
  const {
    avatar_id,
    script,
    voice_id,
    motion_prompt,
    background_color,
  } = body;

  if (!avatar_id || !script || !voice_id) {
    return NextResponse.json(
      { error: "avatar_id, script, and voice_id are required" },
      { status: 400 },
    );
  }

  const payload: Record<string, unknown> = {
    type: "avatar",
    avatar_id,
    script,
    voice_id,
    title: `Generated ${new Date().toISOString().slice(0, 16)}`,
    resolution: "720p",
    aspect_ratio: "9:16",
    expressiveness: "high",
    output_format: "mp4",
    background: {
      type: "color",
      value: background_color || "#1a1a2e",
    },
  };

  if (motion_prompt) {
    payload.motion_prompt = motion_prompt;
  }

  const res = await fetch(`${HEYGEN_API}/v3/videos`, {
    method: "POST",
    headers: {
      "X-Api-Key": HEYGEN_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json();

  if (!data.data?.video_id) {
    return NextResponse.json(
      { error: data.error?.message || "Video generation failed", detail: data },
      { status: 400 },
    );
  }

  return NextResponse.json({
    video_id: data.data.video_id,
    status: data.data.status || "processing",
  });
}
