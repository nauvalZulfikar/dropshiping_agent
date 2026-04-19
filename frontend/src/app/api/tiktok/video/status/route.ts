import { NextRequest, NextResponse } from "next/server";

const HEYGEN_API = "https://api.heygen.com";
const HEYGEN_KEY = process.env.HEYGEN_API_KEY || "";

export async function GET(request: NextRequest) {
  const videoId = request.nextUrl.searchParams.get("id");

  if (!videoId) {
    return NextResponse.json({ error: "Missing video id" }, { status: 400 });
  }

  const res = await fetch(`${HEYGEN_API}/v3/videos/${videoId}`, {
    headers: { "X-Api-Key": HEYGEN_KEY },
  });
  const data = await res.json();
  const video = data.data || {};

  return NextResponse.json({
    status: video.status || "unknown",
    video_url: video.video_url || "",
    duration: video.duration || 0,
    error: video.error,
  });
}
