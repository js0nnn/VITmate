import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

const FFCS_REPLY = {
  reply: "**FFCS** is VIT's Fully Flexible Credit System.",
  intent: "ffcs",
  confidence: 0.97,
  is_fallback: false,
  is_follow_up: false,
  topic: "FFCS",
  sources: ["https://vit.ac.in/academics/ffcs"],
  time_sensitive: false,
  context: { previous_intent: "ffcs", depth: 0 },
  latency_ms: 5,
};

function mockBackend(chat: (body: { message: string; context: unknown }) => Promise<Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.endsWith("/api/suggestions")) return jsonResponse([{ intent: "ffcs", question: "What is FFCS?" }]);
    if (url.endsWith("/api/chat")) return chat(JSON.parse(String(init?.body)));
    return Promise.reject(new Error(`unexpected ${url}`));
  });
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.dataset.theme = "light";
  window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as unknown as typeof window.matchMedia;
});

afterEach(() => vi.restoreAllMocks());

describe("App", () => {
  it("sends a typed message, shows the reply and persists the conversation", async () => {
    const fetchMock = mockBackend(() => jsonResponse(FFCS_REPLY));
    render(<App />);

    await userEvent.type(screen.getByLabelText(/message vitmate/i), "What is FFCS?{Enter}");

    const log = await screen.findByRole("log");
    expect(within(log).getByText("What is FFCS?")).toBeInTheDocument();
    expect(await within(log).findByText(/Fully Flexible Credit System/)).toBeInTheDocument();
    expect(within(log).getByText("ffcs")).toBeInTheDocument(); // predicted intent chip

    const stored = JSON.parse(localStorage.getItem("vitmate:conversations.v1") ?? "[]");
    expect(stored).toHaveLength(1);
    expect(stored[0].title).toBe("What is FFCS");
    expect(stored[0].context).toEqual({ previous_intent: "ffcs", depth: 0 });
    const chatCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/api/chat"));
    expect(JSON.parse(String(chatCall?.[1]?.body))).toMatchObject({ message: "What is FFCS?", input_mode: "text" });
  });

  it("sends the conversation context with follow-up questions", async () => {
    const bodies: { context: unknown }[] = [];
    mockBackend((body) => {
      bodies.push(body);
      return jsonResponse(FFCS_REPLY);
    });
    render(<App />);
    const input = screen.getByLabelText(/message vitmate/i);
    await userEvent.type(input, "What is FFCS?{Enter}");
    await screen.findByText(/Fully Flexible Credit System/);
    await userEvent.type(input, "How does it work?{Enter}");
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1].context).toEqual({ previous_intent: "ffcs", depth: 0 });
  });

  it("shows a friendly error when the backend is unreachable", async () => {
    mockBackend(() => Promise.reject(new TypeError("Failed to fetch")));
    render(<App />);
    await userEvent.type(screen.getByLabelText(/message vitmate/i), "What is FFCS?{Enter}");
    expect(await screen.findByText("Unable to connect to the assistant. Please try again.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("starts a new chat, switches back and deletes conversations", async () => {
    mockBackend(() => jsonResponse(FFCS_REPLY));
    render(<App />);
    await userEvent.type(screen.getByLabelText(/message vitmate/i), "What is FFCS?{Enter}");
    await screen.findByText(/Fully Flexible Credit System/);

    await userEvent.click(screen.getByRole("button", { name: /^new chat$/i }));
    expect(screen.getByText("Hi! I'm VITmate 👋")).toBeInTheDocument();

    const history = screen.getByRole("navigation", { name: /previous conversations/i });
    await userEvent.click(within(history).getByRole("button", { name: "What is FFCS" }));
    expect(await screen.findByText(/Fully Flexible Credit System/)).toBeInTheDocument();

    await userEvent.click(within(history).getByRole("button", { name: /delete "What is FFCS"/i }));
    await userEvent.click(within(history).getByRole("button", { name: /confirm delete/i }));
    expect(within(history).queryByText("What is FFCS")).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("vitmate:conversations.v1") ?? "[]")).toHaveLength(0);
  });

  it("toggles and remembers the theme", async () => {
    mockBackend(() => jsonResponse(FFCS_REPLY));
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /switch to (dark|light) mode/i }));
    const theme = document.documentElement.dataset.theme;
    expect(localStorage.getItem("vitmate:theme")).toBe(theme);
  });

  it("opens the About dialog", async () => {
    mockBackend(() => jsonResponse(FFCS_REPLY));
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /about/i }));
    expect(screen.getByRole("dialog")).toHaveTextContent("B. Jaison Edward");
  });

  it("shows suggestions from the backend on a new chat", async () => {
    mockBackend(() => jsonResponse(FFCS_REPLY));
    render(<App />);
    expect(await screen.findByRole("button", { name: /what is ffcs\?/i })).toBeInTheDocument();
  });

  it("remembers the selected input mode", async () => {
    mockBackend(() => jsonResponse(FFCS_REPLY));
    render(<App />);
    await userEvent.click(screen.getByRole("radio", { name: /speak/i }));
    expect(localStorage.getItem("vitmate:inputMode")).toBe("voice");
  });
});
