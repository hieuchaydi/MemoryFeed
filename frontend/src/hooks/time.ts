import dayjs from "dayjs";
import "dayjs/locale/vi";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

export function fromNow(value?: string | null, language: "vi" | "en" = "en"): string {
  if (!value) return "";
  return dayjs(value).locale(language === "vi" ? "vi" : "en").fromNow();
}

export function prettyDate(value?: string | null): string {
  if (!value) return "";
  return dayjs(value).format("YYYY-MM-DD HH:mm");
}

export function todayISO(): string {
  return dayjs().format("YYYY-MM-DD");
}
