from pathlib import Path

import fitz

from call_functions.pdf_highlighter import _highlight_pdf_file


def test_highlight_pdf_creates_output_and_annotation(tmp_path):
    pdf_path = Path('data/kb-sample1.pdf')
    snippet = '이 계약은 구매기업이 은행의'
    output_path = Path(_highlight_pdf_file(pdf_path, [(0, snippet)]))
    assert output_path.exists()

    with fitz.open(str(output_path)) as doc:
        page = doc[0]
        annots = list(page.annots() or [])
        assert len(annots) > 0
