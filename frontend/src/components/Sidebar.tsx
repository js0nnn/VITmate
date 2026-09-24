import { useState } from "react";
import { Check, MessageSquare, PanelLeftClose, Plus, Trash2, X } from "lucide-react";
import type { Conversation } from "../types";
import { groupConversations } from "../utils/conversations";
import { LogoMark, Wordmark } from "./Logo";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  open: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function Sidebar({ conversations, activeId, open, onClose, onNewChat, onSelect, onDelete }: SidebarProps) {
  const groups = groupConversations(conversations.filter((c) => c.messages.length > 0));

  return (
    <>
      <div className={`sidebar-backdrop ${open ? "is-visible" : ""}`} onClick={onClose} aria-hidden="true" />
      <aside className={`sidebar ${open ? "is-open" : ""}`} aria-label="Conversation history">
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <LogoMark size={28} />
            <Wordmark />
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close sidebar">
            <PanelLeftClose size={18} />
          </button>
        </div>

        <button className="new-chat-button" onClick={onNewChat}>
          <Plus size={18} />
          New Chat
        </button>

        <nav className="history" aria-label="Previous conversations">
          {groups.length === 0 && <p className="history-empty">Your conversations will appear here.</p>}
          {groups.map((group) => (
            <section key={group.label} className="history-group">
              <h2 className="history-label">{group.label}</h2>
              <ul>
                {group.conversations.map((conversation) => (
                  <ConversationItem
                    key={conversation.id}
                    conversation={conversation}
                    active={conversation.id === activeId}
                    onSelect={onSelect}
                    onDelete={onDelete}
                  />
                ))}
              </ul>
            </section>
          ))}
        </nav>

        <p
          className="sidebar-footer"
          title="Stored in this browser's local database (IndexedDB). Private windows and clearing site data remove them."
        >
          Chats are saved on this device and never uploaded.
        </p>
      </aside>
    </>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  active: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

function ConversationItem({ conversation, active, onSelect, onDelete }: ConversationItemProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <li className={`history-item ${active ? "is-active" : ""}`}>
      <button
        className="history-select"
        onClick={() => onSelect(conversation.id)}
        aria-current={active ? "page" : undefined}
        title={conversation.title}
      >
        <MessageSquare size={15} aria-hidden="true" />
        <span className="history-title">{conversation.title}</span>
      </button>
      {confirming ? (
        <span className="history-confirm">
          <button className="icon-button danger" onClick={() => onDelete(conversation.id)} aria-label={`Confirm delete "${conversation.title}"`}>
            <Check size={15} />
          </button>
          <button className="icon-button" onClick={() => setConfirming(false)} aria-label="Cancel delete">
            <X size={15} />
          </button>
        </span>
      ) : (
        <button className="icon-button history-delete" onClick={() => setConfirming(true)} aria-label={`Delete "${conversation.title}"`}>
          <Trash2 size={15} />
        </button>
      )}
    </li>
  );
}
