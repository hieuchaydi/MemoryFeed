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
  heat?: number | null;
  importance_score?: number | null;
  resurfacing_score?: number | null;
  recency_score?: number | null;
  recurrence_score?: number | null;
  last_surfaced?: string | null;
  surfaced_count?: number;
  archived_at?: string | null;
  archive_reason?: string | null;
  related_topics?: string[];
  related_entities?: string[];
  cluster_id?: string | null;
  semantic_group?: string | null;
  suspicious_prompt_content?: boolean;
  embedding_skipped_reason?: string | null;
  surface_score?: number | null;
  surface_reason?: string | null;
  needs_review?: boolean;
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

export interface ActiveFeedResponse {
  mode: string;
  count: number;
  items: FeedItem[];
}

export interface ResurfaceResponse {
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
