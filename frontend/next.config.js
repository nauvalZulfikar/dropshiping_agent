/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.tokopedia.net" },
      { protocol: "https", hostname: "**.tokopedia.com" },
      { protocol: "https", hostname: "**.shopee.co.id" },
      { protocol: "https", hostname: "**.shopeecdn.com" },
      { protocol: "https", hostname: "**.aliexpress.com" },
      { protocol: "https", hostname: "ae01.alicdn.com" },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
