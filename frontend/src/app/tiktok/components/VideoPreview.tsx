"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface GeneratedVideo {
  video_id: string;
  video_url: string;
  duration: number;
}

interface Props {
  video: GeneratedVideo;
  onPostToTikTok: () => void;
  onGenerateAnother: () => void;
  tiktokConnected: boolean;
}

export function VideoPreview({
  video,
  onPostToTikTok,
  onGenerateAnother,
  tiktokConnected,
}: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Video Preview</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Video player */}
        <div className="rounded-lg overflow-hidden bg-black max-w-sm mx-auto">
          <video
            src={video.video_url}
            controls
            className="w-full"
            style={{ maxHeight: "500px" }}
          />
        </div>

        {/* Info */}
        <div className="flex items-center justify-between text-sm text-zinc-400">
          <span>Duration: {video.duration.toFixed(1)}s</span>
          <code className="bg-zinc-800 px-2 py-0.5 rounded text-xs">
            {video.video_id.slice(0, 12)}...
          </code>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          {tiktokConnected ? (
            <Button className="flex-1" onClick={onPostToTikTok}>
              Post to TikTok
            </Button>
          ) : (
            <div className="flex-1 p-3 bg-zinc-900 rounded text-sm text-zinc-400 text-center">
              Connect TikTok dulu untuk post
            </div>
          )}
          <Button variant="outline" onClick={onGenerateAnother}>
            Generate Lagi
          </Button>
        </div>

        {/* Download */}
        <a
          href={video.video_url}
          download={`video_${video.video_id.slice(0, 8)}.mp4`}
          className="block text-center text-sm text-blue-400 hover:text-blue-300"
        >
          Download .mp4
        </a>
      </CardContent>
    </Card>
  );
}
