import { memo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { ExternalLink, Mic, RotateCcw, User } from "lucide-react";
import type { Message } from "../types";
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

interface MessageBubbleProps {
  message: Message;
  onRetry?: (message: Message) => void;
}

export const MessageBubble = memo(function MessageBubble({ message, onRetry }: MessageBubbleProps) {
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
            <span className="message-sources-label">Official sources</span>
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

        {meta && (
          <div className="message-meta" title="Output of the deep-learning intent classifier">
            <span className="intent-chip">
              Intent: <code>{meta.intent}</code>
            </span>
            <span className="intent-chip">Confidence {(meta.confidence * 100).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </article>
  );
});
