/**
 * Detection of whether voice input can work in this browser.
 *
 * Three layers, none based on the user-agent string (Brave, for example,
 * reports exactly the same user agent as Chrome):
 *   1. The Web Speech API constructor must exist (missing in Firefox) and the
 *      page must be a secure context.
 *   2. Brave exposes the API but ships no speech service; it is recognised by
 *      its documented `navigator.brave` interface.
 *   3. Any other browser whose speech service fails with a `network` error
 *      while the device is online is marked unavailable for the rest of the
 *      session (see `markSpeechServiceUnavailable`).
 */
import { useSyncExternalStore } from "react";

export interface RecognitionAlternative {
  transcript: string;
}
export interface RecognitionResult {
  isFinal: boolean;
  0: RecognitionAlternative;
}
export interface RecognitionEvent {
  resultIndex: number;
  results: ArrayLike<RecognitionResult>;
}
export interface RecognitionErrorEvent {
  error: string;
}
export interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onresult: ((event: RecognitionEvent) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
export type RecognitionConstructor = new () => Recognition;

export type SpeechUnsupportedReason = "unsupported" | "insecure-context" | "service-unavailable";

export function getRecognitionConstructor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Brave provides the SpeechRecognition API but no speech service behind it. */
function hasApiWithoutSpeechService(): boolean {
  const brave = (navigator as Navigator & { brave?: { isBrave?: unknown } }).brave;
  return typeof brave?.isBrave === "function";
}

let serviceFailedAtRuntime = false;
const listeners = new Set<() => void>();

/** Called when recognition fails with a speech-service error although the device is online. */
export function markSpeechServiceUnavailable(): void {
  if (serviceFailedAtRuntime) return;
  serviceFailedAtRuntime = true;
  listeners.forEach((listener) => listener());
}

/** Why voice input cannot work here, or null when it is available. */
export function speechUnsupportedReason(): SpeechUnsupportedReason | null {
  if (!getRecognitionConstructor()) return "unsupported";
  if (window.isSecureContext === false) return "insecure-context";
  if (serviceFailedAtRuntime || hasApiWithoutSpeechService()) return "service-unavailable";
  return null;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** React hook: re-renders when a runtime failure reveals that voice input is unavailable. */
export function useSpeechUnsupportedReason(): SpeechUnsupportedReason | null {
  return useSyncExternalStore(subscribe, speechUnsupportedReason, speechUnsupportedReason);
}

/** Test helper: forget a runtime failure. */
export function resetSpeechSupportForTests(): void {
  serviceFailedAtRuntime = false;
}
