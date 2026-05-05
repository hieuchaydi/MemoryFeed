import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { exportData, fetchNativeStatus, fetchQueues, fetchStats, resetData } from "../api/client";
import { useSettings } from "../settings";

export default function StatsPage() {
  const { t } = useSettings();
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
        <h1>{t.stats.title}</h1>
        <p>{t.stats.description}</p>
      </div>

      <div className="status-grid large">
        <div className="status-card">
          <span>{t.stats.total}</span>
          <b>{statsQ.data?.total ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>{t.stats.today}</span>
          <b>{statsQ.data?.today ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>{t.stats.nativeEnabled}</span>
          <b>{String(nativeQ.data?.enabled ?? "...")}</b>
        </div>
        <div className="status-card">
          <span>{t.stats.nativeReason}</span>
          <b>{nativeQ.data?.reason ?? "..."}</b>
        </div>
      </div>

      <div className="status-grid large">
        <div className="status-card">
          <span>{t.stats.indexerQueue}</span>
          <b>{queueQ.data?.indexer?.queue_size ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>{t.stats.visionQueue}</span>
          <b>{queueQ.data?.vision?.queue_size ?? "..."}</b>
        </div>
        <div className="status-card">
          <span>{t.stats.indexerProcessed}</span>
          <b>{queueQ.data ? `${queueQ.data.indexer.processed}/${queueQ.data.indexer.failed}` : "..."}</b>
        </div>
        <div className="status-card">
          <span>{t.stats.visionProcessed}</span>
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
          {exportMut.isPending ? t.stats.exporting : t.stats.export}
        </button>
        <button
          type="button"
          className="action-btn danger"
          onClick={() => {
            if (window.confirm(t.stats.resetConfirm)) {
              resetMut.mutate();
            }
          }}
          disabled={resetMut.isPending}
        >
          {resetMut.isPending ? t.stats.resetting : t.stats.reset}
        </button>
      </div>

      {exportMut.data?.file ? <div className="state">{t.stats.exported}: {exportMut.data.file}</div> : null}

      <div className="stats-grid">
        <div className="stats-box">
          <h2>{t.stats.byPlatform}</h2>
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
          <h2>{t.stats.byType}</h2>
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
