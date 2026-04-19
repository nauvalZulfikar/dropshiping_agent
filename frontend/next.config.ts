import type { NextConfig } from "next";
import { resolve } from "path";

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: resolve(import.meta.dirname || "."),
  },
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [
        {
          source: "/api/dashboard/:path*",
          destination: `${process.env.API_URL || "http://localhost:8003"}/dashboard/:path*`,
        },
      ],
      fallback: [],
    };
  },
};

export default nextConfig;
