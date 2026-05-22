"""
etl/extract_herd_fy24_guide.py — HD 1.3 one-shot extractor.

Reads ``data/raw/herd/Guide To Herd Data Files FY24.pdf`` via pypdf and
writes a plain-text rendering to ``docs/source_documents/herd_fy24_guide.txt``
so the canonical break definitions (questionnaire codes, field labels,
rename history) are grep-able from the harmonization workflow.

Reproducibility note: this script is part of the deposit. Re-running it
against the same PDF must produce byte-identical output (modulo pypdf
version, which is pinned in pyproject.toml / uv.lock).

Run::

    uv run python -m etl.extract_herd_fy24_guide
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data" / "raw" / "herd" / "Guide To Herd Data Files FY24.pdf"
TXT_PATH = ROOT / "docs" / "source_documents" / "herd_fy24_guide.txt"


def extract() -> int:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Source PDF missing: {PDF_PATH}")

    reader = PdfReader(str(PDF_PATH))
    n_pages = len(reader.pages)

    parts: list[str] = []
    parts.append(f"# Source: {PDF_PATH.name}\n# Pages: {n_pages}\n")
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        parts.append(f"\n\n===== PAGE {i} =====\n\n{text}")

    TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TXT_PATH.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {TXT_PATH} ({n_pages} pages, {TXT_PATH.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(extract())
