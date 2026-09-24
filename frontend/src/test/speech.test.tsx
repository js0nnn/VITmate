import { act, render, screen } from "@testing-library/react";
import { SpeechSupportBanner } from "../components/SpeechSupportBanner";
import { VoiceInput } from "../components/VoiceInput";
import { FINAL_PAUSE_MS, INTERIM_PAUSE_MS, mergeSegments } from "../hooks/useSpeechRecognition";

/** Continuous-mode stand-in for SpeechRecognition that accumulates results like Chrome. */
class ContinuousRecognition {
  static last: ContinuousRecognition | null = null;
  lang = "";
  continuous = false;
  interimResults = false;
  maxAlternatives = 1;
  onstart: (() => void) | null = null;
  onresult: ((e: unknown) => void) | null = null;
  onerror: ((e: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  stopped = false;
  private results: { isFinal: boolean; 0: { transcript: string } }[] = [];
  constructor() {
    ContinuousRecognition.last = this;
  }
  start() {
    this.onstart?.();
  }
  stop() {
    this.stopped = true;
    // Stopping finalises any pending interim result, then the session ends.
    this.results = this.results.map((r) => ({ ...r, isFinal: true }));
    this.emit();
    this.onend?.();
  }
  abort() {}
  hear(text: string, isFinal: boolean) {
    const last = this.results[this.results.length - 1];
    if (last && !last.isFinal) this.results[this.results.length - 1] = { isFinal, 0: { transcript: text } };
    else this.results.push({ isFinal, 0: { transcript: text } });
    this.emit();
  }
  private emit() {
    this.onresult?.({ resultIndex: 0, results: this.results });
  }
}

function installRecognition() {
  (window as unknown as Record<string, unknown>).SpeechRecognition = ContinuousRecognition;
}

function removeRecognition() {
  const w = window as unknown as Record<string, unknown>;
  delete w.SpeechRecognition;
  delete w.webkitSpeechRecognition;
}

describe("speech pause handling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    installRecognition();
  });
  afterEach(() => {
    vi.useRealTimers();
    removeRecognition();
  });

  it("uses continuous recognition and tolerates a natural pause mid-question", () => {
    const onTranscript = vi.fn();
    render(<VoiceInput disabled={false} onTranscript={onTranscript} onSwitchToText={vi.fn()} />);
    act(() => screen.getByRole("button", { name: /start voice input/i }).click());
    const recognition = ContinuousRecognition.last!;
    expect(recognition.continuous).toBe(true);
    expect(recognition.interimResults).toBe(true);

    act(() => recognition.hear("I want to know about", true));
    act(() => vi.advanceTimersByTime(FINAL_PAUSE_MS - 400)); // a short pause…
    expect(onTranscript).not.toHaveBeenCalled();
    expect(recognition.stopped).toBe(false);

    act(() => recognition.hear("FFCS", false)); // …then the user continues
    act(() => recognition.hear("FFCS registration", true));
    act(() => vi.advanceTimersByTime(FINAL_PAUSE_MS - 100));
    expect(onTranscript).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(200)); // real end of speech
    expect(onTranscript).toHaveBeenCalledTimes(1);
    expect(onTranscript).toHaveBeenCalledWith("I want to know about FFCS registration");
  });

  it("waits longer while the browser still holds an unfinished phrase", () => {
    const onTranscript = vi.fn();
    render(<VoiceInput disabled={false} onTranscript={onTranscript} onSwitchToText={vi.fn()} />);
    act(() => screen.getByRole("button", { name: /start voice input/i }).click());
    const recognition = ContinuousRecognition.last!;

    act(() => recognition.hear("what are the hostel", false));
    act(() => vi.advanceTimersByTime(FINAL_PAUSE_MS + 200));
    expect(onTranscript).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(INTERIM_PAUSE_MS - FINAL_PAUSE_MS));
    expect(onTranscript).toHaveBeenCalledWith("what are the hostel");
  });

  it("the stop button submits immediately", () => {
    const onTranscript = vi.fn();
    render(<VoiceInput disabled={false} onTranscript={onTranscript} onSwitchToText={vi.fn()} />);
    act(() => screen.getByRole("button", { name: /start voice input/i }).click());
    act(() => ContinuousRecognition.last!.hear("tell me about placements", false));
    act(() => screen.getByRole("button", { name: /stop listening/i }).click());
    expect(onTranscript).toHaveBeenCalledWith("tell me about placements");
  });

  it("shows a thinking state while the answer is pending", () => {
    render(<VoiceInput disabled onTranscript={vi.fn()} onSwitchToText={vi.fn()} />);
    expect(screen.getByText("VITmate is thinking…")).toBeInTheDocument();
  });

  it("merges cumulative segments reported by some mobile browsers", () => {
    expect(mergeSegments(["I want", "I want to know", "I want to know about FFCS"])).toBe("I want to know about FFCS");
    expect(mergeSegments(["I want to know about", "FFCS registration"])).toBe("I want to know about FFCS registration");
  });
});

describe("SpeechSupportBanner", () => {
  beforeEach(() => localStorage.clear());
  afterEach(removeRecognition);

  it("is hidden when speech recognition is available", () => {
    installRecognition();
    render(<SpeechSupportBanner />);
    expect(screen.queryByText(/isn't supported in this browser/i)).not.toBeInTheDocument();
  });

  it("appears when the API is missing, explains via Learn more, and stays dismissed", () => {
    removeRecognition();
    const { unmount } = render(<SpeechSupportBanner />);
    expect(screen.getByText("Speech recognition isn't supported in this browser.")).toBeInTheDocument();

    act(() => screen.getByRole("button", { name: /learn more/i }).click());
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent(/built into your web browser/i);
    expect(dialog).toHaveTextContent(/Google Chrome/);
    expect(dialog).toHaveTextContent(/Microsoft Edge/);
    act(() => screen.getByRole("button", { name: "Close" }).click());

    act(() => screen.getByRole("button", { name: /dismiss speech support notice/i }).click());
    expect(screen.queryByText(/isn't supported in this browser/i)).not.toBeInTheDocument();
    unmount();

    render(<SpeechSupportBanner />); // e.g. after a reload
    expect(screen.queryByText(/isn't supported in this browser/i)).not.toBeInTheDocument();
  });
});
