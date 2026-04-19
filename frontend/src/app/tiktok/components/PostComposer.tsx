import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { VideoUploader } from "./VideoUploader";
import type { CreatorInfo } from "@/lib/tiktok/types";

interface SelectedAvatar {
  avatar_id: string;
  name: string;
}

interface Props {
  onPublished: (publishId: string, caption: string) => void;
  selectedAvatar: SelectedAvatar | null;
  preloadedVideoUrl?: string;
}

const PRODUCTS = ["Product A", "Product B", "Product C"];

const PRIVACY_LABELS: Record<string, string> = {
  PUBLIC_TO_EVERYONE: "Public",
  MUTUAL_FOLLOW_FRIENDS: "Friends",
  FOLLOWER_OF_CREATOR: "Followers",
  SELF_ONLY: "Only me",
};

const isSandbox = process.env.NEXT_PUBLIC_TIKTOK_ENV === "sandbox";

const STATUS_MESSAGES: Record<string, string> = {
  PROCESSING_UPLOAD: "Uploading to TikTok...",
  PROCESSING_DOWNLOAD: "Processing video...",
  SEND_TO_USER_INBOX: "Publishing...",
};

export function PostComposer({ onPublished, selectedAvatar, preloadedVideoUrl }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [product, setProduct] = useState(PRODUCTS[0]);
  const [privacy, setPrivacy] = useState("SELF_ONLY");
  const [allowComment, setAllowComment] = useState(true);
  const [allowDuet, setAllowDuet] = useState(false);
  const [allowStitch, setAllowStitch] = useState(false);
  const [motionPrompt, setMotionPrompt] = useState("");

  const [creatorInfo, setCreatorInfo] = useState<CreatorInfo | null>(null);
  const [loadingCreator, setLoadingCreator] = useState(true);

  const [posting, setPosting] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/tiktok/creator/info")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setError(data.error);
        } else {
          setCreatorInfo(data);
          if (data.privacy_level_options?.length) {
            setPrivacy(data.privacy_level_options[0]);
          }
          setAllowComment(!data.comment_disabled);
          setAllowDuet(!data.duet_disabled);
          setAllowStitch(!data.stitch_disabled);
        }
      })
      .catch(() => setError("Failed to load creator info"))
      .finally(() => setLoadingCreator(false));
  }, []);

  async function handlePost() {
    if (!file) return;
    setPosting(true);
    setError("");
    setProgress("Initializing upload...");

    try {
      // Step 1: Init publish
      const initRes = await fetch("/api/tiktok/publish/init", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: caption,
          privacy_level: privacy,
          disable_comment: !allowComment,
          disable_duet: !allowDuet,
          disable_stitch: !allowStitch,
          video_size: file.size,
        }),
      });
      const initData = await initRes.json();
      if (!initRes.ok || initData.error) {
        throw new Error(initData.error || "Publish init failed");
      }

      // Step 2: Upload video
      setProgress("Uploading video...");
      const formData = new FormData();
      formData.append("upload_url", initData.upload_url);
      formData.append("video", file);

      const uploadRes = await fetch("/api/tiktok/publish/upload", {
        method: "POST",
        body: formData,
      });
      const uploadData = await uploadRes.json();
      if (!uploadRes.ok || uploadData.error) {
        throw new Error(uploadData.error || "Upload failed");
      }

      // Step 3: Poll status — every 2s, up to 60s
      setProgress("Processing...");
      const publishId = initData.publish_id;
      let attempts = 0;
      const maxAttempts = 30; // 30 × 2s = 60s

      while (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 2000));
        const statusRes = await fetch("/api/tiktok/publish/status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ publish_id: publishId }),
        });
        const statusData = await statusRes.json();

        if (statusData.status === "PUBLISH_COMPLETE") {
          onPublished(publishId, caption);
          return;
        }
        if (statusData.status === "FAILED") {
          throw new Error(statusData.fail_reason || "Publishing failed");
        }

        setProgress(STATUS_MESSAGES[statusData.status] || `Processing... (${statusData.status})`);
        attempts++;
      }

      // Timeout — don't treat as error, video may still publish
      onPublished(publishId, caption);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setPosting(false);
      setProgress("");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Post</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Product selector */}
        <div>
          <label className="text-zinc-400 text-sm">Product</label>
          <select
            className="w-full mt-1 px-3 py-2 bg-zinc-800 rounded border border-zinc-700 text-white text-sm"
            value={product}
            onChange={(e) => setProduct(e.target.value)}
          >
            {PRODUCTS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        {/* Video uploader */}
        <VideoUploader file={file} onFileChange={setFile} />

        {/* Caption */}
        <div>
          <label className="text-zinc-400 text-sm">
            Caption ({caption.length}/2200)
          </label>
          <textarea
            className="w-full mt-1 px-3 py-2 bg-zinc-800 rounded border border-zinc-700 text-white text-sm resize-none"
            rows={3}
            maxLength={2200}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Write a caption for your TikTok..."
          />
        </div>

        {/* Sandbox notice */}
        {isSandbox && (
          <div className="p-3 bg-yellow-900/20 border border-yellow-700/50 rounded text-sm text-yellow-300">
            Sandbox mode: videos are only visible to the posting account.
          </div>
        )}

        {/* Privacy level */}
        <div>
          <label className="text-zinc-400 text-sm">Privacy</label>
          {loadingCreator ? (
            <p className="text-xs text-zinc-500 mt-1">Loading options...</p>
          ) : (
            <select
              className="w-full mt-1 px-3 py-2 bg-zinc-800 rounded border border-zinc-700 text-white text-sm"
              value={isSandbox ? "SELF_ONLY" : privacy}
              onChange={(e) => setPrivacy(e.target.value)}
              disabled={isSandbox}
            >
              {isSandbox ? (
                <option value="SELF_ONLY">Only me (Sandbox)</option>
              ) : (
                (creatorInfo?.privacy_level_options || ["SELF_ONLY"]).map((opt) => (
                  <option key={opt} value={opt}>
                    {PRIVACY_LABELS[opt] || opt}
                  </option>
                ))
              )}
            </select>
          )}
        </div>

        {/* Toggles */}
        <div className="flex gap-6 text-sm">
          <label className="flex items-center gap-2 text-zinc-400">
            <input
              type="checkbox"
              checked={allowComment}
              onChange={(e) => setAllowComment(e.target.checked)}
              disabled={creatorInfo?.comment_disabled}
              className="accent-white"
            />
            Comments
          </label>
          <label className="flex items-center gap-2 text-zinc-400">
            <input
              type="checkbox"
              checked={allowDuet}
              onChange={(e) => setAllowDuet(e.target.checked)}
              disabled={creatorInfo?.duet_disabled}
              className="accent-white"
            />
            Duet
          </label>
          <label className="flex items-center gap-2 text-zinc-400">
            <input
              type="checkbox"
              checked={allowStitch}
              onChange={(e) => setAllowStitch(e.target.checked)}
              disabled={creatorInfo?.stitch_disabled}
              className="accent-white"
            />
            Stitch
          </label>
        </div>

        {/* Selected Avatar */}
        {selectedAvatar ? (
          <div className="p-3 bg-zinc-900 rounded text-sm flex items-center gap-2">
            <span>👤</span>
            <span className="text-zinc-300">Avatar: <strong>{selectedAvatar.name}</strong></span>
          </div>
        ) : (
          <div className="p-3 bg-yellow-900/20 border border-yellow-700/50 rounded text-sm text-yellow-300">
            Pilih avatar di atas sebelum posting.
          </div>
        )}

        {/* Motion Prompt */}
        <div>
          <label className="text-zinc-400 text-sm">
            Motion Prompt <span className="text-zinc-600">(opsional, biaya 2x)</span>
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

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Progress */}
        {posting && progress && (
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

        {/* Submit */}
        <Button
          className="w-full"
          onClick={handlePost}
          disabled={!file || posting}
        >
          {posting ? "Posting..." : "Post to TikTok"}
        </Button>
      </CardContent>
    </Card>
  );
}
