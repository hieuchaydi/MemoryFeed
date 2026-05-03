import { useQuery } from "@tanstack/react-query";
import { fetchNativeStatus, fetchStats } from "../api/client";

export default function StatsPage() {
  const statsQ = useQuery({ queryKey: ["stats"], queryFn: fetchStats });
  const nativeQ = useQuery({ queryKey: ["native"], queryFn: fetchNativeStatus });

  return (
    <section className="page">
      <div className="hero-panel compact">
        <h1>System Stats</h1>
        <p>Quan sát sức khỏe indexing pipeline và native acceleration.</p>
      </div>

      <div className="status-grid large">
        <div className="status-card"><span>Total captures</span><b>{statsQ.data?.total ?? "..."}</b></div>
        <div className="status-card"><span>Today</span><b>{statsQ.data?.today ?? "..."}</b></div>
        <div className="status-card"><span>Native enabled</span><b>{String(nativeQ.data?.enabled ?? "...")}</b></div>
        <div className="status-card"><span>Native reason</span><b>{nativeQ.data?.reason ?? "..."}</b></div>
      </div>

      <div className="stats-grid">
        <div className="stats-box">
          <h2>By platform</h2>
          <ul>
            {(statsQ.data?.by_platform || []).map((row) => <li key={row.key}><span>{row.key}</span><b>{row.count}</b></li>)}
          </ul>
        </div>
        <div className="stats-box">
          <h2>By type</h2>
          <ul>
            {(statsQ.data?.by_type || []).map((row) => <li key={row.key}><span>{row.key}</span><b>{row.count}</b></li>)}
          </ul>
        </div>
      </div>
    </section>
  );
}
