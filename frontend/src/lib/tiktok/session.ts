import { cookies } from "next/headers";
import crypto from "crypto";
import type { TikTokSession } from "./types";

const COOKIE_NAME = "tiktok_session";
const STATE_COOKIE = "tiktok_oauth_state";
const SECRET = process.env.SESSION_SECRET || "change-me-generate-a-real-secret!!";

function getKey(): Buffer {
  return crypto.scryptSync(SECRET, "tiktok-session-salt", 32);
}

function encrypt(data: string): string {
  const key = getKey();
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  const encrypted = Buffer.concat([cipher.update(data, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, encrypted]).toString("base64");
}

function decrypt(data: string): string {
  const key = getKey();
  const buf = Buffer.from(data, "base64");
  const iv = buf.subarray(0, 12);
  const tag = buf.subarray(12, 28);
  const encrypted = buf.subarray(28);
  const decipher = crypto.createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAuthTag(tag);
  return decipher.update(encrypted, undefined, "utf8") + decipher.final("utf8");
}

export async function getSession(): Promise<TikTokSession | null> {
  const store = await cookies();
  const cookie = store.get(COOKIE_NAME);
  if (!cookie) return null;
  try {
    return JSON.parse(decrypt(cookie.value));
  } catch {
    return null;
  }
}

export async function setSession(session: TikTokSession): Promise<void> {
  const store = await cookies();
  store.set(COOKIE_NAME, encrypt(JSON.stringify(session)), {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 86400 * 30,
  });
}

export async function clearSession(): Promise<void> {
  const store = await cookies();
  store.delete(COOKIE_NAME);
}

export async function setOAuthState(state: string): Promise<void> {
  const store = await cookies();
  store.set(STATE_COOKIE, state, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 600,
  });
}

export async function getOAuthState(): Promise<string | null> {
  const store = await cookies();
  const cookie = store.get(STATE_COOKIE);
  return cookie?.value ?? null;
}

export async function clearOAuthState(): Promise<void> {
  const store = await cookies();
  store.delete(STATE_COOKIE);
}
