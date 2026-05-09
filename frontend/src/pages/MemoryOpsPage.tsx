import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

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
  const [timelineCursor, setTimelineCursor] = useState(40);

  const heatRows = useMemo(() => (heatmapQ.data?.cells || []).slice(0, 80), [heatmapQ.data]);
  const graphNodes = graphQ.data?.nodes || [];
  const graphEdges = graphQ.data?.edges || [];
  const agingRows = agingQ.data?.items || [];
  const events = timelineQ.data?.events || [];
  const visibleEvents = events.slice(0, Math.max(5, Math.min(events.length, timelineCursor)));
  const relatedMemories = useMemo(() => {
    const m = new Map<string, { in: number; out: number }>();
    for (const edge of graphEdges) {
      const from = String(edge.from || "");
      const to = String(edge.to || "");
      m.set(from, { in: m.get(from)?.in || 0, out: (m.get(from)?.out || 0) + 1 });
      m.set(to, { in: (m.get(to)?.in || 0) + 1, out: m.get(to)?.out || 0 });
    }
    return [...m.entries()]
      .map(([id, v]) => ({ id, degree: v.in + v.out, incoming: v.in, outgoing: v.out }))
      .sort((a, b) => b.degree - a.degree)
      .slice(0, 20);
  }, [graphEdges]);

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
          <h2>Activity Heatmap</h2>
          <div className="ops-heatmap">
            {heatRows.map((row: any, idx: number) => (
              <div
                key={`${row.day}-${row.state}-${idx}`}
                className="ops-heatmap-cell"
                title={`${row.day} ${row.state} (${row.count})`}
                style={{ opacity: Math.max(0.18, Math.min(1, Number(row.count || 0) / 12)) }}
              >
                <small>{row.day?.slice(5) || "??"}</small>
                <b>{row.count}</b>
                <span>{row.state}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="stats-box">
          <h2>Memory Aging Curve</h2>
          <svg viewBox="0 0 520 180" className="ops-curve" role="img" aria-label="Memory aging curve">
            <polyline
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              points={agingRows
                .slice(0, 40)
                .map((row: any, idx: number) => `${8 + idx * 12},${170 - Math.round((Number(row.decay_score || 0) * 155))}`)
                .join(" ")}
            />
          </svg>
          <ul>
            {agingRows.slice(0, 8).map((row: any) => (
              <li key={row.memory_id}><span>{row.memory_id.slice(0, 16)}...</span><b>{row.next_action}</b></li>
            ))}
          </ul>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stats-box">
          <h2>Reinforcement Graph</h2>
          <p>nodes: {graphNodes.length}, edges: {graphEdges.length}</p>
          <ul>
            {relatedMemories.map((row) => (
              <li key={row.id}>
                <span>{row.id.slice(0, 20)}...</span>
                <b>deg {row.degree} (in:{row.incoming} out:{row.outgoing})</b>
              </li>
            ))}
          </ul>
        </div>
        <div className="stats-box">
          <h2>Timeline Scrubber</h2>
          <input
            className="ops-scrubber"
            type="range"
            min={5}
            max={Math.max(5, events.length || 5)}
            value={Math.min(timelineCursor, Math.max(5, events.length || 5))}
            onChange={(e) => setTimelineCursor(Number(e.target.value))}
          />
          <p>visible events: {visibleEvents.length}/{events.length}</p>
          <ul>
            {visibleEvents.slice(0, 12).map((event: any) => (
              <li key={event.event_id}>
                <span>{event.event_type}</span>
                <b>{String(event.memory_id || "").slice(0, 16)}...</b>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
