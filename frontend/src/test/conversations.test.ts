import { groupConversations, makeTitle } from "../utils/conversations";
import type { Conversation } from "../types";

const DAY = 24 * 60 * 60 * 1000;

function conversation(id: string, updatedAt: number): Conversation {
  return {
    id,
    title: id,
    createdAt: updatedAt,
    updatedAt,
    messages: [{ id: "m", role: "user", text: "hi", createdAt: updatedAt }],
    context: { previous_intent: null, depth: 0 },
  };
}

describe("makeTitle", () => {
  it("strips fillers and trailing punctuation", () => {
    expect(makeTitle("uh, what are the hostel facilities?")).toBe("What are the hostel facilities");
    expect(makeTitle("Hey VITmate, what is FFCS?")).toBe("What is FFCS");
  });

  it("truncates long titles", () => {
    const title = makeTitle("Tell me absolutely everything about the scholarships available for students at VIT");
    expect(title.length).toBeLessThanOrEqual(42);
    expect(title.endsWith("…")).toBe(true);
  });
});

describe("groupConversations", () => {
  it("groups by recency, newest first", () => {
    const now = new Date(2026, 8, 24, 15, 0).getTime();
    const groups = groupConversations(
      [
        conversation("older", now - 30 * DAY),
        conversation("today-early", now - 60 * 60 * 1000),
        conversation("yesterday", now - DAY),
        conversation("week", now - 4 * DAY),
        conversation("today-late", now),
      ],
      now,
    );
    expect(groups.map((g) => g.label)).toEqual(["Today", "Yesterday", "Previous 7 Days", "Older"]);
    expect(groups[0].conversations.map((c) => c.id)).toEqual(["today-late", "today-early"]);
  });
});
