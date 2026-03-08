import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";

import { useAppContext } from "../../shared/lib/app-context";
import { queryClient } from "../../shared/lib/query-client";
import { asApiError } from "../../shared/lib/errors";
import type {
  IngestBatchResponse,
  IngestEventRequest,
  IngestSingleResponse,
} from "../../shared/lib/types";
import { Panel } from "../../shared/ui/Panel";
import { ErrorState, LoadingState } from "../../shared/ui/StatusState";

const singleEventSchema = z.object({
  event_type: z.string().trim().min(1).max(255),
  occurred_at: z.string().trim().min(1),
  source: z.string().trim().max(128).optional(),
  user_id: z.string().trim().max(255).optional(),
  session_id: z.string().trim().max(255).optional(),
  severity: z.string().trim().max(32).optional(),
  url: z.string().trim().optional(),
  referrer: z.string().trim().optional(),
  schema_version: z.string().trim().max(32).optional(),
  idempotency_key: z.string().trim().max(255).optional(),
  attributes: z.string().trim().optional(),
});

const batchSchema = z.object({
  batch_id: z.string().trim().max(128).optional(),
  events_json: z.string().trim().min(1),
});

const batchEventSchema = z.object({
  event_type: z.string().trim().min(1).max(255),
  occurred_at: z.string().trim().min(1),
  source: z.string().trim().max(128).optional(),
  user_id: z.string().trim().max(255).optional(),
  session_id: z.string().trim().max(255).optional(),
  severity: z.string().trim().max(32).optional(),
  url: z.string().trim().optional(),
  referrer: z.string().trim().optional(),
  schema_version: z.string().trim().max(32).optional(),
  idempotency_key: z.string().trim().max(255).optional(),
  attributes: z.record(z.unknown()).optional(),
});

export function IngestionPage() {
  const { apiClient } = useAppContext();
  const [mode, setMode] = useState<"single" | "batch">("single");

  const [singleForm, setSingleForm] = useState({
    event_type: "page_view",
    occurred_at: new Date().toISOString(),
    source: "frontend",
    user_id: "",
    session_id: "",
    severity: "",
    url: "",
    referrer: "",
    schema_version: "",
    idempotency_key: "",
    attributes: '{"path":"/home"}',
  });

  const [batchForm, setBatchForm] = useState({
    batch_id: "",
    events_json: JSON.stringify(
      [
        {
          event_type: "page_view",
          occurred_at: new Date().toISOString(),
          source: "frontend",
          user_id: "u-1",
          attributes: { path: "/home" },
        },
      ],
      null,
      2,
    ),
  });

  const [singleValidationError, setSingleValidationError] = useState<string | null>(null);
  const [batchValidationError, setBatchValidationError] = useState<string | null>(null);

  type SingleFormKey = keyof typeof singleForm;

  const singleMutation = useMutation({
    mutationFn: (payload: IngestEventRequest) => apiClient.ingestSingle(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["events"] });
      void queryClient.invalidateQueries({ queryKey: ["aggregates"] });
    },
  });

  const batchMutation = useMutation({
    mutationFn: (payload: { batch_id?: string; events: IngestEventRequest[] }) =>
      apiClient.ingestBatch({
        batch_id: payload.batch_id,
        events: payload.events,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["events"] });
      void queryClient.invalidateQueries({ queryKey: ["aggregates"] });
    },
  });

  const latestSingleResult = useMemo<IngestSingleResponse | null>(() => {
    return singleMutation.data ?? null;
  }, [singleMutation.data]);

  const latestBatchResult = useMemo<IngestBatchResponse | null>(() => {
    return batchMutation.data ?? null;
  }, [batchMutation.data]);

  const submitSingle = () => {
    setSingleValidationError(null);
    const parsed = singleEventSchema.safeParse(singleForm);
    if (!parsed.success) {
      setSingleValidationError(parsed.error.issues[0]?.message ?? "Invalid payload");
      return;
    }

    const occurredAt = new Date(parsed.data.occurred_at);
    if (Number.isNaN(occurredAt.getTime())) {
      setSingleValidationError("occurred_at must be a valid ISO date-time");
      return;
    }

    let attributes: Record<string, unknown>;
    try {
      attributes = parseJsonObject(parsed.data.attributes);
    } catch (error) {
      setSingleValidationError(error instanceof Error ? error.message : "Invalid attributes object");
      return;
    }

    singleMutation.mutate({
      event_type: parsed.data.event_type,
      occurred_at: occurredAt.toISOString(),
      source: parsed.data.source || undefined,
      user_id: parsed.data.user_id || undefined,
      session_id: parsed.data.session_id || undefined,
      severity: parsed.data.severity || undefined,
      url: parsed.data.url || undefined,
      referrer: parsed.data.referrer || undefined,
      schema_version: parsed.data.schema_version || undefined,
      idempotency_key: parsed.data.idempotency_key || undefined,
      attributes,
    });
  };

  const submitBatch = () => {
    setBatchValidationError(null);
    const parsed = batchSchema.safeParse(batchForm);
    if (!parsed.success) {
      setBatchValidationError(parsed.error.issues[0]?.message ?? "Invalid batch payload");
      return;
    }

    let events: unknown;
    try {
      events = JSON.parse(parsed.data.events_json);
    } catch {
      setBatchValidationError("events_json must be valid JSON array");
      return;
    }

    if (!Array.isArray(events) || events.length === 0 || events.length > 1000) {
      setBatchValidationError("events_json must contain 1..1000 event items");
      return;
    }

    const validatedEvents = batchEventSchema.array().safeParse(events);
    if (!validatedEvents.success) {
      setBatchValidationError(validatedEvents.error.issues[0]?.message ?? "Invalid batch event payload");
      return;
    }

    let normalizedEvents: IngestEventRequest[];
    try {
      normalizedEvents = validatedEvents.data.map((event: z.infer<typeof batchEventSchema>) => {
        const occurredAt = new Date(event.occurred_at);
        if (Number.isNaN(occurredAt.getTime())) {
          throw new Error("All occurred_at values must be valid ISO date-time");
        }
        return {
          ...event,
          occurred_at: occurredAt.toISOString(),
        };
      });
    } catch (error) {
      setBatchValidationError(error instanceof Error ? error.message : "Invalid batch events");
      return;
    }

    batchMutation.mutate({ batch_id: parsed.data.batch_id || undefined, events: normalizedEvents });
  };

  return (
    <div className="page-stack">
      <Panel
        title="Ingestion Mode"
        subtitle="Single event for manual tests, batch for replay and bulk checks."
      >
        <div className="segmented-control">
          <button
            type="button"
            className={mode === "single" ? "segmented active" : "segmented"}
            onClick={() => setMode("single")}
          >
            Single
          </button>
          <button
            type="button"
            className={mode === "batch" ? "segmented active" : "segmented"}
            onClick={() => setMode("batch")}
          >
            Batch
          </button>
        </div>
      </Panel>

      {mode === "single" ? (
        <Panel title="Single Ingest" subtitle="POST /v1/ingest/events">
          <div className="form-grid two-columns">
            {Object.entries(singleForm).map(([key, value]) => (
              <label key={key} className={key === "attributes" ? "full-width" : undefined}>
                {key}
                {key === "attributes" ? (
                  <textarea
                    rows={6}
                    value={value}
                    onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                      setSingleForm((previous) => ({
                        ...previous,
                        [key as SingleFormKey]: event.target.value,
                      }))
                    }
                  />
                ) : (
                  <input
                    type="text"
                    value={value}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                      setSingleForm((previous) => ({
                        ...previous,
                        [key as SingleFormKey]: event.target.value,
                      }))
                    }
                  />
                )}
              </label>
            ))}
          </div>

          {singleValidationError && <div className="inline-error">{singleValidationError}</div>}

          <div className="button-row">
            <button
              type="button"
              className="primary-button"
              onClick={submitSingle}
              disabled={singleMutation.isPending}
            >
              Submit Single Event
            </button>
          </div>

          {singleMutation.isPending && <LoadingState text="Submitting event..." />}
          <ErrorState error={asApiError(singleMutation.error)} onRetry={submitSingle} />

          {latestSingleResult && (
            <div className="result-card">
              <h3>Last Result</h3>
              <p>
                <strong>Status:</strong> {latestSingleResult.result.status}
              </p>
              <p>
                <strong>Event ID:</strong> {latestSingleResult.result.event_id}
              </p>
              <p>
                <strong>Duplicate Reason:</strong> {latestSingleResult.result.duplicate_reason ?? "—"}
              </p>
            </div>
          )}
        </Panel>
      ) : (
        <Panel title="Batch Ingest" subtitle="POST /v1/ingest/events:batch">
          <div className="form-grid">
            <label>
              batch_id (optional)
              <input
                type="text"
                value={batchForm.batch_id}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                  setBatchForm((previous) => ({ ...previous, batch_id: event.target.value }))
                }
              />
            </label>

            <label>
              events_json
              <textarea
                rows={12}
                value={batchForm.events_json}
                onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setBatchForm((previous) => ({ ...previous, events_json: event.target.value }))
                }
              />
            </label>
          </div>

          {batchValidationError && <div className="inline-error">{batchValidationError}</div>}

          <div className="button-row">
            <button
              type="button"
              className="primary-button"
              onClick={submitBatch}
              disabled={batchMutation.isPending}
            >
              Submit Batch
            </button>
          </div>

          {batchMutation.isPending && <LoadingState text="Submitting batch..." />}
          <ErrorState error={asApiError(batchMutation.error)} onRetry={submitBatch} />

          {latestBatchResult && (
            <div className="stack">
              <div className="metric-grid">
                <div className="metric-card">
                  <span>Total</span>
                  <strong>{latestBatchResult.total_count}</strong>
                </div>
                <div className="metric-card">
                  <span>Accepted</span>
                  <strong>{latestBatchResult.accepted_count}</strong>
                </div>
                <div className="metric-card">
                  <span>Duplicate</span>
                  <strong>{latestBatchResult.duplicate_count}</strong>
                </div>
              </div>

              <table className="data-table compact">
                <thead>
                  <tr>
                    <th>Event ID</th>
                    <th>Status</th>
                    <th>Duplicate Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {latestBatchResult.results.map((item) => (
                    <tr key={item.event_id}>
                      <td>{item.event_id}</td>
                      <td>{item.status}</td>
                      <td>{item.duplicate_reason ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}

function parseJsonObject(raw?: string): Record<string, unknown> {
  if (!raw || !raw.trim()) {
    return {};
  }
  const parsed = JSON.parse(raw) as unknown;
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
    return parsed as Record<string, unknown>;
  }
  throw new Error("attributes must be a JSON object");
}

