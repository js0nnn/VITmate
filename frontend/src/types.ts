export type InputMode = "text" | "voice";
export type Theme = "light" | "dark";

/** Conversation state echoed back to the stateless backend. */
export interface ChatContext {
  previous_intent: string | null;
  depth: number;
}

export interface AssistantMeta {
  intent: string;
  confidence: number;
  isFallback: boolean;
  sources: string[];
  timeSensitive: boolean;
  /** Topics offered when VITmate was unsure what the user meant. */
  suggestions?: Suggestion[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: number;
  inputMode?: InputMode;
  meta?: AssistantMeta;
  /** Set on assistant messages that report a failed request. */
  failedText?: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
  context: ChatContext;
}

export interface ChatResponse {
  reply: string;
  intent: string;
  confidence: number;
  is_fallback: boolean;
  is_follow_up: boolean;
  topic: string | null;
  sources: string[];
  time_sensitive: boolean;
  context: ChatContext;
  suggestions: Suggestion[];
  latency_ms: number;
}

export interface Suggestion {
  intent: string;
  question: string;
}
