import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Browser-native speech-to-text using the Web Speech API.
 *
 * Recognition runs inside the browser (Chromium browsers use the vendor's
 * speech service); VITmate's server never receives audio, only the final text.
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

// Minimal typings for the (still vendor-prefixed) Web Speech API.
interface RecognitionAlternative {
  transcript: string;
}
interface RecognitionResult {
  isFinal: boolean;
  0: RecognitionAlternative;
}
interface RecognitionEvent {
  resultIndex: number;
  results: ArrayLike<RecognitionResult>;
}
interface RecognitionErrorEvent {
  error: string;
}
interface Recognition {
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
type RecognitionConstructor = new () => Recognition;

function getRecognitionConstructor(): RecognitionConstructor | null {
  const w = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

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

const SUCCESS_RESET_MS = 1200;

interface Options {
  lang?: string;
  onTranscript: (text: string) => void;
}

export function useSpeechRecognition({ lang = "en-IN", onTranscript }: Options) {
  const Constructor = getRecognitionConstructor();
  const supported = Constructor !== null;
  const secure = typeof window === "undefined" || window.isSecureContext !== false;

  const [status, setStatus] = useState<SpeechStatus>("idle");
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<SpeechErrorCode | null>(null);

  const recognitionRef = useRef<Recognition | null>(null);
  const finalRef = useRef("");
  const errorRef = useRef<SpeechErrorCode | null>(null);
  const resetTimer = useRef<number>();
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  const fail = useCallback((code: SpeechErrorCode) => {
    errorRef.current = code;
    setError(code);
    setStatus("error");
  }, []);

  const start = useCallback(() => {
    if (recognitionRef.current) return; // already listening
    if (!Constructor) return fail("unsupported");
    if (!secure) return fail("insecure-context");

    window.clearTimeout(resetTimer.current);
    const recognition = new Constructor();
    recognition.lang = lang;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    finalRef.current = "";
    errorRef.current = null;
    setInterim("");
    setError(null);

    recognition.onstart = () => setStatus("listening");
    recognition.onresult = (event) => {
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) finalRef.current += result[0].transcript;
        else interimText += result[0].transcript;
      }
      setInterim((finalRef.current + interimText).trim());
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") fail(toErrorCode(event.error));
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      if (errorRef.current) return;
      const transcript = finalRef.current.trim();
      if (!transcript) return fail("no-speech");
      setStatus("success");
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
    } catch {
      recognitionRef.current = null;
      fail("unknown");
    }
  }, [Constructor, fail, lang, secure]);

  /** Stop listening and finalise what was heard so far. */
  const stop = useCallback(() => {
    if (!recognitionRef.current) return;
    setStatus("processing");
    recognitionRef.current.stop();
  }, []);

  /** Cancel without sending anything. */
  const cancel = useCallback(() => {
    const recognition = recognitionRef.current;
    if (recognition) {
      recognition.onresult = recognition.onerror = recognition.onend = null;
      recognition.abort();
    }
    recognitionRef.current = null;
    setStatus("idle");
    setInterim("");
  }, []);

  const dismissError = useCallback(() => {
    setError(null);
    setStatus("idle");
  }, []);

  useEffect(
    () => () => {
      window.clearTimeout(resetTimer.current);
      recognitionRef.current?.abort();
    },
    [],
  );

  return {
    supported: supported && secure,
    unsupportedReason: !supported ? ("unsupported" as const) : !secure ? ("insecure-context" as const) : null,
    status,
    interim,
    error,
    errorMessage: error ? SPEECH_ERROR_MESSAGES[error] : null,
    start,
    stop,
    cancel,
    dismissError,
  };
}
