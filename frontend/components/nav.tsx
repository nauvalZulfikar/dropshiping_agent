"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard", icon: "⚡" },
  { href: "/products", label: "Products", icon: "📦" },
  { href: "/niches", label: "Niches", icon: "🔬" },
  { href: "/suppliers", label: "Suppliers", icon: "🏭" },
  { href: "/watchlist", label: "Watchlist", icon: "👁" },
  { href: "/scraper", label: "Scraper", icon: "🕷" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-card border-r border-border flex flex-col z-40">
      <div className="px-4 py-5 border-b border-border">
        <p className="text-xs text-muted-foreground uppercase tracking-widest mb-0.5">Dropship</p>
        <h1 className="font-bold text-lg leading-tight">Research Agent</h1>
      </div>
      <nav className="flex-1 py-4 px-2 space-y-0.5">
        {links.map(({ href, label, icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                active
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <span className="text-base">{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t border-border text-xs text-muted-foreground">
        ID Marketplace Intel
      </div>
    </aside>
  );
}
