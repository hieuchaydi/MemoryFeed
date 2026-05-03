import clsx from "clsx";

const MAP = {
  twitter: { emoji: "🐦", tone: "tw" },
  facebook: { emoji: "👥", tone: "fb" },
  youtube: { emoji: "📺", tone: "yt" },
  linkedin: { emoji: "💼", tone: "li" },
  instagram: { emoji: "📸", tone: "ig" },
  unknown: { emoji: "🧠", tone: "uk" },
};

export default function PlatformBadge({ platform }) {
  const config = MAP[platform] || MAP.unknown;
  return (
    <span className={clsx("platform-badge", `tone-${config.tone}`)}>
      <span>{config.emoji}</span>
      <span>{platform}</span>
    </span>
  );
}
