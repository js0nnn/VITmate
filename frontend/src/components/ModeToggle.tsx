import { Keyboard, Mic } from "lucide-react";
import type { InputMode } from "../types";

interface ModeToggleProps {
  mode: InputMode;
  onChange: (mode: InputMode) => void;
}

const OPTIONS: { value: InputMode; label: string; Icon: typeof Mic }[] = [
  { value: "text", label: "Type", Icon: Keyboard },
  { value: "voice", label: "Speak", Icon: Mic },
];

/** Segmented Type / Speak switch with a sliding highlight. */
export function ModeToggle({ mode, onChange }: ModeToggleProps) {
  return (
    <div className="mode-toggle" role="radiogroup" aria-label="Input mode" data-mode={mode}>
      <span className="mode-toggle-thumb" aria-hidden="true" />
      {OPTIONS.map(({ value, label, Icon }) => (
        <button
          key={value}
          role="radio"
          aria-checked={mode === value}
          className={`mode-toggle-option ${mode === value ? "is-active" : ""}`}
          onClick={() => onChange(value)}
          onKeyDown={(event) => {
            if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
              event.preventDefault();
              onChange(mode === "text" ? "voice" : "text");
            }
          }}
          tabIndex={mode === value ? 0 : -1}
        >
          <Icon size={15} aria-hidden="true" />
          {label}
        </button>
      ))}
    </div>
  );
}
