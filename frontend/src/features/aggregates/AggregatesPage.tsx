import { useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";

import { useAppContext } from "../../shared/lib/app-context";
import { asApiError } from "../../shared/lib/errors";
import { queryKeys } from "../../shared/lib/query-client";
import type {
  AggregateCountParams,
  AggregateTopEventTypesParams,
  AggregateTopUrlsParams,
  AggregateUniqueUsersParams,
} from "../../shared/lib/types";
import { DataSourceBadge } from "../../shared/ui/DataSourceBadge";
import { Panel } from "../../shared/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../shared/ui/StatusState";

interface AggregateFilters {
  occurred_from: string;
  occurred_to: string;
  event_type: string;
  source: string;
  severity: string;
  geo_country: string;
  is_bot: "" | "true" | "false";
  limit: string;
}

const defaultFilters: AggregateFilters = {
  occurred_from: "",
  occurred_to: "",
  event_type: "",
  source: "",
  severity: "",
  geo_country: "",
  is_bot: "",
  limit: "10",
};

export function AggregatesPage() {
  const { apiClient } = useAppContext();
  const [form, setForm] = useState<AggregateFilters>(defaultFilters);
  const [submitted, setSubmitted] = useState<AggregateFilters | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const resolvedFilters = useMemo(() => {
    if (!submitted) {
      return null;
    }
    const limit = Number.parseInt(submitted.limit, 10);
    const normalizedLimit = Number.isFinite(limit) ? Math.min(Math.max(limit, 1), 100) : 10;
    const isBot =
      submitted.is_bot === ""
        ? undefined
        : submitted.is_bot === "true"
          ? true
          : false;

    const common = {
      occurred_from: toIsoOrUndefined(submitted.occurred_from),
      occurred_to: toIsoOrUndefined(submitted.occurred_to),
      source: submitted.source || undefined,
      severity: submitted.severity || undefined,
      geo_country: submitted.geo_country || undefined,
      is_bot: isBot,
    };

    const countParams: AggregateCountParams = {
      ...common,
      event_type: submitted.event_type || undefined,
    };

    const topTypesParams: AggregateTopEventTypesParams = {
      ...common,
      limit: normalizedLimit,
    };

    const topUrlsParams: AggregateTopUrlsParams = {
      ...common,
      event_type: submitted.event_type || undefined,
      limit: normalizedLimit,
    };

    const uniqueUsersParams: AggregateUniqueUsersParams = {
      ...common,
      event_type: submitted.event_type || undefined,
    };

    return { countParams, topTypesParams, topUrlsParams, uniqueUsersParams };
  }, [submitted]);

  const [countQuery, topEventTypesQuery, topUrlsQuery, uniqueUsersQuery] = useQueries({
    queries: [
      {
        queryKey: queryKeys.aggregateCount(resolvedFilters?.countParams ?? {}),
        queryFn: () => apiClient.aggregateCount(resolvedFilters!.countParams),
        enabled: Boolean(resolvedFilters),
      },
      {
        queryKey: queryKeys.aggregateTopEventTypes(resolvedFilters?.topTypesParams ?? {}),
        queryFn: () => apiClient.aggregateTopEventTypes(resolvedFilters!.topTypesParams),
        enabled: Boolean(resolvedFilters),
      },
      {
        queryKey: queryKeys.aggregateTopUrls(resolvedFilters?.topUrlsParams ?? {}),
        queryFn: () => apiClient.aggregateTopUrls(resolvedFilters!.topUrlsParams),
        enabled: Boolean(resolvedFilters),
      },
      {
        queryKey: queryKeys.aggregateUniqueUsers(resolvedFilters?.uniqueUsersParams ?? {}),
        queryFn: () => apiClient.aggregateUniqueUsers(resolvedFilters!.uniqueUsersParams),
        enabled: Boolean(resolvedFilters),
      },
    ],
  });

  const submit = () => {
    setValidationError(null);
    if (!form.occurred_from && !form.occurred_to) {
      setValidationError("At least one time bound is required");
      return;
    }

    if (form.occurred_from && Number.isNaN(new Date(form.occurred_from).getTime())) {
      setValidationError("occurred_from must be valid");
      return;
    }
    if (form.occurred_to && Number.isNaN(new Date(form.occurred_to).getTime())) {
      setValidationError("occurred_to must be valid");
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

    setSubmitted(form);
  };

  return (
    <div className="page-stack">
      <Panel title="Aggregate Filters" subtitle="Runs four aggregate endpoints in parallel.">
        <div className="form-grid three-columns">
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
            limit
            <input
              type="number"
              min={1}
              max={100}
              value={form.limit}
              onChange={(event) => setForm((p) => ({ ...p, limit: event.target.value }))}
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
            source
            <input
              type="text"
              value={form.source}
              onChange={(event) => setForm((p) => ({ ...p, source: event.target.value }))}
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
            geo_country
            <input
              type="text"
              value={form.geo_country}
              onChange={(event) => setForm((p) => ({ ...p, geo_country: event.target.value }))}
            />
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
        </div>

        {validationError && <div className="inline-error">{validationError}</div>}

        <div className="button-row">
          <button type="button" className="primary-button" onClick={submit}>
            Run Aggregate Queries
          </button>
        </div>
      </Panel>

      <div className="page-grid two-columns">
        <Panel title="Count" subtitle="GET /v1/aggregates/count">
          {!submitted && <EmptyState text="Submit filters to run aggregate queries." />}
          {countQuery.isFetching && <LoadingState text="Loading count..." />}
          <ErrorState error={asApiError(countQuery.error)} onRetry={() => countQuery.refetch()} />
          {countQuery.data && (
            <div className="result-card">
              <p className="metric-value">{countQuery.data.value}</p>
              <DataSourceBadge value={countQuery.data.data_source} />
            </div>
          )}
        </Panel>

        <Panel title="Unique Users" subtitle="GET /v1/aggregates/unique-users">
          {!submitted && <EmptyState text="Submit filters to run aggregate queries." />}
          {uniqueUsersQuery.isFetching && <LoadingState text="Loading unique users..." />}
          <ErrorState error={asApiError(uniqueUsersQuery.error)} onRetry={() => uniqueUsersQuery.refetch()} />
          {uniqueUsersQuery.data && (
            <div className="result-card">
              <p className="metric-value">{uniqueUsersQuery.data.value}</p>
              <DataSourceBadge value={uniqueUsersQuery.data.data_source} />
            </div>
          )}
        </Panel>
      </div>

      <div className="page-grid two-columns">
        <Panel title="Top Event Types" subtitle="GET /v1/aggregates/top-event-types">
          {!submitted && <EmptyState text="Submit filters to run aggregate queries." />}
          {topEventTypesQuery.isFetching && <LoadingState text="Loading top event types..." />}
          <ErrorState
            error={asApiError(topEventTypesQuery.error)}
            onRetry={() => topEventTypesQuery.refetch()}
          />
          {topEventTypesQuery.data && (
            <div className="stack">
              <DataSourceBadge value={topEventTypesQuery.data.data_source} />
              {topEventTypesQuery.data.items.length === 0 ? (
                <EmptyState text="No buckets returned for top event types." />
              ) : (
                <table className="data-table compact">
                  <thead>
                    <tr>
                      <th>Event Type</th>
                      <th>Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topEventTypesQuery.data.items.map((item) => (
                      <tr key={item.key}>
                        <td>{item.key}</td>
                        <td>{item.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </Panel>

        <Panel title="Top URLs" subtitle="GET /v1/aggregates/top-urls">
          {!submitted && <EmptyState text="Submit filters to run aggregate queries." />}
          {topUrlsQuery.isFetching && <LoadingState text="Loading top URLs..." />}
          <ErrorState error={asApiError(topUrlsQuery.error)} onRetry={() => topUrlsQuery.refetch()} />
          {topUrlsQuery.data && (
            <div className="stack">
              <DataSourceBadge value={topUrlsQuery.data.data_source} />
              {topUrlsQuery.data.items.length === 0 ? (
                <EmptyState text="No buckets returned for top URLs." />
              ) : (
                <table className="data-table compact">
                  <thead>
                    <tr>
                      <th>URL Host</th>
                      <th>Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topUrlsQuery.data.items.map((item) => (
                      <tr key={item.key}>
                        <td>{item.key}</td>
                        <td>{item.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </Panel>
      </div>
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

