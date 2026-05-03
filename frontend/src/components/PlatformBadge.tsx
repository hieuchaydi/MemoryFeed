import clsx from "clsx";

const MAP: Record<string, { emoji: string; tone: string }> = {
  twitter: { emoji: "🐦", tone: "tw" },
  facebook: { emoji: "👥", tone: "fb" },
  youtube: { emoji: "📺", tone: "yt" },
  linkedin: { emoji: "💼", tone: "li" },
  instagram: { emoji: "📸", tone: "ig" },
  unknown: { emoji: "🧠", tone: "uk" },
};

interface PlatformBadgeProps {
  platform: string;
}

export default function PlatformBadge({ platform }: PlatformBadgeProps) {
  const normalized = platform || "unknown";
  const config = MAP[normalized] || MAP.unknown;
  return (
    <span className={clsx("platform-badge", `tone-${config.tone}`)}>
      <span>{config.emoji}</span>
      <span>{normalized}</span>
    </span>
  );
}
