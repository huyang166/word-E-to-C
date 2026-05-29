from app.mapper import build_order_mapping
from app.models import BlockKind, Side, TextBlock


def block(side: Side, index: int, text: str) -> TextBlock:
    return TextBlock(
        id=f"{side.value}-{index:05d}",
        side=side,
        kind=BlockKind.PARAGRAPH,
        index=index,
        text=text,
        path=f"p:{index}",
    )


def test_builds_order_based_mapping():
    en_blocks = [block(Side.EN, 0, "A"), block(Side.EN, 1, "B")]
    zh_blocks = [block(Side.ZH, 0, "甲"), block(Side.ZH, 1, "乙")]

    mappings, warnings = build_order_mapping(en_blocks, zh_blocks)

    assert warnings == []
    assert [item.en_id for item in mappings] == ["en-00000", "en-00001"]
    assert [item.zh_id for item in mappings] == ["zh-00000", "zh-00001"]
    assert en_blocks[0].mapped_id == "zh-00000"
    assert zh_blocks[1].mapped_id == "en-00001"


def test_warns_and_marks_extra_blocks_unmapped():
    en_blocks = [block(Side.EN, 0, "A"), block(Side.EN, 1, "B")]
    zh_blocks = [block(Side.ZH, 0, "甲")]

    mappings, warnings = build_order_mapping(en_blocks, zh_blocks)

    assert len(mappings) == 2
    assert mappings[0].mapped is True
    assert mappings[1].mapped is False
    assert warnings == ["两份文档段落数量不一致，系统已按顺序建立可用映射。"]
