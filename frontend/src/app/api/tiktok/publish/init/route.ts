import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/tiktok/session";
import { initVideoPublish } from "@/lib/tiktok/client";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not connected" }, { status: 401 });
  }

  const body = await request.json();
  const { title, privacy_level, disable_comment, disable_duet, disable_stitch, video_size } = body;

  if (!video_size || video_size > 50 * 1024 * 1024) {
    return NextResponse.json(
      { error: "Video must be under 50MB" },
      { status: 400 },
    );
  }

  const data = await initVideoPublish(session.access_token, {
    title: title || "",
    privacy_level: privacy_level || "SELF_ONLY",
    disable_comment: disable_comment ?? false,
    disable_duet: disable_duet ?? true,
    disable_stitch: disable_stitch ?? true,
    video_size,
  });

  if (data.error?.code) {
    return NextResponse.json(
      { error: data.error.message || "Publish init failed" },
      { status: 400 },
    );
  }

  return NextResponse.json({
    publish_id: data.data?.publish_id,
    upload_url: data.data?.upload_url,
  });
}
