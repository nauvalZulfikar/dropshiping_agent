import { NextRequest, NextResponse } from "next/server";

const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";

export async function POST(request: NextRequest) {
  if (!OPENAI_API_KEY) {
    return NextResponse.json({ error: "OPENAI_API_KEY not set" }, { status: 500 });
  }

  const body = await request.json();
  const { product_name, niche, key_features, target_duration } = body;

  if (!product_name) {
    return NextResponse.json({ error: "product_name is required" }, { status: 400 });
  }

  const duration = target_duration || 20;

  const prompt = `Buat script TikTok ${duration} detik untuk produk berikut.

Produk: ${product_name}
${niche ? `Niche: ${niche}` : ""}
${key_features ? `Fitur: ${key_features}` : ""}

Rules:
1. Bahasa Indonesia casual sehari-hari, boleh campur bahasa gaul
2. Hook kuat di 3 detik pertama — pertanyaan atau pernyataan mengejutkan
3. Jelaskan BENEFIT bukan fitur. Bukan "baterai 5000mAh" tapi "HP ga mati seharian"
4. Akhiri dengan CTA singkat (link di bio)
5. Durasi ${duration} detik = sekitar ${Math.round(duration * 2.5)} kata
6. JANGAN mulai dengan "Halo guys" atau salam generik
7. Terasa kayak ngobrol sama temen, bukan iklan

Output script saja, tanpa instruksi visual atau keterangan tambahan.`;

  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      max_tokens: 300,
      messages: [
        {
          role: "system",
          content:
            "Kamu copywriter TikTok Indonesia. Buat script pendek yang catchy, casual, dan bikin orang berhenti scroll.",
        },
        { role: "user", content: prompt },
      ],
    }),
  });

  const data = await res.json();
  const script = data.choices?.[0]?.message?.content?.trim() || "";

  if (!script) {
    return NextResponse.json(
      { error: "Failed to generate script" },
      { status: 500 },
    );
  }

  return NextResponse.json({ script });
}
