"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScriptGenerator } from "./ScriptGenerator";
import { VoicePicker, type Voice } from "./VoicePicker";

interface Avatar {
  avatar_id: string;
  name: string;
}

interface GeneratedVideo {
  video_id: string;
  video_url: string;
  duration: number;
}

interface Props {
  selectedAvatar: Avatar | null;
  onVideoReady: (video: GeneratedVideo) => void;
}

const STATUS_MSG: Record<string, string> = {
  processing: "Rendering video...",
  waiting: "Dalam antrian...",
  completed: "Selesai!",
  failed: "Gagal",
};

export function VideoGenerator({ selectedAvatar, onVideoReady }: Props) {
  const [script, setScript] = useState("");
  const [selectedVoice, setSelectedVoice] = useState<Voice | null>(null);
  const [motionPrompt, setMotionPrompt] = useState("");
  const [bgColor, setBgColor] = useState("#1a1a2e");

  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");

  async function handleGenerate() {
    if (!selectedAvatar) {
      setError("Pilih avatar dulu");
      return;
    }
    if (!script.trim()) {
      setError("Tulis atau generate script dulu");
      return;
    }
    if (!selectedVoice) {
      setError("Pilih suara dulu");
      return;
    }

    setGenerating(true);
    setError("");
    setProgress("Mengirim ke HeyGen...");

    try {
      // Step 1: Submit generation
      const genRes = await fetch("/api/tiktok/video/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          avatar_id: selectedAvatar.avatar_id,
          script,
          voice_id: selectedVoice.voice_id,
          motion_prompt: motionPrompt || undefined,
          background_color: bgColor,
        }),
      });
      const genData = await genRes.json();

      if (!genRes.ok || genData.error) {
        throw new Error(genData.error || "Generation failed");
      }

      const videoId = genData.video_id;
      setProgress("Rendering video...");

      // Step 2: Poll status
      let attempts = 0;
      const maxAttempts = 60; // 60 × 5s = 5 minutes

      while (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 5000));
        attempts++;

        const statusRes = await fetch(
          `/api/tiktok/video/status?id=${videoId}`,
        );
        const statusData = await statusRes.json();

        setProgress(
          STATUS_MSG[statusData.status] ||
            `Processing... (${statusData.status})`,
        );

        if (statusData.status === "completed" && statusData.video_url) {
          onVideoReady({
            video_id: videoId,
            video_url: statusData.video_url,
            duration: statusData.duration,
          });
          return;
        }

        if (statusData.status === "failed") {
          throw new Error(statusData.error || "Video rendering failed");
        }
      }

      throw new Error("Timeout — video masih diproses. Cek HeyGen dashboard.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setGenerating(false);
      setProgress("");
    }
  }

  const estimatedCost = motionPrompt
    ? "~14 credits ($6.67)"
    : "~7 credits ($3.33)";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generate Video</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Avatar indicator */}
        {selectedAvatar ? (
          <div className="p-2 bg-zinc-900 rounded text-sm flex items-center gap-2">
            <span>👤</span>
            <span className="text-zinc-300">
              Avatar: <strong>{selectedAvatar.name}</strong>
            </span>
          </div>
        ) : (
          <div className="p-3 bg-yellow-900/20 border border-yellow-700/50 rounded text-sm text-yellow-300">
            Pilih avatar di atas dulu.
          </div>
        )}

        {/* Script generator */}
        <ScriptGenerator script={script} onScriptChange={setScript} />

        {/* Voice picker */}
        <VoicePicker selectedVoice={selectedVoice} onSelect={setSelectedVoice} />

        {/* Motion prompt */}
        <div>
          <label className="text-zinc-400 text-sm">
            Motion Prompt{" "}
            <span className="text-zinc-600">(opsional, biaya 2x)</span>
          </label>
          <textarea
            className="w-full mt-1 px-3 py-2 bg-zinc-800 rounded border border-zinc-700 text-white text-sm resize-none"
            rows={2}
            value={motionPrompt}
            onChange={(e) => setMotionPrompt(e.target.value)}
            placeholder="Contoh: Friendly smile, slight head movements, gentle nod when explaining"
          />
          {motionPrompt && (
            <p className="text-xs text-yellow-400 mt-1">
              Motion prompt aktif — biaya render 2x lipat
            </p>
          )}
        </div>

        {/* Background color */}
        <div className="flex items-center gap-3">
          <label className="text-zinc-400 text-sm">Background</label>
          <input
            type="color"
            value={bgColor}
            onChange={(e) => setBgColor(e.target.value)}
            className="w-8 h-8 rounded cursor-pointer bg-transparent border border-zinc-700"
          />
          <span className="text-xs text-zinc-500">{bgColor}</span>
        </div>

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Progress */}
        {generating && progress && (
          <div className="p-3 bg-zinc-900 rounded text-sm text-zinc-300 flex items-center gap-2">
            <svg
              className="animate-spin h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            {progress}
          </div>
        )}

        {/* Generate button */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-zinc-500">Estimasi: {estimatedCost}</p>
          <Button
            onClick={handleGenerate}
            disabled={generating || !selectedAvatar || !script || !selectedVoice}
          >
            {generating ? "Generating..." : "Generate Video"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
