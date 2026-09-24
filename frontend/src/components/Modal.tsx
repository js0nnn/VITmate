import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  labelledBy: string;
  className?: string;
  children: ReactNode;
}

/**
 * Accessible dialog: focus moves inside, Tab is trapped, Escape and backdrop close it.
 * Rendered into document.body so no ancestor (e.g. an animated panel with a CSS
 * transform) can become the containing block of the fixed-position overlay.
 */
/** Matches the CSS exit animation (`.modal-overlay.is-closing`). */
export const MODAL_EXIT_MS = 150;

export function Modal({ open, onClose, labelledBy, className = "", children }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  // Stay mounted for a moment after closing so the exit animation can play.
  const [mounted, setMounted] = useState(open);

  useEffect(() => {
    if (open) {
      setMounted(true);
      return;
    }
    const timer = window.setTimeout(() => setMounted(false), MODAL_EXIT_MS);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !dialogRef.current) return;
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

  if (!open && !mounted) return null;

  return createPortal(
    <div
      className={`modal-overlay ${open ? "" : "is-closing"}`}
      onMouseDown={(e) => open && e.target === e.currentTarget && onClose()}
    >
      <div
        className={`modal ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-hidden={!open || undefined}
        ref={dialogRef}
      >
        <button className="icon-button modal-close" onClick={onClose} aria-label="Close" ref={closeRef}>
          <X size={18} />
        </button>
        {children}
      </div>
    </div>,
    document.body,
  );
}
