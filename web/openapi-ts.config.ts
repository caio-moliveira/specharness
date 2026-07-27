import { defineConfig } from "@hey-api/openapi-ts";

// ADR-014: o cliente TypeScript é gerado do OpenAPI do FastAPI. O cliente
// "legacy/fetch" é autocontido (usa fetch, sem dependência de runtime), então
// todo dado do web passa por ele — nada de fetch/axios escrito à mão.
export default defineConfig({
  input: "./openapi.json",
  output: {
    path: "./src/client",
    format: false,
    lint: false,
  },
  plugins: ["legacy/fetch"],
});
