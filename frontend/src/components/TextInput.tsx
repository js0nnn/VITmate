import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";

interface TextInputProps {
  disabled: boolean;
  maxLength: number;
  onSend: (text: string) => void;
}

const MAX_HEIGHT_PX = 180;

export function TextInput({ disabled, maxLength, onSend }: TextInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = value.trim().length > 0 && !disabled;

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Grow with the content up to a maximum height.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter inserts a new line. Ignore Enter while composing (IME).
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form className="text-input" onSubmit={submit}>
      <label htmlFor="chat-input" className="visually-hidden">
        Message VITmate
      </label>
      <textarea
        id="chat-input"
        ref={textareaRef}
        rows={1}
        value={value}
        maxLength={maxLength}
        placeholder="Ask anything about VIT…"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
      />
      <button type="submit" className="send-button" disabled={!canSend} aria-label="Send message">
        <ArrowUp size={18} />
      </button>
    </form>
  );
}
