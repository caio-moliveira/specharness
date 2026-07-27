/* ADR-014 / SPEC-016 acceptance[5]: todo dado vem do cliente gerado do OpenAPI.
   Esta regra proíbe `fetch` (e axios) fora de src/client — uma chamada à mão
   descola do contrato e não é pega em build. O cliente gerado é a única porta. */
module.exports = {
  root: true,
  env: { browser: true, es2021: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react-hooks"],
  // src/client é gerado (ADR-014) — usa fetch internamente e não é código à mão;
  // fica fora do lint. A regra abaixo cobre TODO o código escrito por humanos.
  ignorePatterns: ["dist", "node_modules", ".eslintrc.cjs", "src/client"],
  rules: {
    "no-restricted-globals": [
      "error",
      { name: "fetch", message: "Use o cliente gerado do OpenAPI (src/client) — ADR-014." },
    ],
    "no-restricted-imports": [
      "error",
      {
        paths: [
          { name: "axios", message: "Use o cliente gerado do OpenAPI (src/client) — ADR-014." },
        ],
      },
    ],
  },
};
