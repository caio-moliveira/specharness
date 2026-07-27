"""Local git CLI adapter (SPEC-006, ADR-011).

This is where subprocess I/O over `git` is allowed. The core decides *what* a
commit is; this package knows how to read it from a checkout.
"""

from .local import LocalGitCommitReader

__all__ = ["LocalGitCommitReader"]
