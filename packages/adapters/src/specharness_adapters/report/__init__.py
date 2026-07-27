"""Adapters for the sprint report (SPEC-015).

The report content and its read-before-cite guard are pure core; here live the
two I/O pieces: the minimal stdlib .docx writer and the LLM narrative loop.
"""

from .docx import write_docx
from .narrative import NarrativeResult, generate_narrative

__all__ = ["NarrativeResult", "generate_narrative", "write_docx"]
