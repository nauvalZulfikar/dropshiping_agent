import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function ConnectCard() {
  return (
    <Card className="max-w-lg mx-auto mt-12">
      <CardContent className="p-8 text-center space-y-6">
        <div className="text-5xl">📱</div>
        <h2 className="text-xl font-bold">Connect your TikTok Account</h2>
        <p className="text-sm text-zinc-400">
          Link your TikTok account to auto-post product videos directly from
          this dashboard. Drive traffic to your dropship store without leaving
          the app.
        </p>

        <div className="text-left bg-zinc-900 rounded-lg p-4 text-sm space-y-2">
          <p className="text-zinc-300 font-medium mb-2">
            Permissions requested:
          </p>
          <div className="flex items-center gap-2 text-zinc-400">
            <span className="text-green-400">&#10003;</span>
            <span>
              <strong className="text-zinc-300">user.info.basic</strong> — Read
              your profile info
            </span>
          </div>
          <div className="flex items-center gap-2 text-zinc-400">
            <span className="text-green-400">&#10003;</span>
            <span>
              <strong className="text-zinc-300">video.upload</strong> — Upload
              videos to your account
            </span>
          </div>
          <div className="flex items-center gap-2 text-zinc-400">
            <span className="text-green-400">&#10003;</span>
            <span>
              <strong className="text-zinc-300">video.publish</strong> — Publish
              videos to your profile
            </span>
          </div>
        </div>

        <Button
          className="w-full"
          onClick={() => {
            window.location.href = "/api/tiktok/auth/init";
          }}
        >
          Connect TikTok Account
        </Button>

        <p className="text-xs text-zinc-500">
          You can disconnect at any time. We never post without your action.
        </p>
      </CardContent>
    </Card>
  );
}
