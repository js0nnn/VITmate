/**
 * Persistent, browser-local conversation storage.
 *
 * Conversations are stored in IndexedDB, one record per conversation, so they
 * survive refreshes and browser restarts and two open tabs never overwrite each
 * other's history. Where IndexedDB is unavailable the store falls back to
 * localStorage. Nothing is ever sent to a server.
 */
import type { Conversation } from "../types";
import { readJson, STORAGE_KEYS, writeJson } from "./storage";

export interface ChatStore {
  readonly kind: "indexeddb" | "localStorage";
  loadAll(): Promise<Conversation[]>;
  save(conversation: Conversation): Promise<void>;
  remove(id: string): Promise<void>;
}

const DB_NAME = "vitmate";
const DB_VERSION = 1;
const STORE = "conversations";
const LEGACY_KEY = STORAGE_KEYS.conversations; // v1 format: one localStorage array

export function isConversation(value: unknown): value is Conversation {
  const c = value as Conversation | null;
  return typeof c?.id === "string" && Array.isArray(c?.messages) && typeof c?.updatedAt === "number";
}

function promisify<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) {
        request.result.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("IndexedDB upgrade blocked"));
  });
}

class IndexedDbChatStore implements ChatStore {
  readonly kind = "indexeddb" as const;

  constructor(private readonly db: IDBDatabase) {}

  private run<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
    const transaction = this.db.transaction(STORE, mode);
    return promisify(action(transaction.objectStore(STORE)));
  }

  async loadAll(): Promise<Conversation[]> {
    const rows = await this.run("readonly", (store) => store.getAll());
    return rows.filter(isConversation);
  }

  async save(conversation: Conversation): Promise<void> {
    await this.run("readwrite", (store) => store.put(conversation));
  }

  async remove(id: string): Promise<void> {
    await this.run("readwrite", (store) => store.delete(id));
  }
}

/** Fallback for browsers without IndexedDB (same format as VITmate v1). */
export class LocalStorageChatStore implements ChatStore {
  readonly kind = "localStorage" as const;

  private read(): Conversation[] {
    const stored = readJson<unknown>(LEGACY_KEY, []);
    return Array.isArray(stored) ? stored.filter(isConversation) : [];
  }

  async loadAll(): Promise<Conversation[]> {
    return this.read();
  }

  async save(conversation: Conversation): Promise<void> {
    const others = this.read().filter((c) => c.id !== conversation.id);
    writeJson(LEGACY_KEY, [conversation, ...others]);
  }

  async remove(id: string): Promise<void> {
    writeJson(LEGACY_KEY, this.read().filter((c) => c.id !== id));
  }
}

/** Move conversations saved by VITmate v1 (localStorage) into IndexedDB once. */
async function migrateLegacyConversations(store: ChatStore): Promise<void> {
  const legacy = new LocalStorageChatStore();
  const conversations = await legacy.loadAll();
  if (conversations.length === 0) return;
  const existing = new Set((await store.loadAll()).map((c) => c.id));
  for (const conversation of conversations) {
    if (!existing.has(conversation.id)) await store.save(conversation);
  }
  try {
    localStorage.removeItem(`vitmate:${LEGACY_KEY}`);
  } catch {
    // ignore: the data is already safely in IndexedDB
  }
}

/** Ask the browser not to evict VITmate's storage under disk pressure (best effort). */
function requestPersistentStorage(): void {
  try {
    void navigator.storage?.persist?.().catch(() => undefined);
  } catch {
    // not supported
  }
}

export async function createChatStore(): Promise<ChatStore> {
  if (typeof indexedDB === "undefined") return new LocalStorageChatStore();
  try {
    const store = new IndexedDbChatStore(await openDatabase());
    await migrateLegacyConversations(store);
    requestPersistentStorage();
    return store;
  } catch {
    return new LocalStorageChatStore();
  }
}

/** Notifies other open VITmate tabs that the stored history changed. */
export function createChangeChannel(onChange: () => void): { notify(): void; close(): void } {
  if (typeof BroadcastChannel === "undefined") return { notify: () => undefined, close: () => undefined };
  const channel = new BroadcastChannel("vitmate-conversations");
  channel.onmessage = () => onChange();
  return { notify: () => channel.postMessage("changed"), close: () => channel.close() };
}
