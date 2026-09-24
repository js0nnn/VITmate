/// <reference types="vitest" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      // During development, API calls go to the local FastAPI backend.
      proxy: { "/api": env.VITE_DEV_API_PROXY || "http://127.0.0.1:8000" },
    },
    build: { outDir: "dist", sourcemap: false },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      css: false,
    },
  };
});
