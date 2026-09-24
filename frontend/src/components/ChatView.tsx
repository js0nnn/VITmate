import { useEffect, useRef } from "react";
import { ArrowUpRight } from "lucide-react";
import type { Message, Suggestion } from "../types";
import { LogoMark } from "./Logo";
import { MessageBubble } from "./MessageBubble";

interface ChatViewProps {
  messages: Message[];
  pending: boolean;
  suggestions: Suggestion[];
  onSuggestion: (question: string) => void;
  onRetry: (message: Message) => void;
}

export function ChatView({ messages, pending, suggestions, onSuggestion, onRetry }: ChatViewProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  if (messages.length === 0) {
    return <WelcomeScreen suggestions={suggestions} onSuggestion={onSuggestion} />;
  }

  return (
    <div className="chat-scroll">
      <div className="chat-thread" role="log" aria-live="polite" aria-label="Conversation">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} onRetry={onRetry} />
        ))}
        {pending && <TypingIndicator />}
        <div ref={endRef} />
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <article className="message message-assistant" aria-label="VITmate is typing">
      <div className="message-avatar" aria-hidden="true">
        <LogoMark size={30} />
      </div>
      <div className="message-body">
        <div className="message-author">VITmate</div>
        <div className="typing-indicator" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </article>
  );
}

interface WelcomeScreenProps {
  suggestions: Suggestion[];
  onSuggestion: (question: string) => void;
}

function WelcomeScreen({ suggestions, onSuggestion }: WelcomeScreenProps) {
  return (
    <div className="chat-scroll">
      <div className="welcome">
        <LogoMark size={64} />
        <h2 className="welcome-title">Hi! I'm VITmate 👋</h2>
        <p className="welcome-subtitle">Your VIT Campus Companion. How can I help you today?</p>
        {suggestions.length > 0 && (
          <ul className="suggestions" aria-label="Suggested questions">
            {suggestions.map((s) => (
              <li key={s.question}>
                <button className="suggestion-card" onClick={() => onSuggestion(s.question)}>
                  <span>{s.question}</span>
                  <ArrowUpRight size={16} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
