import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { archiveFeedItems, fetchActiveFeed, markFeedSurfaced, resurfaceContext } from "../api/client";
import ResultCard from "../components/ResultCard";
import { useSettings } from "../settings";
import type { FeedItem } from "../types";

const MODES = [
  "default",
  "focus",
  "light",
  "explore",
] as const;

const REASON_LABELS: Record<string, { vi: string; en: string }> = {
  hot_memory: { vi: "Memory đang nóng", en: "Hot memory" },
  review_or_archive: { vi: "Cần xem lại", en: "Review needed" },
  worth_resurfacing: { vi: "Đáng gợi lại", en: "Worth resurfacing" },
  starred_memory: { vi: "Đã đánh dấu", en: "Starred" },
  recent_capture: { vi: "Mới capture", en: "Recent capture" },
  related_to_current_context: { vi: "Liên quan ngữ cảnh", en: "Related to context" },
  memory: { vi: "Memory", en: "Memory" },
};

type Mode = (typeof MODES)[number];

const MODE_LABEL_KEYS: Record<Mode, keyof ReturnType<typeof useSettings>["t"]["feed"]["modes"]> = {
  default: "default",
  focus: "focus",
  light: "light",
  explore: "explore",
};

export default function FeedPage() {
  const { language, t } = useSettings();
  const [mode, setMode] = useState<Mode>("default");
  const [context, setContext] = useState("");
  const qc = useQueryClient();

  const feedQ = useQuery({
    queryKey: ["active-feed", mode],
    queryFn: () => fetchActiveFeed({ limit: 24, mode }),
  });

  const resurfaceMut = useMutation({
    mutationFn: () => resurfaceContext({ context, limit: 6, bump_heat: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["active-feed"] }),
  });

  const surfacedMut = useMutation({
    mutationFn: (ids: string[]) => markFeedSurfaced(ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["active-feed"] }),
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => archiveFeedItems([id]),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["active-feed"] }),
  });

  const feedItems = feedQ.data?.items || [];
  const resurfacedItems = resurfaceMut.data?.items || [];
  const visibleIds = useMemo(() => feedItems.map((item) => item.id), [feedItems]);

  return (
    <section className="page">
      <div className="hero-panel">
        <h1>{t.feed.title}</h1>
        <p>{t.feed.description}</p>

        <div className="query-grid">
          <select value={mode} onChange={(e) => setMode(e.target.value as Mode)} className="days-select" aria-label={t.feed.mode}>
            {MODES.map((m) => (
              <option key={m} value={m}>
                {t.feed.modes[MODE_LABEL_KEYS[m]]}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="action-btn"
            disabled={!visibleIds.length || surfacedMut.isPending}
            onClick={() => surfacedMut.mutate(visibleIds)}
          >
            {surfacedMut.isPending ? t.feed.marking : t.feed.mark}
          </button>
        </div>

        <div className="query-grid">
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder={t.feed.contextPlaceholder}
            className="query-input"
            rows={4}
          />
          <button
            type="button"
            className="action-btn"
            disabled={context.trim().length < 3 || resurfaceMut.isPending}
            onClick={() => resurfaceMut.mutate()}
          >
            {resurfaceMut.isPending ? t.feed.resurfacing : t.feed.resurface}
          </button>
        </div>
      </div>

      {resurfacedItems.length ? (
        <FeedSection
          title={t.feed.contextTitle}
          items={resurfacedItems}
          language={language}
          labels={t.feed}
          onArchive={(id) => archiveMut.mutate(id)}
        />
      ) : null}

      {feedQ.isFetching ? <div className="state">{t.feed.loading}</div> : null}
      {!feedQ.isFetching && feedItems.length === 0 ? <div className="state">{t.feed.empty}</div> : null}

      <FeedSection
        title={t.feed.forYou}
        items={feedItems}
        language={language}
        labels={t.feed}
        onArchive={(id) => archiveMut.mutate(id)}
      />
    </section>
  );
}

function FeedSection({
  title,
  items,
  language,
  labels,
  onArchive,
}: {
  title: string;
  items: FeedItem[];
  language: "vi" | "en";
  labels: ReturnType<typeof useSettings>["t"]["feed"];
  onArchive: (id: string) => void;
}) {
  if (!items.length) return null;

  return (
    <div className="timeline-group">
      <h2>{title}</h2>
      <div className="result-list">
        {items.map((item) => (
          <div key={`${title}-${item.id}`}>
            <div className="feed-meta-card">
              <span>
                {reasonLabel(item.surface_reason, language)} · {labels.heat}{" "}
                {typeof item.heat === "number" ? item.heat.toFixed(2) : "1.00"}
                {item.needs_review ? ` · ${labels.review}` : ""}
              </span>
              {item.needs_review ? (
                <button type="button" className="action-btn danger" onClick={() => onArchive(item.id)}>
                  {labels.archive}
                </button>
              ) : null}
            </div>
            <ResultCard item={item} />
          </div>
        ))}
      </div>
    </div>
  );
}

function reasonLabel(reason: string | null | undefined, language: "vi" | "en") {
  const key = reason || "memory";
  return REASON_LABELS[key]?.[language] || key.replace(/_/g, " ");
}
