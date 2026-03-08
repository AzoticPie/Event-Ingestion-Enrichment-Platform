import { useMemo, useState } from "react";

import { useAppContext } from "../../shared/lib/app-context";
import { formatDateTime } from "../../shared/lib/time";
import { maskSecret } from "../../shared/lib/storage";
import { Panel } from "../../shared/ui/Panel";

export function SettingsPage() {
  const {
    settings,
    updateSettings,
    resetSettings,
    requestSummaries,
    clearRequestSummaries,
  } = useAppContext();

  const [formState, setFormState] = useState({
    apiBaseUrl: settings.apiBaseUrl,
    ingestKey: settings.ingestKey,
    environmentLabel: settings.environmentLabel,
  });

  const maskedKeyPreview = useMemo(() => maskSecret(formState.ingestKey), [formState.ingestKey]);

  const handleSave = () => {
    updateSettings(formState);
  };

  const handleReset = () => {
    resetSettings();
    setFormState({
      apiBaseUrl: "http://localhost:8000",
      ingestKey: "",
      environmentLabel: "local",
    });
  };

  return (
    <div className="page-stack">
      <Panel title="API Settings" subtitle="Stored in sessionStorage for current browser session only.">
        <div className="form-grid">
          <label>
            API Base URL
            <input
              type="url"
              value={formState.apiBaseUrl}
              onChange={(event) =>
                setFormState((previous) => ({ ...previous, apiBaseUrl: event.target.value }))
              }
              placeholder="http://localhost:8000"
            />
          </label>

          <label>
            Environment Label
            <input
              type="text"
              value={formState.environmentLabel}
              onChange={(event) =>
                setFormState((previous) => ({ ...previous, environmentLabel: event.target.value }))
              }
              placeholder="local"
            />
          </label>

          <label>
            X-Ingest-Key
            <input
              type="password"
              value={formState.ingestKey}
              onChange={(event) =>
                setFormState((previous) => ({ ...previous, ingestKey: event.target.value }))
              }
              placeholder="ing_..."
              autoComplete="off"
            />
          </label>
        </div>

        <p className="muted">Masked key preview: {maskedKeyPreview || "(empty)"}</p>

        <div className="button-row">
          <button type="button" className="primary-button" onClick={handleSave}>
            Save Settings
          </button>
          <button type="button" className="secondary-button" onClick={handleReset}>
            Reset to Defaults
          </button>
        </div>
      </Panel>

      <Panel
        title="Request Summaries"
        subtitle="Last 30 API requests for troubleshooting without browser devtools."
        actions={
          <button type="button" className="ghost-button" onClick={clearRequestSummaries}>
            Clear
          </button>
        }
      >
        {requestSummaries.length === 0 ? (
          <p className="muted">No requests recorded yet.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Method</th>
                  <th>Path</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Request ID</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {requestSummaries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{formatDateTime(entry.timestamp)}</td>
                    <td>{entry.method}</td>
                    <td>{entry.path}</td>
                    <td>{entry.status}</td>
                    <td>{entry.durationMs} ms</td>
                    <td>{entry.requestId ?? "—"}</td>
                    <td>{entry.errorMessage ?? "—"}</td>
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

