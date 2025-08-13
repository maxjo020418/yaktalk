"""PDF text highlighting tool."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Tuple
import re

import fitz  # PyMuPDF
from langchain_core.tools import tool

from . import pdf_reader


def _normalize(text: str) -> str:
    """Normalize text for comparison.

    Lowercase, remove punctuation, collapse internal whitespace and strip.
    This makes matching snippets against the PDF text more robust.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text)#.strip()


def _normalize_for_pdf_search(text: str) -> str:
    """Normalize text specifically for PDF search, handling line breaks.
    
    PDFs often have line breaks that get removed during text extraction,
    causing words to be concatenated. This function handles that case.
    """
    text = text.lower()
    # Remove punctuation but keep spaces
    text = re.sub(r"[^\w\s]", "", text)
    # Replace multiple whitespace (including line breaks) with single space
    text = re.sub(r"\s+", " ", text)
    # Also create a version without any spaces for fallback matching
    return text#.strip()


def highlight_pdf(
    pdf_path: str | Path,
    spans: Iterable[Tuple[int, str]],
) -> str:
    """Highlight given snippets in a PDF.

    Args:
        pdf_path: Path to the source PDF file.
        spans: Iterable of ``(page_number, snippet)`` tuples.

    Returns:
        Path to the highlighted PDF saved under ``data/temp``, or error message if highlights couldn't be added.
    """
    doc = fitz.open(str(pdf_path))
    highlights_added = False

    print(f"doc page count: {doc.page_count}")
    print(f"Highlighting snippets in PDF: {spans}")
    for page_number, snippet in spans:
        page = doc.load_page(page_number)
        
        # Normalize snippet for comparison
        normalized_snippet = _normalize_for_pdf_search(snippet)
        
        # Try different search strategies
        quads = []
        
        # 1. Direct search with original text
        quads = page.search_for(snippet, quads=True)
        print(f"Direct search result: {quads}")
        
        # 2. If direct search fails, try with normalized spacing (handle line breaks)
        if not quads:
            # Strategy A: Try searching for text with line breaks removed (common PDF issue)
            snippet_no_breaks = re.sub(r'\s+', '', snippet)
            page_text_raw = page.get_text()
            page_text_no_breaks = re.sub(r'\s+', '', page_text_raw)
            
            if snippet_no_breaks in page_text_no_breaks:
                print("Found text match without spaces - trying different spacing variants...")
                
                # Try with spaces normalized to single space
                quads = page.search_for(snippet.replace('\n', ' '), quads=True)
                print(f"Line-break to space search result: {quads}")
                
                # Try with all multi-spaces reduced to single space
                if not quads:
                    snippet_single_space = re.sub(r'\s+', ' ', snippet)
                    quads = page.search_for(snippet_single_space, quads=True)
                    print(f"Single-space normalized search result: {quads}")
                
                # Try without any spaces (match the PDF's extracted format)
                if not quads:
                    quads = page.search_for(snippet_no_breaks, quads=True)
                    print(f"No-spaces search result: {quads}")
                    
                # If we found the text without spaces in PDF, try word-by-word highlighting
                if not quads:
                    print("Attempting word-by-word matching for spacing issues...")
                    words = page.get_text("words")
                    if words:
                        snippet_words = snippet_no_breaks
                        # Find approximate location using the no-space version
                        page_text_lower = page_text_no_breaks.lower()
                        snippet_lower = snippet_no_breaks.lower()
                        
                        if snippet_lower in page_text_lower:
                            start_idx = page_text_lower.find(snippet_lower)
                            end_idx = start_idx + len(snippet_lower)
                            
                            # Try to find words that cover this text range
                            covering_words = []
                            current_text = ""
                            for word in words:
                                word_text = re.sub(r'[^\w]', '', word[4].lower())
                                current_text += word_text
                                covering_words.append(word)
                                
                                if len(current_text) >= len(snippet_lower):
                                    if snippet_lower in current_text:
                                        # Found the words - create highlight
                                        x0 = min(w[0] for w in covering_words)
                                        y0 = min(w[1] for w in covering_words)
                                        x1 = max(w[2] for w in covering_words)
                                        y1 = max(w[3] for w in covering_words)
                                        page.add_highlight_annot(fitz.Rect(x0, y0, x1, y1))
                                        highlights_added = True
                                        print("Successfully highlighted using word-by-word matching!")
                                        break
                                    
                                    # Remove first word if text is getting too long
                                    if len(covering_words) > 20:  # Prevent infinite loop
                                        covering_words.pop(0)
                                        first_word_text = re.sub(r'[^\w]', '', covering_words[0][4].lower()) if covering_words else ""
                                        current_text = current_text[len(first_word_text):]
                            
                            if highlights_added:
                                continue  # Skip to next snippet since we found and highlighted this one
        
        # 3. Fallback to existing fuzzy search logic
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

                # If fuzzy search fails to locate any quads, try word-level matching
                if not quads and best_sub:
                    words = page.get_text("words")
                    if words:
                        normalized_words = [(_normalize(w[4]), w) for w in words]
                        tokens = [nw[0] for nw in normalized_words]
                        snippet_tokens = normalized_snippet.split()
                        m = len(snippet_tokens)
                        matches_found = False
                        for i in range(len(tokens) - m + 1):
                            if tokens[i : i + m] == snippet_tokens:
                                matches_found = True
                                sequence = [normalized_words[j][1] for j in range(i, i + m)]
                                x0 = min(w[0] for w in sequence)
                                y0 = min(w[1] for w in sequence)
                                x1 = max(w[2] for w in sequence)
                                y1 = max(w[3] for w in sequence)
                                page.add_highlight_annot(fitz.Rect(x0, y0, x1, y1))
                                highlights_added = True
                        if matches_found:
                            continue

        for quad in quads:
            page.add_highlight_annot(quad)
            highlights_added = True
    
    if not highlights_added:
        return f"ERROR: Could not find the requested text to highlight in the PDF. Please verify the text exists and try again with exact text from the PDF."

    output_dir = Path("data/temp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"highlighted_{Path(pdf_path).name}"
    doc.save(str(output_path))
    doc.close()
    return str(output_path)


@tool
def highlight_snippet(page_number: int, snippet: str) -> str:
    """Highlights text snippet in the currently loaded PDF."""
    pdf_path = getattr(pdf_reader._pdf_service.vector_store, "pdf_file_path", None)
    if not pdf_path:
        return "No PDF loaded"
    
    result = highlight_pdf(pdf_path, [(page_number, snippet)])
    
    # Check if it's an error message
    if result.startswith("ERROR:"):
        return result
    
    # Return the full absolute path for proper file handling
    if os.path.exists(result):
        return os.path.abspath(result)
    else:
        return f"Failed to create highlighted PDF at: {result}"


# Export tools (for consistency with other modules)
tools = [highlight_snippet]
