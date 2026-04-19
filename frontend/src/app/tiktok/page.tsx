"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import type { TikTokUser, RecentPost } from "@/lib/tiktok/types";
import { ConnectCard } from "./components/ConnectCard";
import { ConnectedAccountCard } from "./components/ConnectedAccountCard";
import { AvatarManager } from "./components/AvatarManager";
import { VideoGenerator } from "./components/VideoGenerator";
import { VideoPreview } from "./components/VideoPreview";
import { PostComposer } from "./components/PostComposer";
import { SuccessCard } from "./components/SuccessCard";

interface SelectedAvatar {
  avatar_id: string;
  asset_id: string;
  name: string;
  preview_url: string;
  created_at: string;
}

interface GeneratedVideo {
  video_id: string;
  video_url: string;
  duration: number;
}

export default function TikTokPage() {
  return (
    <Suspense>
      <TikTokPageInner />
    </Suspense>
  );
}

function TikTokPageInner() {
  const searchParams = useSearchParams();

  // TikTok connection
  const [tiktokConnected, setTiktokConnected] = useState(false);
  const [tiktokUser, setTiktokUser] = useState<TikTokUser | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [checkingConnection, setCheckingConnection] = useState(true);

  // Avatar
  const [selectedAvatar, setSelectedAvatar] = useState<SelectedAvatar | null>(null);

  // Generated video
  const [generatedVideo, setGeneratedVideo] = useState<GeneratedVideo | null>(null);

  // TikTok posting
  const [postMode, setPostMode] = useState(false);
  const [lastPublishId, setLastPublishId] = useState("");
  const [recentPosts, setRecentPosts] = useState<RecentPost[]>([]);

  // Error
  const [error, setError] = useState("");

  const checkConnection = useCallback(async () => {
    try {
      const res = await fetch("/api/tiktok/user/info");
      const data = await res.json();
      if (data.connected && data.user) {
        setTiktokUser(data.user);
        setTiktokConnected(true);
      }
    } catch {
      // not connected
    } finally {
      setCheckingConnection(false);
    }
  }, []);

  useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  useEffect(() => {
    const errParam = searchParams.get("error");
    if (errParam) setError(decodeURIComponent(errParam));
  }, [searchParams]);

  async function handleDisconnect() {
    setDisconnecting(true);
    await fetch("/api/tiktok/auth/disconnect", { method: "POST" });
    setTiktokUser(null);
    setTiktokConnected(false);
    setDisconnecting(false);
  }

  function handleVideoReady(video: GeneratedVideo) {
    setGeneratedVideo(video);
  }

  function handlePublished(publishId: string, caption: string) {
    setLastPublishId(publishId);
    setRecentPosts((prev) => [
      {
        publish_id: publishId,
        caption,
        status: "PUBLISH_COMPLETE",
        posted_at: new Date().toLocaleString("id-ID"),
      },
      ...prev,
    ]);
    setPostMode(false);
    setGeneratedVideo(null);
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">TikTok Publishing</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Buat AI avatar video dan post langsung ke TikTok.
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-300 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError("")}
            className="text-red-400 hover:text-red-200 ml-4"
          >
            &#10005;
          </button>
        </div>
      )}

      {/* Success from last post */}
      {lastPublishId && !postMode && !generatedVideo && (
        <SuccessCard
          publishId={lastPublishId}
          onPostAnother={() => setLastPublishId("")}
          recentPosts={recentPosts}
        />
      )}

      {/* Step 1: Avatar Manager — always visible */}
      {!checkingConnection && (
        <AvatarManager
          selectedAvatar={selectedAvatar}
          onSelect={setSelectedAvatar}
        />
      )}

      {/* Step 2: Video Generator — visible after avatar selected */}
      {selectedAvatar && !generatedVideo && !postMode && (
        <VideoGenerator
          selectedAvatar={selectedAvatar}
          onVideoReady={handleVideoReady}
        />
      )}

      {/* Step 3: Video Preview — after generation complete */}
      {generatedVideo && !postMode && (
        <VideoPreview
          video={generatedVideo}
          tiktokConnected={tiktokConnected}
          onPostToTikTok={() => setPostMode(true)}
          onGenerateAnother={() => setGeneratedVideo(null)}
        />
      )}

      {/* Step 4: Post to TikTok — after clicking "Post to TikTok" on preview */}
      {postMode && generatedVideo && tiktokConnected && tiktokUser && (
        <div className="space-y-6">
          <ConnectedAccountCard
            user={tiktokUser}
            onDisconnect={handleDisconnect}
            disconnecting={disconnecting}
          />
          <PostComposer
            onPublished={handlePublished}
            selectedAvatar={selectedAvatar}
            preloadedVideoUrl={generatedVideo.video_url}
          />
        </div>
      )}

      {/* TikTok Connection — show at bottom if not connected */}
      {!checkingConnection && !tiktokConnected && (
        <ConnectCard />
      )}

      {/* Connected account info — show at bottom if connected but not in post mode */}
      {tiktokConnected && tiktokUser && !postMode && (
        <ConnectedAccountCard
          user={tiktokUser}
          onDisconnect={handleDisconnect}
          disconnecting={disconnecting}
        />
      )}
    </div>
  );
}
