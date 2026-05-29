from app.models import MappingPair, TextBlock

COUNT_MISMATCH_WARNING = "两份文档段落数量不一致，系统已按顺序建立可用映射。"


def build_order_mapping(
    en_blocks: list[TextBlock],
    zh_blocks: list[TextBlock],
) -> tuple[list[MappingPair], list[str]]:
    mapped_count = min(len(en_blocks), len(zh_blocks))
    max_count = max(len(en_blocks), len(zh_blocks))
    mappings: list[MappingPair] = []

    for index in range(max_count):
        en_block = en_blocks[index] if index < len(en_blocks) else None
        zh_block = zh_blocks[index] if index < len(zh_blocks) else None
        mapped = index < mapped_count

        if en_block and zh_block and mapped:
            en_block.mapped_id = zh_block.id
            zh_block.mapped_id = en_block.id

        mappings.append(
            MappingPair(
                enId=en_block.id if en_block else None,
                zhId=zh_block.id if zh_block else None,
                index=index,
                mapped=mapped,
            )
        )

    warnings = [COUNT_MISMATCH_WARNING] if len(en_blocks) != len(zh_blocks) else []
    return mappings, warnings
