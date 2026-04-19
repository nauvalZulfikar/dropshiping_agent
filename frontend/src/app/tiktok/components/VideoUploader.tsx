import { useRef, useState, useCallback } from "react";

interface Props {
  file: File | null;
  onFileChange: (file: File | null) => void;
}

const MAX_SIZE = 50 * 1024 * 1024; // 50MB
const ACCEPTED = ".mp4,.mov";

export function VideoUploader({ file, onFileChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = useCallback(
    (f: File | null) => {
      setError("");
      if (!f) {
        setPreview(null);
        onFileChange(null);
        return;
      }

      if (f.size > MAX_SIZE) {
        setError(`File too large (${(f.size / 1024 / 1024).toFixed(1)}MB). Max 50MB.`);
        return;
      }

      if (!f.type.startsWith("video/")) {
        setError("Only .mp4 and .mov video files are accepted.");
        return;
      }

      const url = URL.createObjectURL(f);
      setPreview(url);
      onFileChange(f);
    },
    [onFileChange],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  return (
    <div className="space-y-2">
      <label className="text-zinc-400 text-sm">Video</label>

      {preview && file ? (
        <div className="relative">
          <video
            src={preview}
            className="w-full max-h-64 rounded-lg bg-black object-contain"
            controls
          />
          <div className="flex items-center justify-between mt-2 text-sm">
            <span className="text-zinc-400 truncate max-w-[70%]">
              {file.name} ({(file.size / 1024 / 1024).toFixed(1)}MB)
            </span>
            <button
              className="text-red-400 hover:text-red-300"
              onClick={() => {
                handleFile(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <div
          className="border-2 border-dashed border-zinc-700 rounded-lg p-8 text-center cursor-pointer hover:border-zinc-500 transition-colors"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <div className="text-3xl mb-2">🎬</div>
          <p className="text-sm text-zinc-400">
            Click to select or drag & drop
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            .mp4 or .mov, max 50MB, max 60 seconds
          </p>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
      />

      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
