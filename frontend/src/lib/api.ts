import useSWR from "swr";

const BASE = "/api/dashboard";

async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function useDashboard<T>(path: string, refreshInterval = 300_000) {
  return useSWR<T>(`${BASE}${path}`, fetcher, {
    refreshInterval,
    revalidateOnFocus: false,
  });
}
