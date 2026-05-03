import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchNativeStatus, fetchStats, searchFeed } from "../api/client";
import ResultCard from "../components/ResultCard";

function useDebounced(value, ms = 280) {
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
  const debounced = useDebounced(query, 300);

  const searchQ = useQuery({
    queryKey: ["search", debounced, daysBack],
    queryFn: () => searchFeed(debounced, { limit: 24, daysBack: Number(daysBack) || undefined }),
    enabled: debounced.trim().length > 0,
  });

  const statsQ = useQuery({ queryKey: ["stats"], queryFn: fetchStats });
  const nativeQ = useQuery({ queryKey: ["native"], queryFn: fetchNativeStatus, staleTime: 30_000 });

  const results = searchQ.data?.results || [];

  return (
    <section className="page">
      <div className="hero-panel">
        <h1>MemoryFeed Console</h1>
        <p>Truy vấn tự nhiên: <code>meme mèo giận tuần trước</code> hoặc <code>startup culture failure</code>.</p>

        <div className="query-grid">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Nhập câu truy vấn..."
            className="query-input"
          />
          <select value={daysBack} onChange={(e) => setDaysBack(e.target.value)} className="days-select">
            <option value="">Tất cả thời gian</option>
            <option value="7">7 ngày</option>
            <option value="30">30 ngày</option>
            <option value="90">90 ngày</option>
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
      </div>

      <div className="results-wrap">
        {searchQ.isFetching ? <div className="state">Đang tìm...</div> : null}
        {!searchQ.isFetching && debounced.trim().length > 0 && results.length === 0 ? (
          <div className="state">Không tìm thấy kết quả.</div>
        ) : null}
        {!debounced.trim().length ? <div className="state">Nhập từ khóa để bắt đầu.</div> : null}

        <div className="result-list">
          {results.map((item) => (
            <ResultCard key={item.id} item={item} />
          ))}
        </div>
      </div>
    </section>
  );
}

