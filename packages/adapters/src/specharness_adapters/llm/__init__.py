"""LiteLLM implementation of the LLM port (SPEC-005, ADR-005/ADR-006).

This is where I/O is allowed. The core decides *which* provider and model; this
package knows how to reach it, validate structured output, price the call and
translate its failures — and how to probe a local Ollama.
"""

from .client import LiteLlmClient, Ping, check_connection, client_from_env
from .detect import detect_providers, ollama_responds
from .errors import classify

__all__ = [
    "LiteLlmClient",
    "Ping",
    "classify",
    "client_from_env",
    "detect_providers",
    "ollama_responds",
    "check_connection",
]
