import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // O backend sobe em 8321; em dev o cliente aponta para lá via
    // VITE_API_BASE_URL (web/.env.development). No build de produção a var some e
    // o cliente usa a mesma origem que serve a página (SPEC-028).
  },
});
