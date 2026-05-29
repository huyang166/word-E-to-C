from enum import StrEnum
from pathlib import Path

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
    mapped_id: str | None = Field(default=None, alias="mappedId")
    status: BlockStatus = BlockStatus.CLEAN


class MappingPair(BaseModel):
    en_id: str | None = Field(default=None, alias="enId")
    zh_id: str | None = Field(default=None, alias="zhId")
    index: int
    mapped: bool


class ProjectState(BaseModel):
    project_id: str = Field(alias="projectId")
    en_filename: str = Field(alias="enFilename")
    zh_filename: str = Field(alias="zhFilename")
    en_blocks: list[TextBlock] = Field(alias="enBlocks")
    zh_blocks: list[TextBlock] = Field(alias="zhBlocks")
    mappings: list[MappingPair]
    warnings: list[str] = []


class SuggestRequest(BaseModel):
    direction: str
    source_block_id: str = Field(alias="sourceBlockId")
    target_block_id: str = Field(alias="targetBlockId")
    source_text: str = Field(alias="sourceText")
    target_text: str = Field(alias="targetText")


class SuggestResponse(BaseModel):
    suggestion: str


class UpdateBlockRequest(BaseModel):
    text: str
    status: BlockStatus


class ExportResponse(BaseModel):
    en_download_url: str = Field(alias="enDownloadUrl")
    zh_download_url: str = Field(alias="zhDownloadUrl")


class StoredProject(BaseModel):
    state: ProjectState
    root: Path
    en_original: Path
    zh_original: Path
