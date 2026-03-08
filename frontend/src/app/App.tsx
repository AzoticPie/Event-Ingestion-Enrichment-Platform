import { Navigate, NavLink, Route, Routes } from "react-router-dom";

import { AggregatesPage } from "../features/aggregates/AggregatesPage";
import { EventsPage } from "../features/events/EventsPage";
import { HealthPage } from "../features/health/HealthPage";
import { IngestionPage } from "../features/ingestion/IngestionPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { useAppContext } from "../shared/lib/app-context";
import { ApiErrorBanner } from "../shared/ui/ApiErrorBanner";

const navItems = [
  { to: "/health", label: "Health" },
  { to: "/ingestion", label: "Ingestion" },
  { to: "/events", label: "Events Explorer" },
  { to: "/aggregates", label: "Aggregates" },
  { to: "/settings", label: "Settings" },
];

export function App() {
  const { settings, latestApiError, clearLatestApiError } = useAppContext();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Event Platform Frontend MVP</h1>
          <p className="muted">Operational console for health, ingestion, query, and aggregate APIs</p>
        </div>
        <span className="env-badge">{settings.environmentLabel || "local"}</span>
      </header>

      <div className="app-body">
        <aside className="app-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </aside>

        <main className="app-main">
          {!settings.ingestKey && (
            <div className="warning-banner">
              X-Ingest-Key is not configured. Protected endpoints will fail until key is set in Settings.
            </div>
          )}

          {latestApiError && (
            <ApiErrorBanner error={latestApiError} onDismiss={clearLatestApiError} />
          )}

          <Routes>
            <Route path="/" element={<Navigate to="/health" replace />} />
            <Route path="/health" element={<HealthPage />} />
            <Route path="/ingestion" element={<IngestionPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/aggregates" element={<AggregatesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/health" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

