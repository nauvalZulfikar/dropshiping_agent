import { NextResponse } from "next/server";
import crypto from "crypto";
import { setOAuthState } from "@/lib/tiktok/session";

export async function GET() {
  const state = crypto.randomBytes(16).toString("hex");
  await setOAuthState(state);

  const params = new URLSearchParams({
    client_key: process.env.TIKTOK_CLIENT_KEY!,
    scope: "user.info.basic,video.upload,video.publish",
    response_type: "code",
    redirect_uri: process.env.TIKTOK_REDIRECT_URI!,
    state,
  });

  return NextResponse.redirect(
    `https://www.tiktok.com/v2/auth/authorize/?${params.toString()}`,
  );
}
