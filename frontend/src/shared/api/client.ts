import type {
  AggregateBucketsResponse,
  AggregateCountParams,
  AggregateCountResponse,
  AggregateTopEventTypesParams,
  AggregateTopUrlsParams,
  AggregateUniqueUsersParams,
  AggregateUniqueUsersResponse,
  ApiErrorModel,
  AppSettings,
  EventDetailResponse,
  EventListResponse,
  EventsListParams,
  HealthLiveResponse,
  HealthReadyResponse,
  IngestBatchRequest,
  IngestBatchResponse,
  IngestEventRequest,
  IngestSingleResponse,
} from "../lib/types";

const REQUEST_ID_HEADER = "x-request-id";

type HttpMethod = "GET" | "POST";

export interface RequestRecorder {
  (entry: {
    method: HttpMethod;
    path: string;
    status: number;
    durationMs: number;
    requestId: string | null;
    errorMessage: string | null;
  }): void;
}

export interface ApiClientOptions {
  settings: AppSettings;
  onError?: (error: ApiErrorModel) => void;
  onRequestComplete?: RequestRecorder;
}

class ApiClient {
  private readonly options: ApiClientOptions;

  constructor(options: ApiClientOptions) {
    this.options = options;
  }

  async healthLive(): Promise<HealthLiveResponse> {
    return this.fetchJson<HealthLiveResponse>("GET", "/health/live");
  }

  async healthReady(): Promise<HealthReadyResponse> {
    return this.fetchJson<HealthReadyResponse>("GET", "/health/ready");
  }

  async ingestSingle(payload: IngestEventRequest): Promise<IngestSingleResponse> {
    return this.fetchJson<IngestSingleResponse>("POST", "/v1/ingest/events", { body: payload });
  }

  async ingestBatch(payload: IngestBatchRequest): Promise<IngestBatchResponse> {
    return this.fetchJson<IngestBatchResponse>("POST", "/v1/ingest/events:batch", { body: payload });
  }

  async listEvents(params: EventsListParams): Promise<EventListResponse> {
    return this.fetchJson<EventListResponse>("GET", "/v1/events", { params });
  }

  async getEventDetail(eventId: string): Promise<EventDetailResponse> {
    return this.fetchJson<EventDetailResponse>("GET", `/v1/events/${encodeURIComponent(eventId)}`);
  }

  async aggregateCount(params: AggregateCountParams): Promise<AggregateCountResponse> {
    return this.fetchJson<AggregateCountResponse>("GET", "/v1/aggregates/count", { params });
  }

  async aggregateTopEventTypes(
    params: AggregateTopEventTypesParams,
  ): Promise<AggregateBucketsResponse> {
    return this.fetchJson<AggregateBucketsResponse>("GET", "/v1/aggregates/top-event-types", {
      params,
    });
  }

  async aggregateTopUrls(params: AggregateTopUrlsParams): Promise<AggregateBucketsResponse> {
    return this.fetchJson<AggregateBucketsResponse>("GET", "/v1/aggregates/top-urls", {
      params,
    });
  }

  async aggregateUniqueUsers(
    params: AggregateUniqueUsersParams,
  ): Promise<AggregateUniqueUsersResponse> {
    return this.fetchJson<AggregateUniqueUsersResponse>("GET", "/v1/aggregates/unique-users", {
      params,
    });
  }

  private async fetchJson<T>(
    method: HttpMethod,
    path: string,
    options: { params?: object; body?: unknown } = {},
  ): Promise<T> {
    const startedAt = performance.now();
    const url = buildUrl(this.options.settings.apiBaseUrl, path, options.params);
    const headers: Record<string, string> = {
      Accept: "application/json",
    };

    if (this.options.settings.ingestKey) {
      headers["X-Ingest-Key"] = this.options.settings.ingestKey;
    }

    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers,
        body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      });
    } catch (error) {
      const durationMs = Math.round(performance.now() - startedAt);
      const apiError: ApiErrorModel = {
        status: 0,
        code: "network_error",
        message: error instanceof Error ? error.message : "Network request failed",
        requestId: null,
        detail: null,
      };
      this.options.onError?.(apiError);
      this.options.onRequestComplete?.({
        method,
        path,
        status: 0,
        durationMs,
        requestId: null,
        errorMessage: apiError.message,
      });
      throw apiError;
    }

    const requestId = response.headers.get(REQUEST_ID_HEADER);
    const durationMs = Math.round(performance.now() - startedAt);
    const responseContentType = response.headers.get("content-type") ?? "";
    const responseBody = responseContentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const apiError = normalizeApiError(response.status, requestId, responseBody);
      this.options.onError?.(apiError);
      this.options.onRequestComplete?.({
        method,
        path,
        status: response.status,
        durationMs,
        requestId,
        errorMessage: apiError.message,
      });
      throw apiError;
    }

    this.options.onRequestComplete?.({
      method,
      path,
      status: response.status,
      durationMs,
      requestId,
      errorMessage: null,
    });

    return responseBody as T;
  }
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  return new ApiClient(options);
}

function buildUrl(baseUrl: string, path: string, params?: object): string {
  const root = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  const url = new URL(`${root}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") {
        continue;
      }
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

function normalizeApiError(status: number, requestId: string | null, detail: unknown): ApiErrorModel {
  const fallback = {
    code: status >= 500 ? "internal_error" : "request_failed",
    message: typeof detail === "string" ? detail : `Request failed with status ${status}`,
  };

  if (isObject(detail) && "detail" in detail) {
    const nested = (detail as { detail: unknown }).detail;
    if (isObject(nested)) {
      const code = typeof nested.code === "string" ? nested.code : fallback.code;
      const message = typeof nested.message === "string" ? nested.message : fallback.message;
      return { status, code, message, requestId, detail };
    }
    if (typeof nested === "string") {
      return { status, code: fallback.code, message: nested, requestId, detail };
    }
  }

  return {
    status,
    code: fallback.code,
    message: fallback.message,
    requestId,
    detail,
  };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

