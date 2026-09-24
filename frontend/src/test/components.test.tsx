import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AboutModal } from "../components/AboutModal";
import { MODAL_EXIT_MS } from "../components/Modal";
import { ModeToggle } from "../components/ModeToggle";
import { VoiceInput } from "../components/VoiceInput";

describe("ModeToggle", () => {
  it("switches between Type and Speak", async () => {
    const onChange = vi.fn();
    render(<ModeToggle mode="text" onChange={onChange} />);
    expect(screen.getByRole("radio", { name: /type/i })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: /speak/i }));
    expect(onChange).toHaveBeenCalledWith("voice");
  });
});

describe("AboutModal", () => {
  it("shows the project credits and closes on Escape", async () => {
    const onClose = vi.fn();
    render(<AboutModal open onClose={onClose} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("Voice-Enabled Deep Learning Chatbot");
    expect(dialog).toHaveTextContent("B. Jaison Edward");
    expect(dialog).toHaveTextContent("Reg. No: 23BAI0094");
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("plays a short exit animation, then unmounts", () => {
    vi.useFakeTimers();
    const { rerender } = render(<AboutModal open onClose={() => undefined} />);
    rerender(<AboutModal open={false} onClose={() => undefined} />);
    const overlay = document.querySelector(".modal-overlay");
    expect(overlay).toHaveClass("is-closing"); // still mounted while animating out…
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); // …but hidden from assistive tech
    act(() => vi.advanceTimersByTime(MODAL_EXIT_MS));
    expect(document.querySelector(".modal-overlay")).toBeNull();
    vi.useRealTimers();
  });

  it("renders nothing when closed", () => {
    render(<AboutModal open={false} onClose={() => undefined} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

/** Minimal controllable stand-in for the browser's SpeechRecognition. */
class MockRecognition {
  static last: MockRecognition | null = null;
  lang = "";
  continuous = false;
  interimResults = false;
  maxAlternatives = 1;
  onstart: (() => void) | null = null;
  onresult: ((e: unknown) => void) | null = null;
  onerror: ((e: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  constructor() {
    MockRecognition.last = this;
  }
  start() {
    this.onstart?.();
  }
  stop() {
    this.onend?.();
  }
  abort() {}
  speak(text: string) {
    this.onresult?.({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: text } }] });
    this.onend?.();
  }
}

describe("VoiceInput", () => {
  afterEach(() => {
    delete (window as unknown as Record<string, unknown>).webkitSpeechRecognition;
  });

  it("explains when the browser does not support speech recognition", () => {
    render(<VoiceInput disabled={false} onTranscript={vi.fn()} onSwitchToText={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent(/isn't supported in this browser/i);
    expect(screen.getByRole("button", { name: /switch to type/i })).toBeInTheDocument();
  });

  it("listens, shows the listening state and sends the transcript", async () => {
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition = MockRecognition;
    const onTranscript = vi.fn();
    render(<VoiceInput disabled={false} onTranscript={onTranscript} onSwitchToText={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /start voice input/i }));
    expect(screen.getByText("Listening…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /stop listening/i })).toBeInTheDocument();

    act(() => MockRecognition.last!.speak("What is FFCS"));
    expect(onTranscript).toHaveBeenCalledWith("What is FFCS");
    expect(screen.getByText("Got it!")).toBeInTheDocument();
  });

  it("explains how to fix a blocked microphone", async () => {
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition = MockRecognition;
    render(<VoiceInput disabled={false} onTranscript={vi.fn()} onSwitchToText={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /start voice input/i }));
    act(() => MockRecognition.last!.onerror?.({ error: "not-allowed" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/allow the microphone/i);
  });

  it("reports silence instead of sending an empty message", async () => {
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition = MockRecognition;
    const onTranscript = vi.fn();
    render(<VoiceInput disabled={false} onTranscript={onTranscript} onSwitchToText={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /start voice input/i }));
    act(() => MockRecognition.last!.stop());
    expect(onTranscript).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/didn't catch anything/i);
  });
});
