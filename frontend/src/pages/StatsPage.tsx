import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { exportData, fetchNativeStatus, fetchQueues, fetchStats, resetData } from "../api/client";

export default function StatsPage() {
  const qc = useQueryClient();
  const statsQ = useQuery({ queryKey: ["stats"], queryFn: fetchStats, refetchInterval: 3000 });
  const nativeQ = useQuery({ queryKey: ["native"], queryFn: fetchNativeStatus, refetchInterval: 10_000 });
  const queueQ = useQuery({ queryKey: ["queues"], queryFn: fetchQueues, refetchInterval: 3000 });

  const exportMut = useMutation({ mutationFn: exportData });
  const resetMut = useMutation({
    mutationFn: resetData,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["search"] });
      qc.invalidateQueries({ queryKey: ["timeline"] });
    },
  });

  return (
    <section className="page">
      <div className="hero-panel compact">
        <h1>System Stats</h1>
        <p>Quan sat suc khoe pipeline indexing, queue backlog va cong cu van hanh.</p>
      </div>

      <div className="status-grid large">
        <div className="status-card">
          <span>Total captures</span>
          <b>{statsQ.data?.total ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>Today</span>
          <b>{statsQ.data?.today ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>Native enabled</span>
          <b>{String(nativeQ.data?.enabled ?? "...")}</b>
        </div>
        <div className="status-card">
          <span>Native reason</span>
          <b>{nativeQ.data?.reason ?? "..."}</b>
        </div>
      </div>

      <div className="status-grid large">
        <div className="status-card">
          <span>Indexer queue</span>
          <b>{queueQ.data?.indexer?.queue_size ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>Vision queue</span>
          <b>{queueQ.data?.vision?.queue_size ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>Indexer processed/failed</span>
          <b>{queueQ.data ? `${queueQ.data.indexer.processed}/${queueQ.data.indexer.failed}` : "..."}</b>
        </div>
        <div className="status-card">
          <span>Vision processed/failed</span>
          <b>{queueQ.data ? `${queueQ.data.vision.processed}/${queueQ.data.vision.failed}` : "..."}</b>
        </div>
      </div>

      <div className="action-row">
        <button
          type="button"
          className="action-btn"
          onClick={() => exportMut.mutate()}
          disabled={exportMut.isPending}
        >
          {exportMut.isPending ? "Dang export..." : "Export JSON"}
        </button>
        <button
          type="button"
          className="action-btn danger"
          onClick={() => {
            if (window.confirm("Reset toan bo du lieu? Hanh dong nay khong the hoan tac.")) {
              resetMut.mutate();
            }
          }}
          disabled={resetMut.isPending}
        >
          {resetMut.isPending ? "Dang reset..." : "Reset Data"}
        </button>
      </div>

      {exportMut.data?.file ? <div className="state">Da export: {exportMut.data.file}</div> : null}

      <div className="stats-grid">
        <div className="stats-box">
          <h2>By platform</h2>
          <ul>
            {(statsQ.data?.by_platform || []).map((row) => (
              <li key={row.key}>
                <span>{row.key}</span>
                <b>{row.count}</b>
              </li>
            ))}
          </ul>
        </div>
        <div className="stats-box">
          <h2>By type</h2>
          <ul>
            {(statsQ.data?.by_type || []).map((row) => (
              <li key={row.key}>
                <span>{row.key}</span>
                <b>{row.count}</b>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
