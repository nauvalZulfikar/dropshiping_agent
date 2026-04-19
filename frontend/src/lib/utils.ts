import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatIDR(n: number): string {
  return `Rp ${n.toLocaleString("id-ID")}`;
}

export function formatPct(n: number, decimals = 1): string {
  return `${(n * 100).toFixed(decimals)}%`;
}

export function maskPhone(phone: string): string {
  if (phone.length <= 8) return phone;
  return phone.slice(0, 4) + "****" + phone.slice(-4);
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    new: "bg-blue-500",
    sent_to_supplier: "bg-yellow-500",
    shipped: "bg-green-500",
    delivered: "bg-emerald-600",
    returned: "bg-red-500",
  };
  return map[status] || "bg-gray-500";
}

export function decisionColor(decision: string): string {
  const map: Record<string, string> = {
    flip_to_dropship: "bg-green-900/50 text-green-200",
    scale_affiliate: "bg-blue-900/50 text-blue-200",
    optimize: "bg-yellow-900/50 text-yellow-200",
    abandon: "bg-red-900/50 text-red-200",
  };
  return map[decision] || "";
}

export function trendIcon(trend: string): string {
  return trend === "up" ? "↑" : trend === "down" ? "↓" : "→";
}
