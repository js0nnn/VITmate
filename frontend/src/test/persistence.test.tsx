import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";

const REPLY = {
  reply: "Hostel answer",
  intent: "hostel",
  confidence: 0.93,
  is_fallback: false,
  is_follow_up: false,
  topic: "hostels",
  sources: ["https://vit.ac.in/campuslife/hostels"],
  time_sensitive: false,
  context: { previous_intent: "hostel", depth: 0 },
  suggestions: [],
  latency_ms: 4,
};

beforeEach(() => {
  globalThis.indexedDB = new IDBFactory();
  localStorage.clear();
  window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as unknown as typeof window.matchMedia;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
    Promise.resolve(
      new Response(JSON.stringify(String(input).endsWith("/api/suggestions") ? [] : REPLY), {
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
});

afterEach(() => vi.restoreAllMocks());

it("restores conversations and the open chat after the app is reopened (IndexedDB)", async () => {
  const first = render(<App />);
  await userEvent.type(screen.getByLabelText(/message vitmate/i), "What are the hostel facilities?{Enter}");
  expect(await screen.findByText("Hostel answer")).toBeInTheDocument();
  await new Promise((resolve) => setTimeout(resolve, 50)); // let the IndexedDB write finish
  first.unmount();

  render(<App />); // simulates closing and reopening the site
  const history = await screen.findByRole("navigation", { name: /previous conversations/i });
  expect(await within(history).findByRole("button", { name: "What are the hostel facilities" })).toBeInTheDocument();
  expect(await screen.findByText("Hostel answer")).toBeInTheDocument(); // the active chat is reopened
  expect(screen.getByText("hostel")).toBeInTheDocument(); // intent is preserved
});
