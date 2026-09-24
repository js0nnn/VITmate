import { useCallback, useEffect, useState } from "react";
import { readJson, readString, STORAGE_KEYS, writeJson, writeString } from "../services/storage";
import type { ChatContext, Conversation, Message } from "../types";
import { createId, makeTitle } from "../utils/conversations";

const EMPTY_CONTEXT: ChatContext = { previous_intent: null, depth: 0 };
const MAX_CONVERSATIONS = 100;

function loadConversations(): Conversation[] {
  const stored = readJson<unknown>(STORAGE_KEYS.conversations, []);
  if (!Array.isArray(stored)) return [];
  return stored.filter(
    (c): c is Conversation => typeof c?.id === "string" && Array.isArray(c?.messages),
  );
}

/** Conversation history kept in the browser's localStorage. */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(() => {
    const saved = readString(STORAGE_KEYS.activeConversation);
    return saved && loadConversations().some((c) => c.id === saved) ? saved : null;
  });

  useEffect(() => {
    // Empty conversations are never persisted.
    writeJson(STORAGE_KEYS.conversations, conversations.filter((c) => c.messages.length > 0));
  }, [conversations]);

  useEffect(() => {
    writeString(STORAGE_KEYS.activeConversation, activeId ?? "");
  }, [activeId]);

  const active = conversations.find((c) => c.id === activeId) ?? null;

  const startNewChat = useCallback(() => setActiveId(null), []);

  const selectConversation = useCallback((id: string) => setActiveId(id), []);

  const deleteConversation = useCallback((id: string) => {
    setConversations((list) => list.filter((c) => c.id !== id));
    setActiveId((current) => (current === id ? null : current));
  }, []);

  /** Create a conversation for the first message of a new chat; returns its id. */
  const ensureConversation = useCallback(
    (firstMessage: string): string => {
      if (activeId && conversations.some((c) => c.id === activeId)) return activeId;
      const now = Date.now();
      const conversation: Conversation = {
        id: createId(),
        title: makeTitle(firstMessage),
        createdAt: now,
        updatedAt: now,
        messages: [],
        context: EMPTY_CONTEXT,
      };
      setConversations((list) => [conversation, ...list].slice(0, MAX_CONVERSATIONS));
      setActiveId(conversation.id);
      return conversation.id;
    },
    [activeId, conversations],
  );

  const appendMessage = useCallback((conversationId: string, message: Message, context?: ChatContext) => {
    setConversations((list) =>
      list.map((c) =>
        c.id === conversationId
          ? { ...c, messages: [...c.messages, message], updatedAt: Date.now(), context: context ?? c.context }
          : c,
      ),
    );
  }, []);

  const removeMessage = useCallback((conversationId: string, messageId: string) => {
    setConversations((list) =>
      list.map((c) => (c.id === conversationId ? { ...c, messages: c.messages.filter((m) => m.id !== messageId) } : c)),
    );
  }, []);

  return {
    conversations,
    active,
    activeId,
    startNewChat,
    selectConversation,
    deleteConversation,
    ensureConversation,
    appendMessage,
    removeMessage,
  };
}
