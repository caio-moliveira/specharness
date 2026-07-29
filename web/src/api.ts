// Configura o cliente gerado do OpenAPI (ADR-014). Sem VITE_API_BASE_URL, a base
// é a MESMA ORIGEM que serve a página (SPEC-028): o `specharness up` embute o
// dashboard e a API na mesma porta, então requisições relativas acham a API em
// qualquer host/porta. O dev com Vite em porta separada seta a var explicitamente
// (web/.env.development).
import { OpenAPI } from "./client";

OpenAPI.BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export * from "./client";
