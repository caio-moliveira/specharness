"""Minimal stdlib .docx export (SPEC-015)."""

from __future__ import annotations

import zipfile

from specharness_adapters.report import write_docx


def test_docx_is_a_valid_zip_with_the_three_parts(tmp_path):
    path = write_docx(["# Título", "linha 1", "linha 2"], tmp_path / "r.docx")

    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= names
        document = zf.read("word/document.xml").decode("utf-8")

    assert "linha 1" in document and "linha 2" in document
    assert document.count("<w:p>") == 3  # one paragraph per line


def test_docx_escapes_xml_special_characters(tmp_path):
    path = write_docx(["a < b & c > d"], tmp_path / "r.docx")
    with zipfile.ZipFile(path) as zf:
        document = zf.read("word/document.xml").decode("utf-8")
    assert "&lt;" in document and "&amp;" in document and "&gt;" in document
    assert "a < b" not in document  # the raw text was escaped
