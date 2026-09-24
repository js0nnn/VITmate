import { useCallback, useEffect, useState } from "react";
import { readString, STORAGE_KEYS, writeString } from "../services/storage";
import type { Theme } from "../types";

function initialTheme(): Theme {
  const saved = readString(STORAGE_KEYS.theme);
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Light/dark theme persisted in localStorage; defaults to the system preference. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      writeString(STORAGE_KEYS.theme, next);
      return next;
    });
  }, []);

  return { theme, toggleTheme };
}
