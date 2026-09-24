import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { createChatStore } from "../services/chatStore";
import type { Conversation } from "../types";
import { mergeWithStored } from "../utils/conversations";

function conversation(id: string, updatedAt = 1000, text = "What is FFCS?"): Conversation {
  return {
    id,
    title: id,
    createdAt: updatedAt,
    updatedAt,
    messages: [
      { id: `${id}-u`, role: "user", text, createdAt: updatedAt, inputMode: "voice" },
      {
        id: `${id}-a`,
        role: "assistant",
        text: "FFCS is …",
        createdAt: updatedAt,
        meta: { intent: "ffcs", confidence: 0.91, isFallback: false, sources: ["https://vit.ac.in/academics/ffcs"], timeSensitive: false },
      },
    ],
    context: { previous_intent: "ffcs", depth: 0 },
  };
}

beforeEach(() => {
  globalThis.indexedDB = new IDBFactory(); // a fresh, empty database per test
  localStorage.clear();
});

describe("IndexedDB chat store", () => {
  it("keeps conversations across store instances (like a browser restart)", async () => {
    const first = await createChatStore();
    expect(first.kind).toBe("indexeddb");
    await first.save(conversation("a"));
    await first.save(conversation("b"));

    const reopened = await createChatStore();
    const loaded = await reopened.loadAll();
    expect(loaded.map((c) => c.id).sort()).toEqual(["a", "b"]);
    // intent, confidence, sources and input mode survive the round trip
    const restored = loaded.find((c) => c.id === "a")!;
    expect(restored.messages[1].meta).toMatchObject({ intent: "ffcs", confidence: 0.91 });
    expect(restored.messages[0].inputMode).toBe("voice");
  });

  it("updates and deletes single conversations without touching others", async () => {
    const store = await createChatStore();
    await store.save(conversation("a"));
    await store.save(conversation("b"));
    await store.save(conversation("a", 2000, "updated"));
    await store.remove("b");
    const loaded = await store.loadAll();
    expect(loaded).toHaveLength(1);
    expect(loaded[0].messages[0].text).toBe("updated");
  });

  it("migrates conversations saved by VITmate v1 in localStorage", async () => {
    localStorage.setItem("vitmate:conversations.v1", JSON.stringify([conversation("legacy")]));
    const store = await createChatStore();
    expect((await store.loadAll()).map((c) => c.id)).toEqual(["legacy"]);
    expect(localStorage.getItem("vitmate:conversations.v1")).toBeNull();
  });
});

describe("mergeWithStored", () => {
  it("prefers the newer copy, keeps unsaved local chats and drops ones deleted elsewhere", () => {
    const current = [conversation("newer-here", 3000), conversation("unsaved", 2500), conversation("deleted", 1000)];
    const stored = [conversation("newer-here", 2000), conversation("from-other-tab", 2800)];
    const merged = mergeWithStored(current, stored, new Set(["newer-here", "deleted"]));
    expect(merged.map((c) => c.id)).toEqual(["newer-here", "from-other-tab", "unsaved"]);
    expect(merged[0].updatedAt).toBe(3000);
  });
});
