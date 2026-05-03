export interface FeedItem {
  id: string;
  url: string;
  platform: string;
  captured_at: string;
  text_content?: string | null;
  text_excerpt?: string | null;
  thumbnail?: string | null;
  author?: string | null;
  score?: number | null;
  starred?: boolean;
  note?: string | null;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: FeedItem[];
}

export interface TimelineResponse {
  date: string;
  platform?: string | null;
  count: number;
  items: FeedItem[];
}

export interface StatRow {
  key: string;
  count: number;
}

export interface NativeStatusResponse {
  enabled: boolean;
  reason: string;
}

export interface QueueState {
  running: boolean;
  queue_size: number;
  processed: number;
  failed: number;
}

export interface QueueStatusResponse {
  indexer: QueueState;
  vision: QueueState;
}

export interface StatsResponse {
  total: number;
  today: number;
  by_platform: StatRow[];
  by_type: StatRow[];
  queues?: QueueStatusResponse;
}

export interface ItemsResponse {
  count: number;
  items: FeedItem[];
}

export interface ExportResponse {
  ok: boolean;
  file: string;
  count: number;
}

export interface ResetResponse {
  ok: boolean;
}

