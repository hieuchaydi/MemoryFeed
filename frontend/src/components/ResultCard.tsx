import { useMemo, useState } from "react";
import { ExternalLink, PlayCircle, X } from "lucide-react";

import { fromNow, prettyDate } from "../hooks/time";
import { useSettings } from "../settings";
import type { FeedItem } from "../types";
import PlatformBadge from "./PlatformBadge";

interface ResultCardProps {
  item: FeedItem;
  onToggleStar?: (item: FeedItem) => void;
}

export default function ResultCard({ item, onToggleStar }: ResultCardProps) {
  const [openPreview, setOpenPreview] = useState(false);
  const { language, t } = useSettings();
  const text = item.text_excerpt || item.text_content || `(${t.card.noText})`;
  const embedUrl = useMemo(() => getEmbedUrl(item.url, item.platform), [item.url, item.platform]);
  const canTryVideo = item.platform === "tiktok" || item.platform === "youtube";

  function handlePreview() {
    if (embedUrl) {
      setOpenPreview(true);
      return;
    }
    window.open(item.url, "_blank", "noopener,noreferrer");
  }

  return (
    <>
      <article className="result-card">
        {item.thumbnail ? (
          <img className="thumb" src={item.thumbnail} alt="" />
        ) : (
          <div className="thumb placeholder" aria-hidden="true" />
        )}
        <div className="content">
          <div className="meta-line">
            <PlatformBadge platform={item.platform} />
            <button
              type="button"
              className={`star-btn ${item.starred ? "on" : ""}`}
              onClick={() => onToggleStar?.(item)}
              title={item.starred ? t.card.unstar : t.card.star}
            >
              {item.starred ? "★" : "+"}
            </button>
            <span className="dot" />
            <span className="ts" title={prettyDate(item.captured_at)}>
              {fromNow(item.captured_at, language)}
            </span>
            {item.author ? (
              <>
                <span className="dot" />
                <span className="author">{item.author}</span>
              </>
            ) : null}
            <a href={item.url} target="_blank" rel="noreferrer" className="open-link" title={t.card.openOriginalTitle}>
              <ExternalLink size={14} className="ext" />
            </a>
          </div>
          <p>{text}</p>
          <div className="action-row inline-actions">
            {canTryVideo ? (
              <button type="button" className="action-btn preview-btn" onClick={handlePreview}>
                <PlayCircle size={14} />
                <span>{embedUrl ? t.card.quickVideo : t.card.openVideo}</span>
              </button>
            ) : null}
            <a href={item.url} target="_blank" rel="noreferrer" className="action-btn preview-btn link-btn">
              <ExternalLink size={14} />
              <span>{t.card.openOriginal}</span>
            </a>
          </div>
          {item.note ? <div className="note-inline">{t.card.note}: {item.note.slice(0, 120)}</div> : null}
          {typeof item.score === "number" ? <div className="score">{t.card.score}: {item.score.toFixed(6)}</div> : null}
        </div>
      </article>

      {openPreview && embedUrl ? (
        <div className="preview-overlay" onClick={() => setOpenPreview(false)}>
          <div className="preview-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="preview-head">
              <strong>{t.card.previewTitle}</strong>
              <button type="button" className="close-btn" onClick={() => setOpenPreview(false)} aria-label={t.card.close}>
                <X size={16} />
              </button>
            </div>
            <div className="preview-player-wrap">
              <iframe
                className="preview-player"
                src={embedUrl}
                title="MemoryFeed video preview"
                allow="autoplay; encrypted-media; picture-in-picture; web-share"
                referrerPolicy="strict-origin-when-cross-origin"
                allowFullScreen
              />
            </div>
            <div className="preview-foot">
              <a href={item.url} target="_blank" rel="noreferrer" className="action-btn preview-btn link-btn">
                <ExternalLink size={14} />
                <span>{t.card.openPlatform}</span>
              </a>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function getEmbedUrl(url: string, platform: string): string | null {
  if (!url) return null;
  if (platform === "youtube") {
    const id = getYouTubeId(url);
    return id ? `https://www.youtube.com/embed/${id}` : null;
  }
  if (platform === "tiktok") {
    const id = getTikTokVideoId(url);
    return id ? `https://www.tiktok.com/player/v1/${id}` : null;
  }
  return null;
}

function getYouTubeId(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtu.be")) {
      return u.pathname.replace("/", "") || null;
    }
    if (u.pathname.startsWith("/watch")) {
      return u.searchParams.get("v");
    }
    if (u.pathname.startsWith("/shorts/")) {
      return u.pathname.split("/")[2] || null;
    }
    if (u.pathname.startsWith("/embed/")) {
      return u.pathname.split("/")[2] || null;
    }
  } catch {
    return null;
  }
  return null;
}

function getTikTokVideoId(url: string): string | null {
  const m = url.match(/\/video\/(\d+)/);
  return m?.[1] || null;
}
