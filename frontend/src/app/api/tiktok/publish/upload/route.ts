import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/tiktok/session";
import { uploadVideoToTikTok } from "@/lib/tiktok/client";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not connected" }, { status: 401 });
  }

  const formData = await request.formData();
  const uploadUrl = formData.get("upload_url") as string;
  const file = formData.get("video") as File;

  if (!uploadUrl || !file) {
    return NextResponse.json(
      { error: "Missing upload_url or video file" },
      { status: 400 },
    );
  }

  const arrayBuffer = await file.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);

  const result = await uploadVideoToTikTok(
    uploadUrl,
    buffer,
    file.type || "video/mp4",
  );

  if (!result.ok) {
    return NextResponse.json(
      { error: `Upload failed with status ${result.status}` },
      { status: 400 },
    );
  }

  return NextResponse.json({ ok: true });
}
