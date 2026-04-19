import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/tiktok/session";
import { fetchPublishStatus } from "@/lib/tiktok/client";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not connected" }, { status: 401 });
  }

  const body = await request.json();
  const { publish_id } = body;

  if (!publish_id) {
    return NextResponse.json({ error: "Missing publish_id" }, { status: 400 });
  }

  const data = await fetchPublishStatus(session.access_token, publish_id);

  if (data.error?.code) {
    return NextResponse.json(
      { error: data.error.message || "Status fetch failed" },
      { status: 400 },
    );
  }

  return NextResponse.json({
    status: data.data?.status || "PROCESSING_UPLOAD",
    fail_reason: data.data?.fail_reason,
    publish_id,
  });
}
