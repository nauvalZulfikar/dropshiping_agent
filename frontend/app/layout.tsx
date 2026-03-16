import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Nav } from "@/components/nav";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Dropship Research — Indonesian Market Intelligence",
  description: "Automated product research platform for Indonesian dropshipping. Ranked by margin & sellability.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className="dark">
      <body className={inter.className}>
        <Providers>
          <div className="flex min-h-screen">
            <Nav />
            <div className="flex-1 ml-56 min-h-screen bg-background">
              {children}
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
