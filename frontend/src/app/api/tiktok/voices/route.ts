import { NextResponse } from "next/server";

const HEYGEN_API = "https://api.heygen.com";
const HEYGEN_KEY = process.env.HEYGEN_API_KEY || "";

export async function GET() {
  if (!HEYGEN_KEY) {
    return NextResponse.json({ error: "HEYGEN_API_KEY not set" }, { status: 500 });
  }

  const res = await fetch(`${HEYGEN_API}/v2/voices`, {
    headers: { "X-Api-Key": HEYGEN_KEY },
  });
  const data = await res.json();
  const allVoices = data.data?.voices || [];

  // Filter Indonesian voices only
  const indonesian = allVoices
    .filter((v: Record<string, string>) =>
      (v.language || "").toLowerCase() === "indonesian"
    )
    .map((v: Record<string, string>) => ({
      voice_id: v.voice_id,
      name: v.display_name || v.name || "(unnamed)",
      gender: v.gender || "unknown",
      preview_url: v.preview_audio || "",
    }));

  return NextResponse.json({ voices: indonesian });
}
