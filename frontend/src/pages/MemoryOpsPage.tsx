import { useQuery } from "@tanstack/react-query";

import {
  fetchMemoryAging,
  fetchMemoryHeatmap,
  fetchMemoryLifecycleTimeline,
  fetchMemoryReinforcementGraph,
  fetchPerf,
  fetchReady,
} from "../api/client";

export default function MemoryOpsPage() {
  const heatmapQ = useQuery({ queryKey: ["ops", "heatmap"], queryFn: fetchMemoryHeatmap, refetchInterval: 10000 });
  const graphQ = useQuery({ queryKey: ["ops", "graph"], queryFn: fetchMemoryReinforcementGraph, refetchInterval: 10000 });
  const agingQ = useQuery({ queryKey: ["ops", "aging"], queryFn: fetchMemoryAging, refetchInterval: 10000 });
  const timelineQ = useQuery({ queryKey: ["ops", "timeline"], queryFn: fetchMemoryLifecycleTimeline, refetchInterval: 10000 });
  const readyQ = useQuery({ queryKey: ["ops", "ready"], queryFn: fetchReady, refetchInterval: 5000 });
  const perfQ = useQuery({ queryKey: ["ops", "perf"], queryFn: fetchPerf, refetchInterval: 5000 });

  return (
    <section className="page">
      <div className="hero-panel compact">
        <h1>Memory Ops</h1>
        <p>Operational view for lifecycle, queues, reinforcement graph, and memory aging.</p>
      </div>

      <div className="status-grid large">
        <div className="status-card"><span>Ready</span><b>{String(readyQ.data?.ready ?? "...")}</b></div>
        <div className="status-card"><span>Indexer Queue</span><b>{readyQ.data?.queues?.indexer?.queue_size ?? "..."}</b></div>
        <div className="status-card"><span>Vision Queue</span><b>{readyQ.data?.queues?.vision?.queue_size ?? "..."}</b></div>
        <div className="status-card"><span>Dead Letters</span><b>{Array.isArray(perfQ.data?.dead_letters) ? perfQ.data.dead_letters.length : "..."}</b></div>
      </div>

      <div className="stats-grid">
        <div className="stats-box">
          <h2>Heatmap Cells</h2>
          <ul>
            {(heatmapQ.data?.cells || []).slice(0, 12).map((row: any, idx: number) => (
              <li key={idx}><span>{row.day} / {row.state}</span><b>{row.count}</b></li>
            ))}
          </ul>
        </div>
        <div className="stats-box">
          <h2>Aging</h2>
          <ul>
            {(agingQ.data?.items || []).slice(0, 12).map((row: any) => (
              <li key={row.memory_id}><span>{row.memory_id.slice(0, 16)}...</span><b>{row.next_action}</b></li>
            ))}
          </ul>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stats-box">
          <h2>Reinforcement Graph</h2>
          <p>nodes: {graphQ.data?.nodes?.length ?? 0}, edges: {graphQ.data?.edges?.length ?? 0}</p>
          <pre style={{ whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto" }}>{JSON.stringify((graphQ.data?.edges || []).slice(0, 6), null, 2)}</pre>
        </div>
        <div className="stats-box">
          <h2>Lifecycle Events</h2>
          <pre style={{ whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto" }}>{JSON.stringify((timelineQ.data?.events || []).slice(0, 10), null, 2)}</pre>
        </div>
      </div>
    </section>
  );
}
