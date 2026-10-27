import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/auth": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
