"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

const NAV_ITEMS = [
  { href: "/overview", label: "Overview", icon: "📊" },
  { href: "/affiliate", label: "Affiliate Intelligence", icon: "🔗" },
  { href: "/orders", label: "Orders & Fulfillment", icon: "📦" },
  { href: "/products", label: "Products & Inventory", icon: "🏷️" },
  { href: "/cs-analytics", label: "CS Bot Analytics", icon: "🤖" },
  { href: "/business-intelligence", label: "Business Intelligence", icon: "💡" },
  { href: "/automation", label: "Automation", icon: "⚡" },
  { href: "/tiktok", label: "TikTok Publishing", icon: "📱" },
  { href: "/returns", label: "Returns & Disputes", icon: "↩️" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [time, setTime] = useState("");

  useEffect(() => {
    const tick = () => {
      setTime(
        new Date().toLocaleTimeString("id-ID", {
          timeZone: "Asia/Jakarta",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }) + " WIB"
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <aside className="w-64 min-h-screen bg-zinc-950 border-r border-zinc-800 flex flex-col">
      <div className="p-6">
        <h1 className="text-lg font-bold">Dropship Dashboard</h1>
        <p className="text-xs text-zinc-500 mt-1">Automation Engine</p>
      </div>

      <nav className="flex-1 px-3">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm mb-1 transition-colors",
              pathname === item.href
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:bg-zinc-900 hover:text-white"
            )}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t border-zinc-800">
        <p className="text-xs text-zinc-500">{time}</p>
        <p className="text-xs text-zinc-600 mt-1">Production</p>
      </div>
    </aside>
  );
}
