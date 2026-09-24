import type { Conversation } from "../types";

export interface ConversationGroup {
  label: string;
  conversations: Conversation[];
}

const DAY_MS = 24 * 60 * 60 * 1000;
const MAX_TITLE_LENGTH = 42;
const FILLER_START = /^(uh+|um+|hey|hi|hello|so|okay|ok|please|vitmate)[,!.\s]+/i;

export function createId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

/** Derive a short sidebar title from the first meaningful user message. */
export function makeTitle(message: string): string {
  let text = message.trim();
  while (FILLER_START.test(text)) text = text.replace(FILLER_START, "");
  text = text.replace(/[?.!]+$/, "").trim() || message.trim();
  const title = text.charAt(0).toUpperCase() + text.slice(1);
  return title.length > MAX_TITLE_LENGTH ? `${title.slice(0, MAX_TITLE_LENGTH - 1).trimEnd()}…` : title;
}

function startOfDay(timestamp: number): number {
  const date = new Date(timestamp);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

/** Group conversations into Today / Yesterday / Previous 7 Days / Older (newest first). */
export function groupConversations(conversations: Conversation[], now = Date.now()): ConversationGroup[] {
  const today = startOfDay(now);
  const buckets: ConversationGroup[] = [
    { label: "Today", conversations: [] },
    { label: "Yesterday", conversations: [] },
    { label: "Previous 7 Days", conversations: [] },
    { label: "Older", conversations: [] },
  ];
  const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);
  for (const conversation of sorted) {
    const day = startOfDay(conversation.updatedAt);
    const index = day >= today ? 0 : day >= today - DAY_MS ? 1 : day >= today - 7 * DAY_MS ? 2 : 3;
    buckets[index].conversations.push(conversation);
  }
  return buckets.filter((group) => group.conversations.length > 0);
}
