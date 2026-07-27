import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // O dev server do backend (SPEC-016) sobe em 8321; o cliente gerado aponta
    // para lá via VITE_API_BASE_URL. Sem env, usa o mesmo host.
  },
});
