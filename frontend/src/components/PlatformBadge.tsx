import clsx from "clsx";

const MAP: Record<string, { label: string; tone: string }> = {
  twitter: { label: "X", tone: "tw" },
  facebook: { label: "FB", tone: "fb" },
  youtube: { label: "YT", tone: "yt" },
  linkedin: { label: "IN", tone: "li" },
  instagram: { label: "IG", tone: "ig" },
  tiktok: { label: "TT", tone: "tt" },
  unknown: { label: "MF", tone: "uk" },
};

interface PlatformBadgeProps {
  platform: string;
}

export default function PlatformBadge({ platform }: PlatformBadgeProps) {
  const normalized = platform || "unknown";
  const config = MAP[normalized] || MAP.unknown;
  return (
    <span className={clsx("platform-badge", `tone-${config.tone}`)} title={normalized}>
      <span className="platform-mark">{config.label}</span>
      <span>{normalized}</span>
    </span>
  );
}
