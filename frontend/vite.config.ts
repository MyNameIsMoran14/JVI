import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev setup: Vite proxies /api to the local FastAPI container so the Mini App can be served
// through a single HTTPS origin (cloudflared tunnel today, Caddy on the real VPS later) —
// the backend itself is never exposed directly. allowedHosts is open because the tunnel
// hostname is random per run (trycloudflare.com quick tunnels); tighten this once there's
// a fixed domain.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5327,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
