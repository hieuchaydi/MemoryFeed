import { ExternalLink } from "lucide-react";
import PlatformBadge from "./PlatformBadge";
import { fromNow, prettyDate } from "../hooks/time";

export default function ResultCard({ item, onToggleStar }) {
  const text = item.text_excerpt || item.text_content || "(khong co noi dung text)";
  return (
    <article className="result-card">
      {item.thumbnail ? <img className="thumb" src={item.thumbnail} alt="thumbnail" /> : <div className="thumb placeholder" />}
      <div className="content">
        <div className="meta-line">
          <PlatformBadge platform={item.platform} />
          <button
            type="button"
            className={`star-btn ${item.starred ? "on" : ""}`}
            onClick={() => onToggleStar?.(item)}
            title={item.starred ? "Bo danh dau" : "Danh dau quan trong"}
          >
            {item.starred ? "★" : "☆"}
          </button>
          <span className="dot" />
          <span className="ts" title={prettyDate(item.captured_at)}>
            {fromNow(item.captured_at)}
          </span>
          {item.author ? (
            <>
              <span className="dot" />
              <span className="author">{item.author}</span>
            </>
          ) : null}
          <a href={item.url} target="_blank" rel="noreferrer" className="open-link" title="Mo noi dung goc">
            <ExternalLink size={14} className="ext" />
          </a>
        </div>
        <p>{text}</p>
        {item.note ? <div className="note-inline">Note: {item.note.slice(0, 120)}</div> : null}
        <div className="score">score: {item.score?.toFixed ? item.score.toFixed(6) : item.score}</div>
      </div>
    </article>
  );
}
