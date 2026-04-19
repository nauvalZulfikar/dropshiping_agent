import { NextRequest, NextResponse } from "next/server";
import { exchangeCodeForToken } from "@/lib/tiktok/client";
import { getOAuthState, clearOAuthState, setSession } from "@/lib/tiktok/session";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  if (error) {
    const desc = searchParams.get("error_description") || error;
    return NextResponse.redirect(
      new URL(`/tiktok?error=${encodeURIComponent(desc)}`, request.url),
    );
  }

  if (!code || !state) {
    return NextResponse.redirect(
      new URL("/tiktok?error=Missing+code+or+state", request.url),
    );
  }

  // Verify CSRF state
  const savedState = await getOAuthState();
  if (state !== savedState) {
    return NextResponse.redirect(
      new URL("/tiktok?error=Invalid+state+parameter", request.url),
    );
  }
  await clearOAuthState();

  // Exchange code for tokens
  const tokenData = await exchangeCodeForToken(code);

  if (tokenData.error || !tokenData.access_token) {
    const msg = tokenData.error_description || tokenData.error || "Token exchange failed";
    return NextResponse.redirect(
      new URL(`/tiktok?error=${encodeURIComponent(msg)}`, request.url),
    );
  }

  await setSession({
    access_token: tokenData.access_token,
    refresh_token: tokenData.refresh_token || "",
    open_id: tokenData.open_id || "",
    expires_at: Date.now() + (tokenData.expires_in || 86400) * 1000,
  });

  return NextResponse.redirect(new URL("/tiktok", request.url));
}
