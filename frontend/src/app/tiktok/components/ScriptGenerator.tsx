"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  script: string;
  onScriptChange: (script: string) => void;
}

export function ScriptGenerator({ script, onScriptChange }: Props) {
  const [productName, setProductName] = useState("");
  const [niche, setNiche] = useState("");
  const [features, setFeatures] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerate() {
    if (!productName.trim()) {
      setError("Masukkan nama produk");
      return;
    }
    setGenerating(true);
    setError("");

    try {
      const res = await fetch("/api/tiktok/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_name: productName,
          niche: niche || undefined,
          key_features: features || undefined,
          target_duration: 20,
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      onScriptChange(data.script);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-3">
      <label className="text-zinc-400 text-sm">Script</label>

      {/* AI generator inputs */}
      <div className="p-3 bg-zinc-900 rounded-lg space-y-2">
        <p className="text-xs text-zinc-500">
          Generate script otomatis dari nama produk, atau tulis manual di bawah.
        </p>
        <div className="flex gap-2">
          <input
            className="flex-1 px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white text-sm"
            placeholder="Nama produk"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
          />
          <input
            className="w-28 px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white text-sm"
            placeholder="Niche"
            value={niche}
            onChange={(e) => setNiche(e.target.value)}
          />
        </div>
        <input
          className="w-full px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white text-sm"
          placeholder="Fitur utama (opsional)"
          value={features}
          onChange={(e) => setFeatures(e.target.value)}
        />
        <Button size="sm" onClick={handleGenerate} disabled={generating}>
          {generating ? "Generating..." : "Generate Script AI"}
        </Button>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>

      {/* Script textarea */}
      <textarea
        className="w-full px-3 py-2 bg-zinc-800 rounded border border-zinc-700 text-white text-sm resize-none"
        rows={5}
        value={script}
        onChange={(e) => onScriptChange(e.target.value)}
        placeholder="Script yang akan diucapkan avatar..."
      />
      <p className="text-xs text-zinc-500">
        ~{Math.round(script.split(/\s+/).filter(Boolean).length / 2.5)} detik
        ({script.split(/\s+/).filter(Boolean).length} kata)
      </p>
    </div>
  );
}
