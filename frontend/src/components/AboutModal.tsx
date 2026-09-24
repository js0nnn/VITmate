import { useEffect, useRef } from "react";
import { Brain, Database, Mic, X } from "lucide-react";
import { LogoMark, Wordmark } from "./Logo";

interface AboutModalProps {
  open: boolean;
  onClose: () => void;
}

export function AboutModal({ open, onClose }: AboutModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !dialogRef.current) return;
      // Keep keyboard focus inside the dialog.
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>("button, a[href]");
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="about-title" ref={dialogRef}>
        <button className="icon-button modal-close" onClick={onClose} aria-label="Close" ref={closeRef}>
          <X size={18} />
        </button>

        <div className="about-hero">
          <LogoMark size={56} />
          <h2 id="about-title" className="about-title">
            <Wordmark />
          </h2>
          <p className="about-tagline">Your VIT Campus Companion</p>
          <p className="about-subtitle">Voice-Enabled Deep Learning Chatbot</p>
        </div>

        <p className="about-description">
          VITmate answers questions about VIT academics, admissions, campus life and careers. You can type or speak.
          A fine-tuned transformer classifies each question's intent, and the answer comes from a knowledge base built from
          official VIT web pages.
        </p>

        <ul className="about-features">
          <li><Mic size={16} aria-hidden="true" /> Browser speech recognition</li>
          <li><Brain size={16} aria-hidden="true" /> Transformer intent classifier</li>
          <li><Database size={16} aria-hidden="true" /> Curated VIT knowledge base</li>
        </ul>

        <div className="about-credit">
          <span className="about-credit-label">Developed by</span>
          <strong>B. Jaison Edward</strong>
          <span>Reg. No: 23BAI0094</span>
        </div>

        <p className="about-disclaimer">
          A student lab project and not an official VIT service. Always confirm important details on{" "}
          <a href="https://vit.ac.in/" target="_blank" rel="noopener noreferrer">vit.ac.in</a>.
        </p>
      </div>
    </div>
  );
}
