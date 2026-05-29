from app.docx_service import DocxService
from app.models import BlockKind, Side


def test_extracts_headings_body_paragraphs_and_table_cells(sample_docx):
    service = DocxService()

    blocks = service.extract_blocks(sample_docx, Side.EN)

    assert [block.text for block in blocks] == [
        "Introduction",
        "First body paragraph.",
        "Table cell text.",
    ]
    assert [block.kind for block in blocks] == [
        BlockKind.HEADING,
        BlockKind.PARAGRAPH,
        BlockKind.TABLE_CELL,
    ]
    assert blocks[0].id == "en-00000"
    assert blocks[2].path == "table:0:row:0:cell:0:p:0"
