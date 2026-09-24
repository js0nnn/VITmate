import { useCallback, useEffect, useRef, useState } from "react";
import { createChangeChannel, createChatStore, type ChatStore } from "../services/chatStore";
import { readString, STORAGE_KEYS, writeString } from "../services/storage";
import type { ChatContext, Conversation, Message } from "../types";
import { createId, makeTitle, mergeWithStored } from "../utils/conversations";

const EMPTY_CONTEXT: ChatContext = { previous_intent: null, depth: 0 };
const MAX_CONVERSATIONS = 200;

/** Conversation history persisted in the browser (IndexedDB, localStorage fallback). */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const storeRef = useRef<ChatStore | null>(null);
  const savedRef = useRef(new Map<string, Conversation>()); // what the store currently holds
  const channelRef = useRef<ReturnType<typeof createChangeChannel> | null>(null);

  // Load stored history once, then re-sync whenever another tab changes it.
  useEffect(() => {
    let cancelled = false;

    const sync = async (store: ChatStore) => {
      const stored = await store.loadAll();
      if (cancelled) return [];
      const previouslyStored = new Set(savedRef.current.keys());
      savedRef.current = new Map(stored.map((c) => [c.id, c]));
      setConversations((current) => mergeWithStored(current, stored, previouslyStored));
      return stored;
    };

    createChatStore().then(async (store) => {
      if (cancelled) return;
      storeRef.current = store;
      const stored = await sync(store);
      if (cancelled) return;
      const savedActive = readString(STORAGE_KEYS.activeConversation);
      setActiveId((current) => current ?? (stored.some((c) => c.id === savedActive) ? savedActive : null));
      setLoaded(true);
      channelRef.current = createChangeChannel(() => void sync(store));
    });

    return () => {
      cancelled = true;
      channelRef.current?.close();
    };
  }, []);

  // Write only the conversations that changed; empty conversations are never stored.
  useEffect(() => {
    const store = storeRef.current;
    if (!loaded || !store) return;
    const saved = savedRef.current;
    const current = new Map(conversations.filter((c) => c.messages.length > 0).map((c) => [c.id, c]));
    const writes: Promise<void>[] = [];
    for (const [id, conversation] of current) {
      if (saved.get(id) !== conversation) writes.push(store.save(conversation));
    }
    for (const id of saved.keys()) {
      if (!current.has(id)) writes.push(store.remove(id));
    }
    savedRef.current = current;
    if (writes.length) void Promise.all(writes).then(() => channelRef.current?.notify(), () => undefined);
  }, [conversations, loaded]);

  useEffect(() => {
    if (loaded) writeString(STORAGE_KEYS.activeConversation, activeId ?? "");
  }, [activeId, loaded]);

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
      setConversations((list) =>
        [conversation, ...list].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_CONVERSATIONS),
      );
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
    loaded,
    startNewChat,
    selectConversation,
    deleteConversation,
    ensureConversation,
    appendMessage,
    removeMessage,
  };
}
