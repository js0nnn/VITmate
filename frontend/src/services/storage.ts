/**
 * Browser-local persistence. Everything is namespaced under "vitmate:" and
 * failures (private mode, quota, corrupted JSON) fall back to defaults.
 */
const PREFIX = "vitmate:";

export const STORAGE_KEYS = {
  conversations: "conversations.v1",
  activeConversation: "activeConversation",
  theme: "theme",
  inputMode: "inputMode",
  speechBannerDismissed: "speechBannerDismissed",
} as const;

export function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // Storage full or unavailable: the app keeps working without persistence.
  }
}

export function readString(key: string): string | null {
  try {
    return localStorage.getItem(PREFIX + key);
  } catch {
    return null;
  }
}

export function writeString(key: string, value: string): void {
  try {
    localStorage.setItem(PREFIX + key, value);
  } catch {
    // ignore
  }
}
