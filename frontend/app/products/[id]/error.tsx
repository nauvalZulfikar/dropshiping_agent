"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[Product Detail Error]", error);
  }, [error]);

  return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[50vh] text-center">
      <p className="text-4xl mb-4">🔍</p>
      <h2 className="text-xl font-semibold mb-2">Product not found</h2>
      <p className="text-muted-foreground text-sm mb-6 max-w-sm">
        {error.message || "This product may have been removed or the ID is invalid."}
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="px-4 py-2 bg-primary text-primary-foreground rounded text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Retry
        </button>
        <Link href="/products" className="px-4 py-2 bg-secondary border border-border rounded text-sm hover:border-primary transition-colors">
          Back to Products
        </Link>
      </div>
    </div>
  );
}
