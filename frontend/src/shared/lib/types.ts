export type DataSource = "rollup" | "direct_query";

export interface ApiErrorModel {
  status: number;
  code: string;
  message: string;
  requestId: string | null;
  detail: unknown;
}

export interface RequestSummary {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  status: number;
  durationMs: number;
  requestId: string | null;
  errorMessage: string | null;
}

export interface AppSettings {
  apiBaseUrl: string;
  ingestKey: string;
  environmentLabel: string;
}

export interface HealthLiveResponse {
  status: string;
}

export interface HealthReadyResponse {
  status: string;
  dependencies: Record<string, string>;
}

export interface IngestEventRequest {
  event_type: string;
  occurred_at: string;
  source?: string;
  user_id?: string;
  session_id?: string;
  severity?: string;
  url?: string;
  referrer?: string;
  schema_version?: string;
  idempotency_key?: string;
  attributes?: Record<string, unknown>;
}

export interface IngestedEventResult {
  event_id: string;
  status: "accepted" | "duplicate";
  duplicate_reason: "idempotency_key" | "dedupe_hash" | null;
}

export interface IngestSingleResponse {
  result: IngestedEventResult;
}

export interface IngestBatchRequest {
  batch_id?: string;
  events: IngestEventRequest[];
}

export interface IngestBatchResponse {
  total_count: number;
  accepted_count: number;
  duplicate_count: number;
  results: IngestedEventResult[];
}

export interface EventListItem {
  event_id: string;
  event_type: string;
  occurred_at: string;
  source: string;
  user_id: string | null;
  session_id: string | null;
  severity: string | null;
  url: string | null;
  referrer: string | null;
  received_at: string;
  ingest_status: string;
  geo_country: string | null;
  ua_browser: string | null;
  ua_os: string | null;
  ua_device: string | null;
  url_host: string | null;
  referrer_domain: string | null;
  is_bot: boolean;
}

export interface EventListResponse {
  count: number;
  has_more: boolean;
  next_cursor: string | null;
  items: EventListItem[];
}

export interface EventDetailResponse {
  item: EventListItem;
}

export interface AggregateCountResponse {
  value: number;
  data_source: DataSource;
}

export interface AggregateBucketItem {
  key: string;
  value: number;
}

export interface AggregateBucketsResponse {
  items: AggregateBucketItem[];
  data_source: DataSource;
}

export interface AggregateUniqueUsersResponse {
  value: number;
  data_source: "direct_query";
}

export interface EventsListParams {
  limit?: number;
  sort?: "asc" | "desc";
  cursor?: string;
  occurred_from?: string;
  occurred_to?: string;
  event_type?: string;
  severity?: string;
  source?: string;
  user_id?: string;
  session_id?: string;
  ingest_status?: string;
  geo_country?: string;
  is_bot?: boolean;
}

export interface AggregateCountParams {
  occurred_from?: string;
  occurred_to?: string;
  event_type?: string;
  severity?: string;
  source?: string;
  user_id?: string;
  session_id?: string;
  ingest_status?: string;
  geo_country?: string;
  is_bot?: boolean;
}

export interface AggregateTopEventTypesParams {
  limit?: number;
  occurred_from?: string;
  occurred_to?: string;
  source?: string;
  severity?: string;
  geo_country?: string;
  is_bot?: boolean;
}

export interface AggregateTopUrlsParams {
  limit?: number;
  occurred_from?: string;
  occurred_to?: string;
  event_type?: string;
  source?: string;
  severity?: string;
  geo_country?: string;
  is_bot?: boolean;
}

export interface AggregateUniqueUsersParams {
  occurred_from?: string;
  occurred_to?: string;
  event_type?: string;
  source?: string;
  severity?: string;
  geo_country?: string;
  is_bot?: boolean;
}

