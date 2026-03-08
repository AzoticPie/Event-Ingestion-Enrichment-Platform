import { useQuery } from "@tanstack/react-query";

import { useAppContext } from "../../shared/lib/app-context";
import { asApiError } from "../../shared/lib/errors";
import { queryKeys } from "../../shared/lib/query-client";
import { Panel } from "../../shared/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../shared/ui/StatusState";

export function HealthPage() {
  const { apiClient } = useAppContext();

  const liveQuery = useQuery({
    queryKey: queryKeys.healthLive,
    queryFn: () => apiClient.healthLive(),
    enabled: false,
    staleTime: 0,
  });

  const readyQuery = useQuery({
    queryKey: queryKeys.healthReady,
    queryFn: () => apiClient.healthReady(),
    enabled: false,
    staleTime: 0,
  });

  const readyError = asApiError(readyQuery.error);
  const readinessDependencies = extractReadinessDependencies(readyError?.detail);

  return (
    <div className="page-grid two-columns">
      <Panel
        title="Liveness"
        subtitle="Checks if API process is running"
        actions={
          <button type="button" className="primary-button" onClick={() => liveQuery.refetch()}>
            Run Live Check
          </button>
        }
      >
        {liveQuery.isFetching && <LoadingState text="Running liveness check..." />}

        <ErrorState
          error={asApiError(liveQuery.error)}
          onRetry={() => liveQuery.refetch()}
        />

        {!liveQuery.data && !liveQuery.isFetching && !liveQuery.error && (
          <EmptyState text="No live checks executed yet." />
        )}

        {liveQuery.data && (
          <div className="metric-row">
            <span>Status</span>
            <strong>{liveQuery.data.status}</strong>
          </div>
        )}
      </Panel>

      <Panel
        title="Readiness"
        subtitle="Verifies dependencies (Postgres/Redis) and readiness"
        actions={
          <button type="button" className="primary-button" onClick={() => readyQuery.refetch()}>
            Run Ready Check
          </button>
        }
      >
        {readyQuery.isFetching && <LoadingState text="Running readiness check..." />}

        <ErrorState
          error={readyError}
          onRetry={() => readyQuery.refetch()}
        />

        {readinessDependencies && (
          <div className="stack">
            <p className="muted">Readiness dependency details</p>
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>Dependency</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(readinessDependencies).map(([name, state]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>
                      <span className={state.startsWith("ok") ? "status-pill success" : "status-pill warning"}>
                        {state}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!readyQuery.data && !readyQuery.isFetching && !readyQuery.error && (
          <EmptyState text="No readiness checks executed yet." />
        )}

        {readyQuery.data && (
          <div className="stack">
            <div className="metric-row">
              <span>Status</span>
              <strong>{readyQuery.data.status}</strong>
            </div>
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>Dependency</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(readyQuery.data.dependencies).map(([name, state]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>
                      <span className={state.startsWith("ok") ? "status-pill success" : "status-pill warning"}>
                        {state}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

function extractReadinessDependencies(detail: unknown): Record<string, string> | null {
  if (!isObject(detail) || !("detail" in detail)) {
    return null;
  }
  const nested = detail.detail;
  if (!isObject(nested) || !("dependencies" in nested)) {
    return null;
  }
  const dependencies = nested.dependencies;
  if (!isObject(dependencies)) {
    return null;
  }
  const entries = Object.entries(dependencies).filter((entry): entry is [string, string] => {
    return typeof entry[0] === "string" && typeof entry[1] === "string";
  });
  return Object.fromEntries(entries);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

