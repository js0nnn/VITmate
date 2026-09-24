import { useCallback, useEffect, useState } from "react";
import { AboutModal } from "./components/AboutModal";
import { ChatView } from "./components/ChatView";
import { Composer } from "./components/Composer";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { SpeechSupportBanner } from "./components/SpeechSupportBanner";
import { useConversations } from "./hooks/useConversations";
import { useTheme } from "./hooks/useTheme";
import { ApiError, CONNECTION_ERROR, fetchSuggestions, sendMessage } from "./services/api";
import { readString, STORAGE_KEYS, writeString } from "./services/storage";
import type { InputMode, Message, Suggestion } from "./types";
import { createId } from "./utils/conversations";

const MAX_MESSAGE_LENGTH = 500;
/**
 * The model answers in a few milliseconds; keeping the "thinking" indicator up
 * for a moment avoids a jarring flash. Slower responses are never delayed further.
 */
const MIN_THINKING_MS = 450;

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));
const DESKTOP_QUERY = "(min-width: 900px)";

function isDesktop(): boolean {
  return window.matchMedia?.(DESKTOP_QUERY).matches ?? true;
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const chats = useConversations();
  const [mode, setMode] = useState<InputMode>(() => (readString(STORAGE_KEYS.inputMode) === "voice" ? "voice" : "text"));
  const [sidebarOpen, setSidebarOpen] = useState(isDesktop);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);

  useEffect(() => {
    fetchSuggestions().then(setSuggestions).catch(() => setSuggestions([]));
  }, []);

  const changeMode = useCallback((next: InputMode) => {
    setMode(next);
    writeString(STORAGE_KEYS.inputMode, next);
  }, []);

  const closeSidebarOnMobile = () => {
    if (!isDesktop()) setSidebarOpen(false);
  };

  const setPending = (id: string, pending: boolean) =>
    setPendingIds((current) => {
      const next = new Set(current);
      if (pending) next.add(id);
      else next.delete(id);
      return next;
    });

  const handleSend = async (text: string, inputMode: InputMode) => {
    const message = text.trim().slice(0, MAX_MESSAGE_LENGTH);
    if (!message) return;
    const conversationId = chats.ensureConversation(message);
    if (pendingIds.has(conversationId)) return;
    const context = chats.active?.id === conversationId ? chats.active.context : { previous_intent: null, depth: 0 };

    chats.appendMessage(conversationId, { id: createId(), role: "user", text: message, createdAt: Date.now(), inputMode });
    setPending(conversationId, true);
    try {
      const [response] = await Promise.all([sendMessage(message, context, inputMode), wait(MIN_THINKING_MS)]);
      chats.appendMessage(
        conversationId,
        {
          id: createId(),
          role: "assistant",
          text: response.reply,
          createdAt: Date.now(),
          meta: {
            intent: response.intent,
            confidence: response.confidence,
            isFallback: response.is_fallback,
            sources: response.sources,
            timeSensitive: response.time_sensitive,
            suggestions: response.suggestions ?? [],
          },
        },
        response.context,
      );
    } catch (error) {
      chats.appendMessage(conversationId, {
        id: createId(),
        role: "assistant",
        text: error instanceof ApiError ? error.message : CONNECTION_ERROR,
        createdAt: Date.now(),
        failedText: message,
      });
    } finally {
      setPending(conversationId, false);
    }
  };

  const handleRetry = (failed: Message) => {
    if (!chats.activeId || !failed.failedText) return;
    // Drop the error bubble and the user message it belongs to, then resend.
    const messages = chats.active?.messages ?? [];
    const index = messages.findIndex((m) => m.id === failed.id);
    const userMessage = index > 0 ? messages[index - 1] : undefined;
    chats.removeMessage(chats.activeId, failed.id);
    if (userMessage?.role === "user") chats.removeMessage(chats.activeId, userMessage.id);
    void handleSend(failed.failedText, userMessage?.inputMode ?? "text");
  };

  const pending = chats.activeId ? pendingIds.has(chats.activeId) : false;

  return (
    <div className={`app ${sidebarOpen ? "sidebar-open" : ""}`}>
      <Sidebar
        conversations={chats.conversations}
        activeId={chats.activeId}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={() => {
          chats.startNewChat();
          closeSidebarOnMobile();
        }}
        onSelect={(id) => {
          chats.selectConversation(id);
          closeSidebarOnMobile();
        }}
        onDelete={chats.deleteConversation}
      />

      <main className="main">
        <Header
          title={chats.active?.title ?? "New chat"}
          theme={theme}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(true)}
          onToggleTheme={toggleTheme}
          onNewChat={chats.startNewChat}
          onOpenAbout={() => setAboutOpen(true)}
        />
        <SpeechSupportBanner />
        <ChatView
          messages={chats.active?.messages ?? []}
          pending={pending}
          suggestions={suggestions}
          onSuggestion={(question) => void handleSend(question, "text")}
          onRetry={handleRetry}
        />
        <Composer
          mode={mode}
          pending={pending}
          maxLength={MAX_MESSAGE_LENGTH}
          onModeChange={changeMode}
          onSend={(text, inputMode) => void handleSend(text, inputMode)}
        />
      </main>

      <AboutModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </div>
  );
}
