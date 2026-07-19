import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Vite config — supports two modes:
// - dev (vite dev): SPA on 5173, /api/* proxied to local backend on 8000.
// - production build (vite build): static bundle in frontend/dist/, deployed
//   to Vercel (or any static host). API base URL injected at runtime via
//   VITE_API_BASE env var so the same bundle works against any backend.
//
// The legacy build output path (../src/career_compass/gui/static/dist) was
// used by the desktop GUI; it's still preserved when CC_DESKTOP_BUILD=1 is
// set so the pywebview entrypoint continues to work.
const outDir = process.env.CC_DESKTOP_BUILD
  ? "../src/career_compass/gui/static/dist"
  : "dist";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir,
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
