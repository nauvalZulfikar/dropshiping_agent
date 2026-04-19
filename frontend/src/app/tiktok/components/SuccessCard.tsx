import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { RecentPost } from "@/lib/tiktok/types";

interface Props {
  publishId: string;
  onPostAnother: () => void;
  recentPosts: RecentPost[];
}

export function SuccessCard({ publishId, onPostAnother, recentPosts }: Props) {
  return (
    <div className="space-y-6">
      <Card className="max-w-lg mx-auto">
        <CardContent className="p-8 text-center space-y-4">
          <div className="text-5xl">&#10003;</div>
          <h2 className="text-xl font-bold text-green-400">
            Video posted to TikTok successfully
          </h2>
          <p className="text-sm text-zinc-400">
            Publish ID:{" "}
            <code className="bg-zinc-800 px-2 py-0.5 rounded text-xs">
              {publishId}
            </code>
          </p>
          <Button onClick={onPostAnother}>Post Another Video</Button>
        </CardContent>
      </Card>

      {recentPosts.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h3 className="text-sm font-semibold mb-3 text-zinc-300">
              Recent Posts
            </h3>
            <div className="space-y-2">
              {recentPosts.map((post) => (
                <div
                  key={post.publish_id}
                  className="flex items-center justify-between p-3 bg-zinc-900 rounded text-sm"
                >
                  <div>
                    <p className="text-zinc-200 truncate max-w-xs">
                      {post.caption || "(no caption)"}
                    </p>
                    <p className="text-xs text-zinc-500">{post.posted_at}</p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      post.status === "PUBLISH_COMPLETE"
                        ? "bg-green-600"
                        : "bg-zinc-600"
                    }`}
                  >
                    {post.status === "PUBLISH_COMPLETE" ? "Published" : post.status}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
