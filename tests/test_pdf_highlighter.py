from pathlib import Path

import fitz

# Import the helper directly rather than the LangChain tool wrapper
from call_functions.pdf_highlighter import _highlight_pdf_file


def test_highlight_pdf_creates_output_and_annotation(tmp_path):
    # Use a sample PDF that contains the Korean snippet we're searching for
    pdf_path = Path('data/kb-sample1.pdf')
    snippet = '이 계약은 구매기업이 은행의'
    # Call the helper with the PDF path and spans and ensure it returns
    # a valid file path to the newly highlighted PDF.
    output_path = Path(_highlight_pdf_file(pdf_path, [(0, snippet)]))
    assert output_path.exists()

    with fitz.open(str(output_path)) as doc:
        page = doc[0]
        annots = list(page.annots() or [])
        assert len(annots) > 0
