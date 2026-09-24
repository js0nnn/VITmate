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

/**
 * Merge the in-memory history with what is in storage (e.g. after another tab
 * changed it). Per conversation the most recently updated copy wins; local
 * conversations not yet written are kept, and ones deleted elsewhere
 * (previously stored, now missing) are dropped.
 */
export function mergeWithStored(
  current: Conversation[],
  stored: Conversation[],
  previouslyStoredIds: ReadonlySet<string>,
): Conversation[] {
  const merged = new Map(stored.map((c) => [c.id, c]));
  for (const conversation of current) {
    const storedCopy = merged.get(conversation.id);
    if (storedCopy) {
      if (conversation.updatedAt > storedCopy.updatedAt) merged.set(conversation.id, conversation);
    } else if (!previouslyStoredIds.has(conversation.id)) {
      merged.set(conversation.id, conversation);
    }
  }
  return [...merged.values()].sort((a, b) => b.updatedAt - a.updatedAt);
}
