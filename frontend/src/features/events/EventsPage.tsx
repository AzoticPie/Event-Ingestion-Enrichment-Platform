import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAppContext } from "../../shared/lib/app-context";
import { asApiError } from "../../shared/lib/errors";
import { formatDateTime } from "../../shared/lib/time";
import { queryKeys } from "../../shared/lib/query-client";
import type { EventListItem, EventsListParams } from "../../shared/lib/types";
import { Panel } from "../../shared/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../shared/ui/StatusState";

interface EventsFilterForm {
  limit: string;
  sort: "asc" | "desc";
  occurred_from: string;
  occurred_to: string;
  event_type: string;
  severity: string;
  source: string;
  user_id: string;
  session_id: string;
  ingest_status: string;
  geo_country: string;
  is_bot: "" | "true" | "false";
}

const defaultFilters: EventsFilterForm = {
  limit: "50",
  sort: "desc",
  occurred_from: "",
  occurred_to: "",
  event_type: "",
  severity: "",
  source: "",
  user_id: "",
  session_id: "",
  ingest_status: "",
  geo_country: "",
  is_bot: "",
};

export function EventsPage() {
  const { apiClient } = useAppContext();
  const [form, setForm] = useState<EventsFilterForm>(defaultFilters);
  const [submittedFilters, setSubmittedFilters] = useState<EventsFilterForm>(defaultFilters);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const listParams = useMemo<EventsListParams>(() => {
    const limit = Number.parseInt(submittedFilters.limit || "50", 10);
    return {
      limit: Number.isFinite(limit) ? Math.min(Math.max(limit, 1), 200) : 50,
      sort: submittedFilters.sort,
      cursor,
      occurred_from: toIsoOrUndefined(submittedFilters.occurred_from),
      occurred_to: toIsoOrUndefined(submittedFilters.occurred_to),
      event_type: submittedFilters.event_type || undefined,
      severity: submittedFilters.severity || undefined,
      source: submittedFilters.source || undefined,
      user_id: submittedFilters.user_id || undefined,
      session_id: submittedFilters.session_id || undefined,
      ingest_status: submittedFilters.ingest_status || undefined,
      geo_country: submittedFilters.geo_country || undefined,
      is_bot:
        submittedFilters.is_bot === ""
          ? undefined
          : submittedFilters.is_bot === "true"
            ? true
            : false,
    };
  }, [submittedFilters, cursor]);

  const eventsQuery = useQuery({
    queryKey: queryKeys.eventsList(listParams),
    queryFn: () => apiClient.listEvents(listParams),
  });

  const detailQuery = useQuery({
    queryKey: queryKeys.eventDetail(selectedEventId ?? ""),
    queryFn: () => apiClient.getEventDetail(selectedEventId ?? ""),
    enabled: Boolean(selectedEventId),
  });

  const submitFilters = () => {
    setValidationError(null);
    if (form.occurred_from && Number.isNaN(new Date(form.occurred_from).getTime())) {
      setValidationError("occurred_from must be a valid date-time");
      return;
    }
    if (form.occurred_to && Number.isNaN(new Date(form.occurred_to).getTime())) {
      setValidationError("occurred_to must be a valid date-time");
      return;
    }
    if (form.occurred_from && form.occurred_to) {
      const from = new Date(form.occurred_from).getTime();
      const to = new Date(form.occurred_to).getTime();
      if (from > to) {
        setValidationError("occurred_from must be earlier than occurred_to");
        return;
      }
    }

    setCursor(undefined);
    setSubmittedFilters(form);
  };

  const goNextPage = () => {
    if (eventsQuery.data?.next_cursor) {
      setCursor(eventsQuery.data.next_cursor);
    }
  };

  return (
    <div className="page-grid two-columns-left-wide">
      <div className="page-stack">
        <Panel title="Event Filters" subtitle="GET /v1/events with cursor pagination">
          <div className="form-grid three-columns">
            <label>
              limit
              <input
                type="number"
                min={1}
                max={200}
                value={form.limit}
                onChange={(event) => setForm((p) => ({ ...p, limit: event.target.value }))}
              />
            </label>

            <label>
              sort
              <select
                value={form.sort}
                onChange={(event) => setForm((p) => ({ ...p, sort: event.target.value as "asc" | "desc" }))}
              >
                <option value="desc">desc</option>
                <option value="asc">asc</option>
              </select>
            </label>

            <label>
              is_bot
              <select
                value={form.is_bot}
                onChange={(event) =>
                  setForm((p) => ({ ...p, is_bot: event.target.value as "" | "true" | "false" }))
                }
              >
                <option value="">any</option>
                <option value="false">false</option>
                <option value="true">true</option>
              </select>
            </label>

            <label>
              occurred_from
              <input
                type="datetime-local"
                value={form.occurred_from}
                onChange={(event) => setForm((p) => ({ ...p, occurred_from: event.target.value }))}
              />
            </label>

            <label>
              occurred_to
              <input
                type="datetime-local"
                value={form.occurred_to}
                onChange={(event) => setForm((p) => ({ ...p, occurred_to: event.target.value }))}
              />
            </label>

            <label>
              event_type
              <input
                type="text"
                value={form.event_type}
                onChange={(event) => setForm((p) => ({ ...p, event_type: event.target.value }))}
              />
            </label>

            <label>
              severity
              <input
                type="text"
                value={form.severity}
                onChange={(event) => setForm((p) => ({ ...p, severity: event.target.value }))}
              />
            </label>

            <label>
              source
              <input
                type="text"
                value={form.source}
                onChange={(event) => setForm((p) => ({ ...p, source: event.target.value }))}
              />
            </label>

            <label>
              user_id
              <input
                type="text"
                value={form.user_id}
                onChange={(event) => setForm((p) => ({ ...p, user_id: event.target.value }))}
              />
            </label>

            <label>
              session_id
              <input
                type="text"
                value={form.session_id}
                onChange={(event) => setForm((p) => ({ ...p, session_id: event.target.value }))}
              />
            </label>

            <label>
              ingest_status
              <input
                type="text"
                value={form.ingest_status}
                onChange={(event) => setForm((p) => ({ ...p, ingest_status: event.target.value }))}
              />
            </label>

            <label>
              geo_country
              <input
                type="text"
                value={form.geo_country}
                onChange={(event) => setForm((p) => ({ ...p, geo_country: event.target.value }))}
              />
            </label>
          </div>

          {validationError && <div className="inline-error">{validationError}</div>}

          <div className="button-row">
            <button type="button" className="primary-button" onClick={submitFilters}>
              Search Events
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={goNextPage}
              disabled={!eventsQuery.data?.has_more || !eventsQuery.data?.next_cursor}
            >
              Next Page
            </button>
          </div>
        </Panel>

        <Panel title="Events" subtitle="Click a row to load event detail.">
          {eventsQuery.isFetching && <LoadingState text="Loading events..." />}
          <ErrorState error={asApiError(eventsQuery.error)} onRetry={() => eventsQuery.refetch()} />

          {!eventsQuery.isFetching && eventsQuery.data && eventsQuery.data.items.length === 0 && (
            <EmptyState text="No events found for selected filters." />
          )}

          {eventsQuery.data && eventsQuery.data.items.length > 0 && (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Occurred</th>
                    <th>Event Type</th>
                    <th>Source</th>
                    <th>User</th>
                    <th>Status</th>
                    <th>Country</th>
                    <th>Bot</th>
                  </tr>
                </thead>
                <tbody>
                  {eventsQuery.data.items.map((item) => (
                    <tr
                      key={item.event_id}
                      className={selectedEventId === item.event_id ? "selected-row" : undefined}
                      onClick={() => setSelectedEventId(item.event_id)}
                    >
                      <td>{formatDateTime(item.occurred_at)}</td>
                      <td>{item.event_type}</td>
                      <td>{item.source}</td>
                      <td>{item.user_id ?? "—"}</td>
                      <td>{item.ingest_status}</td>
                      <td>{item.geo_country ?? "—"}</td>
                      <td>{String(item.is_bot)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Event Detail" subtitle="GET /v1/events/{event_id}">
        {!selectedEventId && <EmptyState text="Select an event from the table to see full projection." />}

        {selectedEventId && detailQuery.isFetching && <LoadingState text="Loading event detail..." />}
        {selectedEventId && (
          <ErrorState error={asApiError(detailQuery.error)} onRetry={() => detailQuery.refetch()} />
        )}

        {detailQuery.data && (
          <EventDetailCard item={detailQuery.data.item} />
        )}
      </Panel>
    </div>
  );
}

function EventDetailCard({ item }: { item: EventListItem }) {
  return (
    <div className="stack">
      <div className="detail-grid">
        <DetailRow label="event_id" value={item.event_id} />
        <DetailRow label="event_type" value={item.event_type} />
        <DetailRow label="occurred_at" value={formatDateTime(item.occurred_at)} />
        <DetailRow label="received_at" value={formatDateTime(item.received_at)} />
        <DetailRow label="source" value={item.source} />
        <DetailRow label="user_id" value={item.user_id} />
        <DetailRow label="session_id" value={item.session_id} />
        <DetailRow label="severity" value={item.severity} />
        <DetailRow label="url" value={item.url} />
        <DetailRow label="referrer" value={item.referrer} />
        <DetailRow label="ingest_status" value={item.ingest_status} />
        <DetailRow label="geo_country" value={item.geo_country} />
        <DetailRow label="ua_browser" value={item.ua_browser} />
        <DetailRow label="ua_os" value={item.ua_os} />
        <DetailRow label="ua_device" value={item.ua_device} />
        <DetailRow label="url_host" value={item.url_host} />
        <DetailRow label="referrer_domain" value={item.referrer_domain} />
        <DetailRow label="is_bot" value={String(item.is_bot)} />
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

function toIsoOrUndefined(value: string): string | undefined {
  if (!value) {
    return undefined;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

