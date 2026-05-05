import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Language = "vi" | "en";
export type ThemeMode = "light" | "dark";

type SettingsContextValue = {
  language: Language;
  theme: ThemeMode;
  setLanguage: (language: Language) => void;
  setTheme: (theme: ThemeMode) => void;
  t: Copy;
};

type Copy = (typeof copy)[Language];

const copy = {
  vi: {
    app: {
      nav: {
        search: "Tìm kiếm",
        feed: "Active Feed",
        timeline: "Timeline",
        stats: "Hệ thống",
      },
      tagline: "Bộ nhớ cá nhân local-first, chủ động gợi lại đúng ngữ cảnh.",
      stack: "FastAPI + SQLite FTS5 + LanceDB + React",
      local: "Dữ liệu local. Truy hồi chủ động. Không telemetry.",
      theme: {
        label: "Giao diện",
        light: "Sáng",
        dark: "Tối",
      },
      language: {
        label: "Ngôn ngữ",
        vi: "VI",
        en: "EN",
      },
    },
    search: {
      title: "Bảng điều khiển",
      description: "Tìm bằng ngôn ngữ tự nhiên, kể cả khi bạn chỉ nhớ ý chính.",
      examples: "Ví dụ",
      placeholder: "Nhập truy vấn...",
      allTime: "Tất cả thời gian",
      sevenDays: "7 ngày",
      thirtyDays: "30 ngày",
      ninetyDays: "90 ngày",
      total: "Tổng capture",
      today: "Hôm nay",
      native: "Native accel",
      enabled: "bật",
      python: "python",
      starredOnly: "Chỉ hiện mục đã đánh dấu",
      searching: "Đang tìm...",
      empty: "Không tìm thấy kết quả.",
      idle: "Nhập từ khóa để bắt đầu.",
    },
    feed: {
      title: "Active Feed",
      description: "Feed xếp hạng theo heat, độ mới, khoảng trống resurfacing và ngữ cảnh hiện tại.",
      mode: "Chế độ",
      modes: {
        default: "Mặc định",
        focus: "Làm việc sâu",
        light: "Lướt nhẹ",
        explore: "Khám phá",
      },
      mark: "Đánh dấu đã surfaced",
      marking: "Đang ghi nhận...",
      contextPlaceholder: "Dán ngữ cảnh hiện tại: đoạn code, bài đang đọc, email đang viết...",
      resurface: "Resurface ngữ cảnh",
      resurfacing: "Đang resurface...",
      contextTitle: "Gợi ý theo ngữ cảnh",
      forYou: "Dành cho bạn",
      loading: "Đang tải active feed...",
      empty: "Chưa có memory để xếp hạng.",
      memory: "memory",
      heat: "heat",
      review: "cần xem lại/archive?",
      archive: "Archive",
    },
    timeline: {
      title: "Timeline",
      description: "Xem lại capture theo ngày và nền tảng.",
      loading: "Đang tải timeline...",
      empty: "Không có dữ liệu.",
    },
    stats: {
      title: "Hệ thống",
      description: "Theo dõi pipeline indexing, queue backlog và công cụ vận hành.",
      total: "Tổng capture",
      today: "Hôm nay",
      nativeEnabled: "Native enabled",
      nativeReason: "Native reason",
      indexerQueue: "Indexer queue",
      visionQueue: "Vision queue",
      indexerProcessed: "Indexer processed/failed",
      visionProcessed: "Vision processed/failed",
      export: "Export JSON",
      exporting: "Đang export...",
      reset: "Reset Data",
      resetting: "Đang reset...",
      resetConfirm: "Reset toàn bộ dữ liệu? Hành động này không thể hoàn tác.",
      exported: "Đã export",
      byPlatform: "Theo nền tảng",
      byType: "Theo loại",
    },
    card: {
      noText: "Không có nội dung text",
      unstar: "Bỏ đánh dấu",
      star: "Đánh dấu quan trọng",
      openOriginalTitle: "Mở nội dung gốc",
      quickVideo: "Xem nhanh video",
      openVideo: "Mở video gốc",
      openOriginal: "Mở bài gốc",
      previewTitle: "Xem nhanh video",
      close: "Đóng",
      openPlatform: "Mở trên nền tảng gốc",
      note: "Ghi chú",
      score: "score",
    },
  },
  en: {
    app: {
      nav: {
        search: "Search",
        feed: "Active Feed",
        timeline: "Timeline",
        stats: "System",
      },
      tagline: "A local-first personal memory layer that resurfaces context at the right time.",
      stack: "FastAPI + SQLite FTS5 + LanceDB + React",
      local: "Local data. Ambient retrieval. No telemetry.",
      theme: {
        label: "Theme",
        light: "Light",
        dark: "Dark",
      },
      language: {
        label: "Language",
        vi: "VI",
        en: "EN",
      },
    },
    search: {
      title: "Operator Console",
      description: "Search naturally, even when you only remember the idea.",
      examples: "Examples",
      placeholder: "Enter a query...",
      allTime: "All time",
      sevenDays: "7 days",
      thirtyDays: "30 days",
      ninetyDays: "90 days",
      total: "Total captures",
      today: "Today",
      native: "Native accel",
      enabled: "enabled",
      python: "python",
      starredOnly: "Only starred items",
      searching: "Searching...",
      empty: "No results found.",
      idle: "Enter a query to start.",
    },
    feed: {
      title: "Active Feed",
      description: "Ranked by heat, recency, resurfacing gap, and current context.",
      mode: "Mode",
      modes: {
        default: "Default",
        focus: "Deep work",
        light: "Light browse",
        explore: "Explore",
      },
      mark: "Mark as surfaced",
      marking: "Saving...",
      contextPlaceholder: "Paste current context: code, article, draft email...",
      resurface: "Resurface context",
      resurfacing: "Resurfacing...",
      contextTitle: "Context surfaced",
      forYou: "For you",
      loading: "Loading active feed...",
      empty: "No memories available to rank yet.",
      memory: "memory",
      heat: "heat",
      review: "review/archive?",
      archive: "Archive",
    },
    timeline: {
      title: "Timeline",
      description: "Review captures by date and platform.",
      loading: "Loading timeline...",
      empty: "No data.",
    },
    stats: {
      title: "System",
      description: "Monitor indexing, queue backlog, and operating tools.",
      total: "Total captures",
      today: "Today",
      nativeEnabled: "Native enabled",
      nativeReason: "Native reason",
      indexerQueue: "Indexer queue",
      visionQueue: "Vision queue",
      indexerProcessed: "Indexer processed/failed",
      visionProcessed: "Vision processed/failed",
      export: "Export JSON",
      exporting: "Exporting...",
      reset: "Reset Data",
      resetting: "Resetting...",
      resetConfirm: "Reset all data? This cannot be undone.",
      exported: "Exported",
      byPlatform: "By platform",
      byType: "By type",
    },
    card: {
      noText: "No text content",
      unstar: "Remove star",
      star: "Mark important",
      openOriginalTitle: "Open original content",
      quickVideo: "Quick video preview",
      openVideo: "Open original video",
      openOriginal: "Open original",
      previewTitle: "Quick video preview",
      close: "Close",
      openPlatform: "Open on original platform",
      note: "Note",
      score: "score",
    },
  },
} as const;

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => readStoredValue("memoryfeed-language", "vi"));
  const [theme, setThemeState] = useState<ThemeMode>(() => readStoredValue("memoryfeed-theme", "dark"));

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("memoryfeed-theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language === "vi" ? "vi" : "en";
    localStorage.setItem("memoryfeed-language", language);
  }, [language]);

  const value = useMemo<SettingsContextValue>(
    () => ({
      language,
      theme,
      setLanguage: setLanguageState,
      setTheme: setThemeState,
      t: copy[language],
    }),
    [language, theme]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettings must be used inside SettingsProvider");
  }
  return ctx;
}

function readStoredValue<T extends string>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key);
    return stored ? (stored as T) : fallback;
  } catch {
    return fallback;
  }
}
