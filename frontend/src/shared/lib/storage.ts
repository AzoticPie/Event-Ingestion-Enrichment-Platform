import { AppSettings } from "./types";

const SETTINGS_KEY = "event-platform.frontend.settings";
const env = (import.meta as { env?: Record<string, string | undefined> }).env ?? {};
const DEFAULT_INGEST_KEY = (env.VITE_DEFAULT_INGEST_KEY ?? "").trim();

export const DEFAULT_SETTINGS: AppSettings = {
  apiBaseUrl: env.VITE_API_BASE_URL ?? "http://localhost:8000",
  ingestKey: DEFAULT_INGEST_KEY,
  environmentLabel: "local",
};

export function loadSettings(): AppSettings {
  try {
    const raw = sessionStorage.getItem(SETTINGS_KEY);
    if (!raw) {
      return DEFAULT_SETTINGS;
    }
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return {
      apiBaseUrl: parsed.apiBaseUrl?.trim() || DEFAULT_SETTINGS.apiBaseUrl,
      ingestKey: parsed.ingestKey?.trim() || "",
      environmentLabel: parsed.environmentLabel?.trim() || DEFAULT_SETTINGS.environmentLabel,
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: AppSettings): void {
  sessionStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

export function clearSettings(): void {
  sessionStorage.removeItem(SETTINGS_KEY);
}

export function maskSecret(secret: string): string {
  if (!secret) {
    return "";
  }
  if (secret.length <= 8) {
    return "*".repeat(secret.length);
  }
  const head = secret.slice(0, 4);
  const tail = secret.slice(-4);
  return `${head}${"*".repeat(secret.length - 8)}${tail}`;
}

