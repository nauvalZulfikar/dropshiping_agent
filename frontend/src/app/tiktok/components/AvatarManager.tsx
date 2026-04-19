"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Avatar {
  avatar_id: string;
  asset_id: string;
  name: string;
  preview_url: string;
  created_at: string;
}

interface Props {
  selectedAvatar: Avatar | null;
  onSelect: (avatar: Avatar) => void;
}

export function AvatarManager({ selectedAvatar, onSelect }: Props) {
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchAvatars = useCallback(async () => {
    try {
      const res = await fetch("/api/tiktok/avatars");
      const data = await res.json();
      setAvatars(data.avatars || []);
    } catch {
      setError("Failed to load avatars");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAvatars();
  }, [fetchAvatars]);

  async function handleUpload(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("Only image files (JPEG, PNG) are accepted");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("Image must be under 10MB");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("photo", file);
      formData.append("name", name || file.name.replace(/\.[^.]+$/, ""));

      const res = await fetch("/api/tiktok/avatars", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (!res.ok || data.error) {
        throw new Error(data.error || "Upload failed");
      }

      setName("");
      if (inputRef.current) inputRef.current.value = "";
      await fetchAvatars();

      // Auto-select the new avatar
      if (data.avatar) {
        onSelect(data.avatar);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(avatarId: string) {
    await fetch(`/api/tiktok/avatars?id=${avatarId}`, { method: "DELETE" });
    if (selectedAvatar?.avatar_id === avatarId) {
      onSelect(null as unknown as Avatar);
    }
    await fetchAvatars();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Avatar AI</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Upload section */}
        <div className="p-4 bg-zinc-900 rounded-lg space-y-3">
          <p className="text-sm text-zinc-400">
            Upload foto untuk dijadikan AI avatar. Foto wajah jelas, hadap
            kamera, pencahayaan bagus.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              className="flex-1 px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white text-sm"
              placeholder="Nama avatar"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Button
              size="sm"
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Upload Foto"}
            </Button>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleUpload(f);
            }}
          />
          {uploading && (
            <div className="flex items-center gap-2 text-sm text-zinc-400">
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
              Uploading ke HeyGen & membuat avatar...
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Avatar gallery */}
        {loading ? (
          <p className="text-sm text-zinc-500">Loading avatars...</p>
        ) : avatars.length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-4">
            Belum ada avatar. Upload foto di atas.
          </p>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {avatars.map((avatar) => {
              const isSelected =
                selectedAvatar?.avatar_id === avatar.avatar_id;
              return (
                <div
                  key={avatar.avatar_id}
                  className={`relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                    isSelected
                      ? "border-blue-500 ring-2 ring-blue-500/30"
                      : "border-zinc-700 hover:border-zinc-500"
                  }`}
                  onClick={() => onSelect(avatar)}
                >
                  {avatar.preview_url ? (
                    <img
                      src={avatar.preview_url}
                      alt={avatar.name}
                      className="w-full aspect-square object-cover"
                    />
                  ) : (
                    <div className="w-full aspect-square bg-zinc-800 flex items-center justify-center text-2xl">
                      👤
                    </div>
                  )}
                  <div className="absolute bottom-0 left-0 right-0 bg-black/70 px-2 py-1">
                    <p className="text-xs text-white truncate">{avatar.name}</p>
                  </div>
                  {isSelected && (
                    <div className="absolute top-1 right-1 bg-blue-500 rounded-full w-5 h-5 flex items-center justify-center text-xs">
                      &#10003;
                    </div>
                  )}
                  <button
                    className="absolute top-1 left-1 bg-red-600/80 hover:bg-red-600 rounded-full w-5 h-5 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(avatar.avatar_id);
                    }}
                  >
                    &#10005;
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {selectedAvatar && (
          <p className="text-sm text-green-400">
            Avatar dipilih: <strong>{selectedAvatar.name}</strong>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
