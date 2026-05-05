import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchTimeline } from "../api/client";
import ResultCard from "../components/ResultCard";
import { todayISO } from "../hooks/time";
import { useSettings } from "../settings";
import type { FeedItem } from "../types";

const PLATFORMS = ["all", "facebook", "twitter", "youtube", "linkedin", "instagram", "unknown"];

export default function TimelinePage() {
  const { t } = useSettings();
  const [date, setDate] = useState(todayISO());
  const [platform, setPlatform] = useState("all");

  const timelineQ = useQuery({
    queryKey: ["timeline", date, platform],
    queryFn: () => fetchTimeline({ date, platform }),
  });

  const groups = useMemo(() => {
    const items = timelineQ.data?.items || [];
    const out = new Map<string, FeedItem[]>();
    for (const item of items) {
      const hh = (item.captured_at || "").slice(11, 13) || "??";
      const key = `${hh}:00`;
      if (!out.has(key)) out.set(key, []);
      out.get(key)?.push(item);
    }
    return Array.from(out.entries()).sort((a, b) => (a[0] < b[0] ? 1 : -1));
  }, [timelineQ.data]);

  return (
    <section className="page">
      <div className="hero-panel compact">
        <h1>{t.timeline.title}</h1>
        <p>{t.timeline.description}</p>
        <div className="query-grid">
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="query-input" />
          <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="days-select">
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
      </div>

      {timelineQ.isFetching ? <div className="state">{t.timeline.loading}</div> : null}
      {!timelineQ.isFetching && groups.length === 0 ? <div className="state">{t.timeline.empty}</div> : null}

      <div className="timeline-groups">
        {groups.map(([hour, items]) => (
          <div key={hour} className="timeline-group">
            <h2>{hour}</h2>
            <div className="result-list">
              {items.map((item) => (
                <ResultCard key={item.id} item={item} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
