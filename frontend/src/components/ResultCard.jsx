import { ExternalLink } from "lucide-react";
import PlatformBadge from "./PlatformBadge";
import { fromNow, prettyDate } from "../hooks/time";

export default function ResultCard({ item }) {
  const text = item.text_excerpt || item.text_content || "(không có nội dung text)";
  return (
    <a className="result-card" href={item.url} target="_blank" rel="noreferrer">
      {item.thumbnail ? <img className="thumb" src={item.thumbnail} alt="thumbnail" /> : <div className="thumb placeholder" />}
      <div className="content">
        <div className="meta-line">
          <PlatformBadge platform={item.platform} />
          <span className="dot" />
          <span className="ts" title={prettyDate(item.captured_at)}>{fromNow(item.captured_at)}</span>
          {item.author ? <><span className="dot" /><span className="author">{item.author}</span></> : null}
          <ExternalLink size={14} className="ext" />
        </div>
        <p>{text}</p>
        <div className="score">score: {item.score?.toFixed ? item.score.toFixed(6) : item.score}</div>
      </div>
    </a>
  );
}
