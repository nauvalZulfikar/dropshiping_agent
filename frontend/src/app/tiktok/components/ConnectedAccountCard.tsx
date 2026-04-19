import { Card, CardContent } from "@/components/ui/card";
import type { TikTokUser } from "@/lib/tiktok/types";

interface Props {
  user: TikTokUser;
  onDisconnect: () => void;
  disconnecting: boolean;
}

export function ConnectedAccountCard({ user, onDisconnect, disconnecting }: Props) {
  return (
    <Card>
      <CardContent className="p-4 flex items-center gap-4">
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.display_name}
            className="w-12 h-12 rounded-full object-cover bg-zinc-700"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-zinc-700 flex items-center justify-center text-xl">
            📱
          </div>
        )}
        <div className="flex-1">
          <p className="font-semibold">{user.display_name || "TikTok User"}</p>
          {user.username && (
            <p className="text-sm text-zinc-400">@{user.username}</p>
          )}
        </div>
        <button
          onClick={onDisconnect}
          disabled={disconnecting}
          className="text-sm text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
        >
          {disconnecting ? "Disconnecting..." : "Disconnect"}
        </button>
      </CardContent>
    </Card>
  );
}
