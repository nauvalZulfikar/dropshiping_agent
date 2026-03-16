"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";

interface Job {
  id: string;
  source: string;
  job_type: string;
  status: string;
  items_scraped?: number;
  items_failed?: number;
  error_message?: string;
  started_at?: string;
  finished_at?: string;
  created_at: string;
}

interface Stat {
  source: string;
  total_jobs: number;
  succeeded: number;
  failed: number;
  pending: number;
  total_scraped?: number;
  last_run?: string;
}

const STATUS_COLOR: Record<string, string> = {
  success: "text-green-400",
  pending: "text-yellow-400",
  running: "text-blue-400",
  failed: "text-red-400",
};

export default function ScraperPage() {
  const queryClient = useQueryClient();
  const [source, setSource] = useState("tokopedia");
  const [keyword, setKeyword] = useState("");
  const [maxPages, setMaxPages] = useState(3);
  const [lastTaskId, setLastTaskId] = useState<string | null>(null);

  const { data: jobsData, isLoading: jobsLoading } = useQuery<{ jobs: Job[] }>({
    queryKey: ["scraper", "jobs"],
    queryFn: () => api.get("/api/scraper/jobs", { params: { limit: 30 } }).then((r) => r.data),
    refetchInterval: 10_000,
  });

  const { data: statsData } = useQuery<{ items: Stat[] }>({
    queryKey: ["scraper", "stats"],
    queryFn: () => api.get("/api/scraper/stats").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: taskStatus } = useQuery({
    queryKey: ["scraper", "task", lastTaskId],
    queryFn: () => api.get(`/api/scraper/status/${lastTaskId}`).then((r) => r.data),
    enabled: !!lastTaskId,
    refetchInterval: (data) => {
      if (!data || data.status === "PENDING" || data.status === "STARTED") return 3000;
      return false;
    },
  });

  const triggerMutation = useMutation({
    mutationFn: () => api.post("/api/scraper/trigger", { source, keyword, max_pages: maxPages }),
    onSuccess: (res) => {
      setLastTaskId(res.data.task_id);
      queryClient.invalidateQueries({ queryKey: ["scraper", "jobs"] });
    },
  });

  const jobs = jobsData?.jobs ?? [];
  const stats = statsData?.items ?? [];

  return (
    <main className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Scraper Control</h1>
        <p className="text-muted-foreground text-sm">Trigger manual scrapes and monitor job history</p>
      </div>

      {/* Stats cards */}
      {stats.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {stats.map((s) => (
            <div key={s.source} className="bg-card rounded-lg p-4 border border-border">
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2 capitalize">{s.source}</p>
              <div className="grid grid-cols-3 gap-1 text-xs">
                <div><p className="text-muted-foreground">OK</p><p className="text-green-400 font-bold">{s.succeeded}</p></div>
                <div><p className="text-muted-foreground">Fail</p><p className="text-red-400 font-bold">{s.failed}</p></div>
                <div><p className="text-muted-foreground">Items</p><p className="font-bold">{s.total_scraped?.toLocaleString() ?? 0}</p></div>
              </div>
              {s.last_run && (
                <p className="text-xs text-muted-foreground mt-2">
                  Last: {new Date(s.last_run).toLocaleString("id-ID")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Trigger form */}
      <div className="bg-card rounded-lg p-6 border border-border mb-8">
        <h2 className="font-semibold mb-4">Trigger Scrape</h2>
        <div className="flex gap-4 flex-wrap items-end">
          <div>
            <label className="text-sm text-muted-foreground block mb-1">Source</label>
            <select
              className="bg-background border border-border rounded px-3 py-2 text-sm"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            >
              <option value="tokopedia">Tokopedia</option>
              <option value="shopee">Shopee</option>
              <option value="aliexpress">AliExpress</option>
            </select>
          </div>
          <div className="flex-1 min-w-40">
            <label className="text-sm text-muted-foreground block mb-1">Keyword</label>
            <input
              type="text"
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm"
              placeholder="e.g. phone case"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && keyword && triggerMutation.mutate()}
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground block mb-1">Pages</label>
            <input
              type="number"
              className="bg-background border border-border rounded px-3 py-2 text-sm w-20"
              min={1}
              max={10}
              value={maxPages}
              onChange={(e) => setMaxPages(Number(e.target.value))}
            />
          </div>
          <button
            className="px-5 py-2 bg-primary text-primary-foreground rounded text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
            disabled={!keyword || triggerMutation.isPending}
            onClick={() => triggerMutation.mutate()}
          >
            {triggerMutation.isPending ? "Queuing…" : "Run Scrape"}
          </button>
        </div>

        {/* Task status */}
        {lastTaskId && taskStatus && (
          <div className="mt-4 p-3 bg-secondary rounded text-sm">
            <span className="text-muted-foreground">Task {lastTaskId.slice(0, 8)}… — </span>
            <span className={STATUS_COLOR[taskStatus.status?.toLowerCase()] ?? "text-foreground"}>
              {taskStatus.status}
            </span>
            {taskStatus.result && (
              <span className="text-muted-foreground ml-2">
                · scraped: {taskStatus.result.scraped ?? "?"}, failed: {taskStatus.result.failed ?? "?"}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Job history */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Recent Jobs</h2>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-secondary text-muted-foreground">
              <tr>
                {["Source", "Keyword", "Status", "Scraped", "Failed", "Error", "Started", "Finished"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobsLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-t border-border animate-pulse">
                      {Array.from({ length: 8 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><div className="h-4 bg-secondary rounded" /></td>
                      ))}
                    </tr>
                  ))
                : jobs.map((job) => (
                    <tr key={job.id} className="border-t border-border hover:bg-secondary/30">
                      <td className="px-4 py-3 capitalize font-medium">{job.source}</td>
                      <td className="px-4 py-3 max-w-xs">
                        <span className="line-clamp-1">{job.job_type.replace("search:", "")}</span>
                      </td>
                      <td className={`px-4 py-3 font-semibold ${STATUS_COLOR[job.status] ?? "text-foreground"}`}>
                        {job.status}
                      </td>
                      <td className="px-4 py-3">{job.items_scraped?.toLocaleString() ?? "—"}</td>
                      <td className="px-4 py-3">{job.items_failed?.toLocaleString() ?? "—"}</td>
                      <td className="px-4 py-3 max-w-xs text-red-400 text-xs">
                        <span className="line-clamp-1">{job.error_message ?? ""}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {job.started_at ? new Date(job.started_at).toLocaleString("id-ID") : "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {job.finished_at ? new Date(job.finished_at).toLocaleString("id-ID") : "—"}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
