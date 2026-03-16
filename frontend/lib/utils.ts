import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatIdr(amount: number): string {
  return `Rp ${amount.toLocaleString("id-ID")}`;
}

export function marginColor(pct: number | null | undefined): string {
  if (pct == null) return "text-muted-foreground";
  if (pct >= 30) return "text-green-400";
  if (pct >= 15) return "text-yellow-400";
  return "text-red-400";
}
