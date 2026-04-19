import { NextResponse } from "next/server";
import { getSession } from "@/lib/tiktok/session";
import { fetchUserInfo } from "@/lib/tiktok/client";

export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ connected: false }, { status: 401 });
  }

  if (Date.now() > session.expires_at) {
    return NextResponse.json(
      { connected: false, error: "Token expired" },
      { status: 401 },
    );
  }

  const data = await fetchUserInfo(session.access_token);

  if (data.error?.code) {
    return NextResponse.json(
      { connected: false, error: data.error.message },
      { status: 401 },
    );
  }

  const user = data.data?.user || {};
  return NextResponse.json({
    connected: true,
    user: {
      open_id: user.open_id || session.open_id,
      avatar_url: user.avatar_url || "",
      display_name: user.display_name || "",
      username: user.username || "",
    },
  });
}
