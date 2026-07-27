"""Minimal .docx export, stdlib only (SPEC-015, decisão de readiness).

A .docx is a zip of a few WordprocessingML parts. Rather than take a dependency
for the least-central output (markdown is the default), we write the three parts
Word needs by hand — the same "gerador interno" stance as the trailer and gherkin
parsers. Each report line becomes one paragraph; the content is the markdown text,
so the docx carries the same content as the markdown (cenário "exportação docx").
"""

from __future__ import annotations

import zipfile
from collections.abc import Sequence
from pathlib import Path
from xml.sax.saxutils import escape

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _paragraph(text: str) -> str:
    body = escape(text)
    return f'<w:p><w:r><w:t xml:space="preserve">{body}</w:t></w:r></w:p>'


def _document(lines: Sequence[str]) -> str:
    paragraphs = "".join(_paragraph(line) for line in lines)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{paragraphs}</w:body></w:document>'
    )


def write_docx(lines: Sequence[str], path: str | Path) -> Path:
    """Write `lines` as a minimal, valid .docx at `path` and return the path."""
    target = Path(path)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", _document(lines))
    return target
