import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchNativeStatus, fetchStats, patchItem, searchFeed } from "../api/client";
import ResultCard from "../components/ResultCard";
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
  const results = starredOnly ? rawResults.filter((x) => x.starred) : rawResults;

  return (
    <section className="page">
      <div className="hero-panel">
        <h1>MemoryFeed Console</h1>
        <p>
          Truy van tu nhien: <code>meme meo gian tuan truoc</code> hoac <code>startup culture failure</code>.
        </p>

        <div className="query-grid">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Nhap cau truy van..."
            className="query-input"
          />
          <select value={daysBack} onChange={(e) => setDaysBack(e.target.value)} className="days-select">
            <option value="">Tat ca thoi gian</option>
            <option value="7">7 ngay</option>
            <option value="30">30 ngay</option>
            <option value="90">90 ngay</option>
          </select>
        </div>

        <div className="status-grid">
          <div className="status-card">
            <span>Total captures</span>
            <b>{statsQ.data?.total ?? "..."}</b>
          </div>
          <div className="status-card">
            <span>Today</span>
            <b>{statsQ.data?.today ?? "..."}</b>
          </div>
          <div className="status-card">
            <span>Native accel</span>
            <b className={nativeQ.data?.enabled ? "ok" : "warn"}>{nativeQ.data?.enabled ? "enabled" : "python"}</b>
          </div>
        </div>

        <label className="toggle-row">
          <input type="checkbox" checked={starredOnly} onChange={(e) => setStarredOnly(e.target.checked)} />
          <span>Chi hien thi muc da danh dau sao</span>
        </label>
      </div>

      <div className="results-wrap">
        {searchQ.isFetching ? <div className="state">Dang tim...</div> : null}
        {!searchQ.isFetching && debounced.trim().length > 0 && results.length === 0 ? (
          <div className="state">Khong tim thay ket qua.</div>
        ) : null}
        {!debounced.trim().length ? <div className="state">Nhap tu khoa de bat dau.</div> : null}

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
