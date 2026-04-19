import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const HEYGEN_API = "https://api.heygen.com";
const HEYGEN_KEY = process.env.HEYGEN_API_KEY || "";
const DATA_FILE = path.join(process.cwd(), "avatars.json");

interface AvatarEntry {
  avatar_id: string;
  asset_id: string;
  name: string;
  preview_url: string;
  created_at: string;
}

function headers() {
  return { "X-Api-Key": HEYGEN_KEY };
}

function jsonHeaders() {
  return { "X-Api-Key": HEYGEN_KEY, "Content-Type": "application/json" };
}

function readAvatars(): AvatarEntry[] {
  try {
    const raw = fs.readFileSync(DATA_FILE, "utf8");
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function writeAvatars(avatars: AvatarEntry[]) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(avatars, null, 2));
}

export async function GET() {
  const avatars = readAvatars();
  return NextResponse.json({ avatars });
}

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const file = formData.get("photo") as File;
  const name = (formData.get("name") as string) || "Custom Avatar";

  if (!file) {
    return NextResponse.json({ error: "No photo uploaded" }, { status: 400 });
  }

  if (!HEYGEN_KEY) {
    return NextResponse.json({ error: "HEYGEN_API_KEY not configured" }, { status: 500 });
  }

  // Step 1: Upload photo to HeyGen
  const arrayBuffer = await file.arrayBuffer();
  const blob = new Blob([arrayBuffer], { type: file.type });
  const uploadForm = new FormData();
  uploadForm.append("file", blob, file.name);

  const uploadRes = await fetch(`${HEYGEN_API}/v3/assets`, {
    method: "POST",
    headers: headers(),
    body: uploadForm,
  });
  const uploadData = await uploadRes.json();

  if (!uploadData.data?.asset_id) {
    return NextResponse.json(
      { error: "Photo upload failed", detail: uploadData },
      { status: 400 },
    );
  }

  const assetId = uploadData.data.asset_id;
  const previewUrl = uploadData.data.url || "";

  // Step 2: Create avatar from photo
  const avatarRes = await fetch(`${HEYGEN_API}/v3/avatars`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({
      type: "photo",
      name,
      file: { type: "asset_id", asset_id: assetId },
    }),
  });
  const avatarData = await avatarRes.json();
  const avatarItem = avatarData.data?.avatar_item || {};
  const avatarId = avatarItem.id || "";

  if (!avatarId) {
    return NextResponse.json(
      { error: "Avatar creation failed", detail: avatarData },
      { status: 400 },
    );
  }

  // Step 3: Save to local storage
  const entry: AvatarEntry = {
    avatar_id: avatarId,
    asset_id: assetId,
    name,
    preview_url: previewUrl,
    created_at: new Date().toISOString(),
  };

  const avatars = readAvatars();
  avatars.push(entry);
  writeAvatars(avatars);

  return NextResponse.json({ avatar: entry });
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const avatarId = searchParams.get("id");

  if (!avatarId) {
    return NextResponse.json({ error: "Missing avatar id" }, { status: 400 });
  }

  const avatars = readAvatars();
  const filtered = avatars.filter((a) => a.avatar_id !== avatarId);
  writeAvatars(filtered);

  return NextResponse.json({ ok: true });
}
