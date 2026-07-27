// Configura o cliente gerado do OpenAPI (ADR-014). Base URL do backend de dev
// (SPEC-016 sobe em :8321); em produção, VITE_API_BASE_URL aponta para a API.
import { OpenAPI } from "./client";

OpenAPI.BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8321";

export * from "./client";
