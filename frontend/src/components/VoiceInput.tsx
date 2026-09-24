import { useState } from "react";
import { AlertCircle, Check, Loader2, Mic, MicOff, Square } from "lucide-react";
import { SPEECH_ERROR_MESSAGES, useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { SpeechSupportModal } from "./SpeechSupportBanner";

interface VoiceInputProps {
  disabled: boolean;
  onTranscript: (text: string) => void;
  onSwitchToText: () => void;
}

const STATUS_TEXT = {
  idle: "Tap the microphone and ask your question",
  listening: "Listening…",
  processing: "Processing…",
  success: "Got it!",
  error: "",
} as const;

export function VoiceInput({ disabled, onTranscript, onSwitchToText }: VoiceInputProps) {
  const speech = useSpeechRecognition({ onTranscript });
  const [learnMoreOpen, setLearnMoreOpen] = useState(false);

  if (!speech.supported) {
    return (
      <div className="voice-input voice-unsupported" role="status">
        <MicOff size={22} aria-hidden="true" />
        <p>{SPEECH_ERROR_MESSAGES[speech.unsupportedReason ?? "unsupported"]}</p>
        <div className="voice-unsupported-actions">
          <button className="link-button" onClick={() => setLearnMoreOpen(true)} aria-haspopup="dialog">
            Learn more
          </button>
          <button className="pill-button" onClick={onSwitchToText}>
            Switch to Type
          </button>
        </div>
        <SpeechSupportModal open={learnMoreOpen} onClose={() => setLearnMoreOpen(false)} />
      </div>
    );
  }

  const { status } = speech;
  const listening = status === "listening";
  const busy = status === "processing" || (disabled && status !== "listening");
  const thinking = disabled && (status === "idle" || status === "success");

  const onMicClick = () => {
    if (listening) speech.stop();
    else if (!busy) speech.start();
  };

  return (
    <div className={`voice-input is-${status}`}>
      <div className="mic-stage">
        {listening && (
          <>
            <span className="mic-ring" aria-hidden="true" />
            <span className="mic-ring mic-ring-delayed" aria-hidden="true" />
          </>
        )}
        <button
          className="mic-button"
          onClick={onMicClick}
          disabled={busy}
          aria-label={listening ? "Stop listening" : "Start voice input"}
          aria-pressed={listening}
        >
          {status === "processing" || thinking ? (
            <Loader2 size={26} className="spin" />
          ) : status === "success" ? (
            <Check size={26} />
          ) : listening ? (
            <Square size={20} fill="currentColor" />
          ) : (
            <Mic size={26} />
          )}
        </button>
      </div>

      <div className="voice-status" aria-live="polite">
        {status === "error" ? (
          <p className="voice-error" role="alert">
            <AlertCircle size={16} aria-hidden="true" />
            {speech.errorMessage}
          </p>
        ) : (
          <>
            <p className="voice-status-text">
              {thinking ? "VITmate is thinking…" : STATUS_TEXT[status]}
              {listening && (
                <span className="waveform" aria-hidden="true">
                  <span /><span /><span /><span /><span />
                </span>
              )}
            </p>
            {speech.interim && <p className="voice-transcript">“{speech.interim}”</p>}
          </>
        )}
        {listening && (
          <button className="link-button" onClick={speech.cancel}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
