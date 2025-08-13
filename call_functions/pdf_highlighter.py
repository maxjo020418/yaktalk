"""PDF text highlighting tool."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import fitz  # PyMuPDF
from langchain_core.tools import tool

from . import pdf_reader


def _normalize(text: str) -> str:
    """Collapse whitespace to single spaces and strip."""
    return " ".join(text.split())


def highlight_pdf(
    pdf_path: str | Path,
    spans: Iterable[Tuple[int, str]],
) -> str:
    """Highlight given snippets in a PDF.

    Args:
        pdf_path: Path to the source PDF file.
        spans: Iterable of ``(page_number, snippet)`` tuples.

    Returns:
        Path to the highlighted PDF saved under ``data/temp``.
    """
    doc = fitz.open(str(pdf_path))

    for page_number, snippet in spans:
        page = doc[page_number]
        normalized_snippet = _normalize(snippet)
        quads = page.search_for(normalized_snippet, quads=True)

        if not quads:
            try:
                from rapidfuzz import fuzz  # type: ignore
            except Exception:  # pragma: no cover - best effort if not installed
                fuzz = None

            if fuzz is not None:
                page_text = _normalize(page.get_text())
                length = len(normalized_snippet)
                best_score = -1
                best_sub = ""
                for i in range(0, len(page_text) - length + 1):
                    candidate = page_text[i : i + length]
                    score = fuzz.ratio(normalized_snippet, candidate)
                    if score > best_score:
                        best_score = score
                        best_sub = candidate
                if best_sub:
                    quads = page.search_for(best_sub, quads=True)

        for quad in quads:
            page.add_highlight_annot(quad)

    output_dir = Path("data/temp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"highlighted_{Path(pdf_path).name}"
    doc.save(str(output_path))
    doc.close()
    return str(output_path)


@tool
def highlight_snippet(page_number: int, snippet: str) -> str:
    """Highlight text snippet in the currently loaded PDF and return the output path."""
    pdf_path = getattr(pdf_reader._pdf_service.vector_store, "pdf_file_path", None)
    if not pdf_path:
        return "No PDF loaded"
    return highlight_pdf(pdf_path, [(page_number, snippet)])


# Export tools (for consistency with other modules)
tools = [highlight_snippet]
