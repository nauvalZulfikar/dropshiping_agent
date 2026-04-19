"use client";

import { useState, useEffect, useRef } from "react";

export interface Voice {
  voice_id: string;
  name: string;
  gender: string;
  preview_url: string;
}

interface Props {
  selectedVoice: Voice | null;
  onSelect: (voice: Voice) => void;
}

export function VoicePicker({ selectedVoice, onSelect }: Props) {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetch("/api/tiktok/voices")
      .then((r) => r.json())
      .then((data) => setVoices(data.voices || []))
      .finally(() => setLoading(false));
  }, []);

  function playPreview(voice: Voice) {
    if (!voice.preview_url) return;
    if (audioRef.current) {
      audioRef.current.pause();
    }
    if (playing === voice.voice_id) {
      setPlaying(null);
      return;
    }
    const audio = new Audio(voice.preview_url);
    audio.onended = () => setPlaying(null);
    audio.play();
    audioRef.current = audio;
    setPlaying(voice.voice_id);
  }

  if (loading) {
    return <p className="text-sm text-zinc-500">Loading voices...</p>;
  }

  const males = voices.filter((v) => v.gender === "male");
  const females = voices.filter((v) => v.gender === "female");

  return (
    <div className="space-y-2">
      <label className="text-zinc-400 text-sm">Suara</label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
        {[
          { label: "Male", list: males },
          { label: "Female", list: females },
        ].map(({ label, list }) => (
          <div key={label} className="space-y-1">
            <p className="text-xs text-zinc-500 font-medium">{label}</p>
            {list.map((v) => {
              const isSelected = selectedVoice?.voice_id === v.voice_id;
              return (
                <div
                  key={v.voice_id}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer text-sm transition-all ${
                    isSelected
                      ? "bg-blue-600/20 border border-blue-500 text-white"
                      : "bg-zinc-900 border border-zinc-800 text-zinc-300 hover:border-zinc-600"
                  }`}
                  onClick={() => onSelect(v)}
                >
                  <span className="flex-1 truncate">{v.name}</span>
                  {v.preview_url && (
                    <button
                      className="text-xs text-zinc-400 hover:text-white shrink-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        playPreview(v);
                      }}
                    >
                      {playing === v.voice_id ? "⏹" : "▶"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {selectedVoice && (
        <p className="text-xs text-green-400">
          Dipilih: {selectedVoice.name} ({selectedVoice.gender})
        </p>
      )}
    </div>
  );
}
