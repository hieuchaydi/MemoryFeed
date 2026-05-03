import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

export function fromNow(value) {
  if (!value) return "";
  return dayjs(value).fromNow();
}

export function prettyDate(value) {
  if (!value) return "";
  return dayjs(value).format("YYYY-MM-DD HH:mm");
}

export function todayISO() {
  return dayjs().format("YYYY-MM-DD");
}
