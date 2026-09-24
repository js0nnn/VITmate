import { memo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Brain, ExternalLink, Mic, RotateCcw, User } from "lucide-react";
import type { AssistantMeta, Message } from "../types";
import { LogoMark } from "./Logo";

// Raw HTML in messages is never rendered (react-markdown escapes it); links open safely.
const markdownComponents: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

function sourceLabel(url: string): string {
  try {
    const { hostname, pathname } = new URL(url);
    const path = pathname.replace(/\/$/, "");
    return path ? `${hostname}${path.length > 32 ? `${path.slice(0, 31)}…` : path}` : hostname;
  } catch {
    return url;
  }
}

/** Display bands for the classifier's softmax confidence (the value itself is unchanged). */
function confidenceLevel(confidence: number): "high" | "medium" | "low" {
  if (confidence >= 0.75) return "high";
  if (confidence >= 0.35) return "medium"; // 0.35 = backend answer threshold
  return "low";
}

function ClassifierReadout({ meta }: { meta: AssistantMeta }) {
  const level = confidenceLevel(meta.confidence);
  const percent = (meta.confidence * 100).toFixed(1);
  return (
    <div className="classifier-readout" title="Output of VITmate's deep-learning intent classifier">
      <span className="classifier-label">
        <Brain size={13} aria-hidden="true" /> Classifier
      </span>
      <span className="classifier-item">
        Intent: <code>{meta.intent}</code>
      </span>
      <span className={`classifier-item confidence is-${level}`}>
        Confidence {percent}%
        <span
          className="confidence-meter"
          role="meter"
          aria-label="Confidence"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Number(percent)}
        >
          <span style={{ width: `${percent}%` }} />
        </span>
        <span className="confidence-level">{level}</span>
      </span>
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
  onRetry?: (message: Message) => void;
  onSuggestion?: (question: string) => void;
}

export const MessageBubble = memo(function MessageBubble({ message, onRetry, onSuggestion }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const meta = message.meta;

  return (
    <article className={`message ${isUser ? "message-user" : "message-assistant"}`}>
      <div className="message-avatar" aria-hidden="true">
        {isUser ? <User size={16} /> : <LogoMark size={30} />}
      </div>
      <div className="message-body">
        <div className="message-author">
          {isUser ? "You" : "VITmate"}
        </div>

        <div className={`message-content ${message.failedText ? "is-error" : ""}`}>
          {isUser ? (
            <p>
              {message.inputMode === "voice" && (
                <span className="voice-prefix" role="img" aria-label="Spoken message" title="Recognised from speech">
                  <Mic size={14} />
                </span>
              )}
              {message.text}
            </p>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.text}
            </ReactMarkdown>
          )}
        </div>

        {message.failedText && onRetry && (
          <button className="retry-button" onClick={() => onRetry(message)}>
            <RotateCcw size={14} /> Try again
          </button>
        )}

        {meta && meta.sources.length > 0 && (
          <div className="message-sources">
            <span className="message-sources-label">Sources</span>
            <ul>
              {meta.sources.map((url) => (
                <li key={url}>
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink size={12} aria-hidden="true" />
                    {sourceLabel(url)}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {meta?.suggestions && meta.suggestions.length > 0 && onSuggestion && (
          <div className="message-suggestions" aria-label="Did you mean">
            {meta.suggestions.map((s) => (
              <button key={s.intent} className="suggestion-chip" onClick={() => onSuggestion(s.question)}>
                {s.question}
              </button>
            ))}
          </div>
        )}

        {meta && <ClassifierReadout meta={meta} />}
      </div>
    </article>
  );
});
