import { Info, Moon, PanelLeftOpen, SquarePen, Sun } from "lucide-react";
import type { Theme } from "../types";

interface HeaderProps {
  title: string;
  theme: Theme;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onToggleTheme: () => void;
  onNewChat: () => void;
  onOpenAbout: () => void;
}

export function Header({ title, theme, sidebarOpen, onToggleSidebar, onToggleTheme, onNewChat, onOpenAbout }: HeaderProps) {
  const nextTheme = theme === "dark" ? "light" : "dark";
  return (
    <header className="header">
      <div className="header-left">
        {!sidebarOpen && (
          <>
            <button className="icon-button" onClick={onToggleSidebar} aria-label="Open sidebar">
              <PanelLeftOpen size={19} />
            </button>
            <button className="icon-button" onClick={onNewChat} aria-label="New chat">
              <SquarePen size={18} />
            </button>
          </>
        )}
        <h1 className="header-title">{title}</h1>
      </div>
      <div className="header-actions">
        <button
          className="icon-button theme-toggle"
          onClick={onToggleTheme}
          aria-label={`Switch to ${nextTheme} mode`}
          title={`Switch to ${nextTheme} mode`}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button className="pill-button" onClick={onOpenAbout} aria-haspopup="dialog">
          <Info size={16} />
          <span>About</span>
        </button>
      </div>
    </header>
  );
}
