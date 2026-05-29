from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field


class Side(StrEnum):
    EN = "en"
    ZH = "zh"


class BlockKind(StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE_CELL = "table_cell"
    UNSUPPORTED = "unsupported"


class BlockStatus(StrEnum):
    CLEAN = "clean"
    EDITED = "edited"
    SUGGESTED = "suggested"
    MODIFIED = "modified"
    ERROR = "error"


class TextBlock(BaseModel):
    id: str
    side: Side
    kind: BlockKind
    index: int
    text: str
    path: str
    mapped_id: Annotated[str | None, Field(alias="mappedId")] = None
    status: BlockStatus = BlockStatus.CLEAN


class MappingPair(BaseModel):
    en_id: Annotated[str | None, Field(alias="enId")] = None
    zh_id: Annotated[str | None, Field(alias="zhId")] = None
    index: int
    mapped: bool


class ProjectState(BaseModel):
    project_id: Annotated[str, Field(alias="projectId")]
    en_filename: Annotated[str, Field(alias="enFilename")]
    zh_filename: Annotated[str, Field(alias="zhFilename")]
    en_blocks: Annotated[list[TextBlock], Field(alias="enBlocks")]
    zh_blocks: Annotated[list[TextBlock], Field(alias="zhBlocks")]
    mappings: list[MappingPair]
    warnings: list[str] = []


class SuggestRequest(BaseModel):
    direction: str
    source_block_id: Annotated[str, Field(alias="sourceBlockId")]
    target_block_id: Annotated[str, Field(alias="targetBlockId")]
    source_text: Annotated[str, Field(alias="sourceText")]
    target_text: Annotated[str, Field(alias="targetText")]


class SuggestResponse(BaseModel):
    suggestion: str


class UpdateBlockRequest(BaseModel):
    text: str
    status: BlockStatus


class ExportResponse(BaseModel):
    en_download_url: Annotated[str, Field(alias="enDownloadUrl")]
    zh_download_url: Annotated[str, Field(alias="zhDownloadUrl")]


class StoredProject(BaseModel):
    state: ProjectState
    root: Path
    en_original: Path
    zh_original: Path
