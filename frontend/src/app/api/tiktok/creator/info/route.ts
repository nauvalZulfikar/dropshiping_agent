import { NextResponse } from "next/server";
import { getSession } from "@/lib/tiktok/session";
import { queryCreatorInfo } from "@/lib/tiktok/client";

export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not connected" }, { status: 401 });
  }

  const data = await queryCreatorInfo(session.access_token);

  if (data.error?.code) {
    return NextResponse.json(
      { error: data.error.message || "Failed to query creator info" },
      { status: 400 },
    );
  }

  const info = data.data || {};
  return NextResponse.json({
    privacy_level_options: info.privacy_level_options || ["SELF_ONLY"],
    comment_disabled: info.comment_disabled ?? false,
    duet_disabled: info.duet_disabled ?? true,
    stitch_disabled: info.stitch_disabled ?? true,
    max_video_post_duration_sec: info.max_video_post_duration_sec || 60,
  });
}
