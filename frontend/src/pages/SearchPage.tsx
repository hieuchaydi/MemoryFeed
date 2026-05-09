import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchNativeStatus, fetchStats, patchItem, searchFeed } from "../api/client";
import ResultCard from "../components/ResultCard";
import { useSettings } from "../settings";
import type { FeedItem } from "../types";

function useDebounced(value: string, ms = 280): string {
  const [state, setState] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setState(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return state;
}

export default function SearchPage() {
  const { t } = useSettings();
  const [query, setQuery] = useState("");
  const [daysBack, setDaysBack] = useState("30");
  const [starredOnly, setStarredOnly] = useState(false);
  const debounced = useDebounced(query, 300);
  const qc = useQueryClient();

  const searchQ = useQuery({
    queryKey: ["search", debounced, daysBack],
    queryFn: () => searchFeed(debounced, { limit: 24, daysBack: Number(daysBack) || undefined }),
    enabled: debounced.trim().length > 0,
  });

  const statsQ = useQuery({ queryKey: ["stats"], queryFn: fetchStats });
  const nativeQ = useQuery({ queryKey: ["native"], queryFn: fetchNativeStatus, staleTime: 30_000 });

  const starMut = useMutation({
    mutationFn: ({ id, starred }: { id: string; starred: boolean }) => patchItem(id, { starred }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["search"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const rawResults = searchQ.data?.results || [];
  const results = useMemo(() => {
    const filtered = starredOnly ? rawResults.filter((x) => x.starred) : rawResults;
    const videos = filtered.filter((item) => isVideoItem(item));
    const nonVideos = filtered.filter((item) => !isVideoItem(item));
    videos.sort((a, b) => toEpoch(b.captured_at) - toEpoch(a.captured_at));
    return [...videos, ...nonVideos];
  }, [rawResults, starredOnly]);

  return (
    <section className="page">
      <div className="hero-panel">
        <h1>{t.search.title}</h1>
        <p>
          {t.search.description} <span className="muted-label">{t.search.examples}:</span>{" "}
          <code>meme mèo giận tuần trước</code> <code>startup culture failure</code>
        </p>

        <div className="query-grid">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.search.placeholder}
            className="query-input"
          />
          <select value={daysBack} onChange={(e) => setDaysBack(e.target.value)} className="days-select">
            <option value="">{t.search.allTime}</option>
            <option value="7">{t.search.sevenDays}</option>
            <option value="30">{t.search.thirtyDays}</option>
            <option value="90">{t.search.ninetyDays}</option>
          </select>
        </div>

        <div className="status-grid">
          <div className="status-card">
            <span>{t.search.total}</span>
            <b>{statsQ.data?.total ?? "..."}</b>
          </div>
          <div className="status-card">
            <span>{t.search.today}</span>
            <b>{statsQ.data?.today ?? "..."}</b>
          </div>
          <div className="status-card">
            <span>{t.search.native}</span>
            <b className={nativeQ.data?.enabled ? "ok" : "warn"}>{nativeQ.data?.enabled ? t.search.enabled : t.search.python}</b>
          </div>
        </div>

        <label className="toggle-row">
          <input type="checkbox" checked={starredOnly} onChange={(e) => setStarredOnly(e.target.checked)} />
          <span>{t.search.starredOnly}</span>
        </label>
      </div>

      <div className="results-wrap">
        {searchQ.isFetching ? <div className="state">{t.search.searching}</div> : null}
        {!searchQ.isFetching && debounced.trim().length > 0 && results.length === 0 ? (
          <div className="state">{t.search.empty}</div>
        ) : null}
        {!debounced.trim().length ? <div className="state">{t.search.idle}</div> : null}

        <div className="result-list">
          {results.map((item: FeedItem) => (
            <ResultCard
              key={item.id}
              item={item}
              onToggleStar={(row) => starMut.mutate({ id: row.id, starred: !row.starred })}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function isVideoItem(item: FeedItem): boolean {
  if ((item.content_type || "").toLowerCase() === "video") return true;
  const platform = (item.platform || "").toLowerCase();
  if (platform === "youtube" || platform === "tiktok") return true;
  return /\/video\/\d+/.test(item.url || "");
}

function toEpoch(value: string): number {
  const ts = Date.parse(value || "");
  return Number.isFinite(ts) ? ts : 0;
}
