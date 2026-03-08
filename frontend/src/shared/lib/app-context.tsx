import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { createApiClient } from "../api/client";
import { clearSettings, DEFAULT_SETTINGS, loadSettings, saveSettings } from "./storage";
import type { ApiErrorModel, AppSettings, RequestSummary } from "./types";

interface AppContextValue {
  settings: AppSettings;
  updateSettings: (patch: Partial<AppSettings>) => void;
  resetSettings: () => void;
  latestApiError: ApiErrorModel | null;
  clearLatestApiError: () => void;
  requestSummaries: RequestSummary[];
  clearRequestSummaries: () => void;
  apiClient: ReturnType<typeof createApiClient>;
}

const AppContext = createContext<AppContextValue | null>(null);

const MAX_REQUEST_SUMMARIES = 30;

export function AppProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(() => loadSettings());
  const [latestApiError, setLatestApiError] = useState<ApiErrorModel | null>(null);
  const [requestSummaries, setRequestSummaries] = useState<RequestSummary[]>([]);

  const updateSettings = useCallback((patch: Partial<AppSettings>) => {
    setSettings((previous) => {
      const next: AppSettings = {
        apiBaseUrl: patch.apiBaseUrl?.trim() ?? previous.apiBaseUrl,
        ingestKey: patch.ingestKey?.trim() ?? previous.ingestKey,
        environmentLabel: patch.environmentLabel?.trim() ?? previous.environmentLabel,
      };
      saveSettings(next);
      return next;
    });
  }, []);

  const resetSettings = useCallback(() => {
    clearSettings();
    setSettings(DEFAULT_SETTINGS);
  }, []);

  const clearLatestApiError = useCallback(() => {
    setLatestApiError(null);
  }, []);

  const clearRequestSummaries = useCallback(() => {
    setRequestSummaries([]);
  }, []);

  const apiClient = useMemo(
    () =>
      createApiClient({
        settings,
        onError: (error) => {
          setLatestApiError(error);
        },
        onRequestComplete: (entry) => {
          setRequestSummaries((previous) => {
            const next: RequestSummary = {
              id: crypto.randomUUID(),
              timestamp: new Date().toISOString(),
              method: entry.method,
              path: entry.path,
              status: entry.status,
              durationMs: entry.durationMs,
              requestId: entry.requestId,
              errorMessage: entry.errorMessage,
            };
            return [next, ...previous].slice(0, MAX_REQUEST_SUMMARIES);
          });
        },
      }),
    [settings],
  );

  const value = useMemo<AppContextValue>(
    () => ({
      settings,
      updateSettings,
      resetSettings,
      latestApiError,
      clearLatestApiError,
      requestSummaries,
      clearRequestSummaries,
      apiClient,
    }),
    [
      settings,
      updateSettings,
      resetSettings,
      latestApiError,
      clearLatestApiError,
      requestSummaries,
      clearRequestSummaries,
      apiClient,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext(): AppContextValue {
  const value = useContext(AppContext);
  if (!value) {
    throw new Error("useAppContext must be used inside AppProvider");
  }
  return value;
}

