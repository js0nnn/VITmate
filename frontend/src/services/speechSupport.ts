/**
 * Feature detection for the browser's Web Speech API (speech-to-text).
 *
 * Support is decided by the presence of the `SpeechRecognition` constructor
 * (or its `webkit` prefixed form) and a secure context, never by browser name.
 */

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

export type SpeechUnsupportedReason = "unsupported" | "insecure-context";

export function getRecognitionConstructor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Why voice input cannot work here, or null when it is available. */
export function speechUnsupportedReason(): SpeechUnsupportedReason | null {
  if (!getRecognitionConstructor()) return "unsupported";
  if (window.isSecureContext === false) return "insecure-context";
  return null;
}
