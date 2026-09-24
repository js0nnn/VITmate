import type { ChatContext, ChatResponse, InputMode, Suggestion } from "../types";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 15000;

export const CONNECTION_ERROR = "Unable to connect to the assistant. Please try again.";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...init, signal: controller.signal });
  } catch {
    throw new ApiError(CONNECTION_ERROR);
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : null;
    throw new ApiError(response.status >= 500 || !detail ? CONNECTION_ERROR : detail);
  }
  return response.json() as Promise<T>;
}

export function sendMessage(message: string, context: ChatContext, inputMode: InputMode): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, context, input_mode: inputMode }),
  });
}

export function fetchSuggestions(): Promise<Suggestion[]> {
  return request<Suggestion[]>("/api/suggestions");
}
