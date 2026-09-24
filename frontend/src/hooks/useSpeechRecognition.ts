import { useCallback, useEffect, useRef, useState } from "react";
import {
  getRecognitionConstructor,
  speechUnsupportedReason,
  type Recognition,
  type RecognitionResult,
} from "../services/speechSupport";

/**
 * Browser-native speech-to-text using the Web Speech API.
 *
 * Recognition runs inside the browser (Chromium browsers use the vendor's
 * speech service); VITmate's server never receives audio, only the final text.
 *
 * Pause handling: recognition runs in continuous mode and VITmate decides when
 * the user has finished. Every recognition result restarts a short silence
 * window, so natural pauses ("I want to know about … FFCS registration") do not
 * end the question, while the answer still follows quickly once the user stops.
 */

export type SpeechStatus = "idle" | "listening" | "processing" | "success" | "error";

export type SpeechErrorCode =
  | "unsupported"
  | "insecure-context"
  | "not-allowed"
  | "audio-capture"
  | "no-speech"
  | "network"
  | "language-not-supported"
  | "unknown";

export const SPEECH_ERROR_MESSAGES: Record<SpeechErrorCode, string> = {
  unsupported:
    "Speech recognition isn't supported in this browser. Please use Google Chrome or Microsoft Edge, or switch to Type mode.",
  "insecure-context": "Voice input needs a secure (https) connection or localhost.",
  "not-allowed":
    "Microphone access was blocked. Click the lock/microphone icon in the address bar, allow the microphone for this site, then try again.",
  "audio-capture": "No microphone was found. Please connect a microphone and try again.",
  "no-speech": "I didn't catch anything. Tap the microphone and try speaking again.",
  network: "The browser's speech service couldn't be reached. Check your internet connection and try again.",
  "language-not-supported": "Speech recognition isn't available for this language in your browser.",
  unknown: "Something went wrong with speech recognition. Please try again.",
};

/** Silence after a finalised phrase before the question is submitted. */
export const FINAL_PAUSE_MS = 1200;
/** Silence tolerated while the browser still holds an unfinished (interim) phrase. */
export const INTERIM_PAUSE_MS = 2000;
/** Safety limit for a single question. */
export const MAX_LISTEN_MS = 30000;
const SUCCESS_RESET_MS = 1200;

function toErrorCode(error: string): SpeechErrorCode {
  switch (error) {
    case "not-allowed":
    case "service-not-allowed":
      return "not-allowed";
    case "audio-capture":
    case "no-speech":
    case "network":
    case "language-not-supported":
      return error;
    default:
      return "unknown";
  }
}

/**
 * Join recognised segments into one transcript. Some mobile Chrome builds
 * repeat the cumulative text in every segment, so a segment that already
 * contains everything heard so far replaces it instead of being appended.
 */
export function mergeSegments(segments: string[]): string {
  let merged = "";
  for (const raw of segments) {
    const segment = raw.trim();
    if (!segment) continue;
    if (segment.toLowerCase().startsWith(merged.toLowerCase())) merged = segment;
    else merged = `${merged} ${segment}`;
  }
  return merged.trim();
}

function transcriptOf(results: ArrayLike<RecognitionResult>) {
  const finals: string[] = [];
  const interims: string[] = [];
  for (let i = 0; i < results.length; i += 1) {
    (results[i].isFinal ? finals : interims).push(results[i][0].transcript);
  }
  return { final: mergeSegments(finals), interim: mergeSegments(interims) };
}

interface Options {
  lang?: string;
  onTranscript: (text: string) => void;
}

export function useSpeechRecognition({ lang = "en-IN", onTranscript }: Options) {
  const unsupportedReason = speechUnsupportedReason();

  const [status, setStatus] = useState<SpeechStatus>("idle");
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<SpeechErrorCode | null>(null);

  const recognitionRef = useRef<Recognition | null>(null);
  const transcriptRef = useRef({ final: "", interim: "" });
  const errorRef = useRef<SpeechErrorCode | null>(null);
  const pauseTimer = useRef<number>();
  const maxTimer = useRef<number>();
  const resetTimer = useRef<number>();
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  const clearTimers = () => {
    window.clearTimeout(pauseTimer.current);
    window.clearTimeout(maxTimer.current);
  };

  const fail = useCallback((code: SpeechErrorCode) => {
    errorRef.current = code;
    setError(code);
    setStatus("error");
  }, []);

  /** Stop listening and finalise what was heard so far. */
  const stop = useCallback(() => {
    clearTimers();
    if (!recognitionRef.current) return;
    setStatus("processing");
    recognitionRef.current.stop();
  }, []);

  const start = useCallback(() => {
    if (recognitionRef.current) return; // already listening
    const Constructor = getRecognitionConstructor();
    if (unsupportedReason || !Constructor) return fail(unsupportedReason ?? "unsupported");

    window.clearTimeout(resetTimer.current);
    const recognition = new Constructor();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    transcriptRef.current = { final: "", interim: "" };
    errorRef.current = null;
    setInterim("");
    setError(null);

    recognition.onstart = () => setStatus("listening");
    recognition.onresult = (event) => {
      const heard = transcriptOf(event.results);
      transcriptRef.current = heard;
      setInterim(`${heard.final} ${heard.interim}`.trim());
      // Restart the silence window: shorter once the browser has finalised the phrase.
      window.clearTimeout(pauseTimer.current);
      pauseTimer.current = window.setTimeout(stop, heard.interim ? INTERIM_PAUSE_MS : FINAL_PAUSE_MS);
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") fail(toErrorCode(event.error));
    };
    recognition.onend = () => {
      clearTimers();
      recognitionRef.current = null;
      if (errorRef.current) return;
      // A stopped session finalises pending words; keep interim text if the browser did not.
      const { final, interim: pending } = transcriptRef.current;
      const transcript = mergeSegments([final, pending]);
      if (!transcript) return fail("no-speech");
      setStatus("success");
      setInterim(transcript);
      onTranscriptRef.current(transcript);
      resetTimer.current = window.setTimeout(() => {
        setStatus("idle");
        setInterim("");
      }, SUCCESS_RESET_MS);
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setStatus("listening");
      maxTimer.current = window.setTimeout(stop, MAX_LISTEN_MS);
    } catch {
      recognitionRef.current = null;
      fail("unknown");
    }
  }, [fail, lang, stop, unsupportedReason]);

  /** Cancel without sending anything. */
  const cancel = useCallback(() => {
    clearTimers();
    const recognition = recognitionRef.current;
    if (recognition) {
      recognition.onresult = recognition.onerror = recognition.onend = null;
      recognition.abort();
    }
    recognitionRef.current = null;
    setStatus("idle");
    setInterim("");
  }, []);

  useEffect(
    () => () => {
      clearTimers();
      window.clearTimeout(resetTimer.current);
      const recognition = recognitionRef.current;
      if (recognition) {
        recognition.onresult = recognition.onerror = recognition.onend = null;
        recognition.abort();
      }
    },
    [],
  );

  return {
    supported: unsupportedReason === null,
    unsupportedReason,
    status,
    interim,
    error,
    errorMessage: error ? SPEECH_ERROR_MESSAGES[error] : null,
    start,
    stop,
    cancel,
  };
}
