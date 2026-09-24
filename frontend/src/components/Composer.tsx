import type { InputMode } from "../types";
import { ModeToggle } from "./ModeToggle";
import { TextInput } from "./TextInput";
import { VoiceInput } from "./VoiceInput";

interface ComposerProps {
  mode: InputMode;
  pending: boolean;
  maxLength: number;
  onModeChange: (mode: InputMode) => void;
  onSend: (text: string, mode: InputMode) => void;
}

/** Both input methods feed the same `onSend` pipeline. */
export function Composer({ mode, pending, maxLength, onModeChange, onSend }: ComposerProps) {
  return (
    <div className="composer">
      <div className="composer-inner">
        <ModeToggle mode={mode} onChange={onModeChange} />
        <div className="composer-panel" key={mode}>
          {mode === "text" ? (
            <TextInput disabled={pending} maxLength={maxLength} onSend={(text) => onSend(text, "text")} />
          ) : (
            <VoiceInput
              disabled={pending}
              onTranscript={(text) => onSend(text, "voice")}
              onSwitchToText={() => onModeChange("text")}
            />
          )}
        </div>
        <p className="composer-note">
          VITmate answers from official VIT information and can make mistakes. Verify important details on vit.ac.in.
        </p>
      </div>
    </div>
  );
}
