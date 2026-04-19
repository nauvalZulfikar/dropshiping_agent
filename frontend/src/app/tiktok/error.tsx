"use client";

import { useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function TikTokError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[TikTok Page Error]", error);
  }, [error]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">TikTok Publishing</h1>
      <Card className="max-w-lg mx-auto mt-12">
        <CardContent className="p-8 text-center space-y-4">
          <div className="text-5xl">&#9888;</div>
          <h2 className="text-xl font-bold text-red-400">
            Something went wrong
          </h2>
          <p className="text-sm text-zinc-400">
            {error.message || "Couldn't connect to TikTok. Please try again."}
          </p>
          <div className="flex gap-3 justify-center">
            <Button onClick={reset}>Try Again</Button>
            <Button
              variant="outline"
              onClick={() => (window.location.href = "/tiktok")}
            >
              Back to TikTok
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
