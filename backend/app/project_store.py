from pathlib import Path
import shutil
from uuid import uuid4

from app.docx_service import DocxService
from app.mapper import build_order_mapping
from app.models import BlockStatus, ProjectState, Side, StoredProject, TextBlock


class ProjectStore:
    def __init__(self, data_dir: Path, docx_service: DocxService | None = None) -> None:
        self.data_dir = data_dir
        self.docx_service = docx_service or DocxService()
        self.projects: dict[str, StoredProject] = {}

    def create_project(
        self,
        en_source: Path,
        zh_source: Path,
        en_filename: str,
        zh_filename: str,
    ) -> ProjectState:
        project_id = uuid4().hex
        root = self.data_dir / project_id
        root.mkdir(parents=True, exist_ok=True)
        en_original = root / "original-en.docx"
        zh_original = root / "original-zh.docx"
        shutil.copyfile(en_source, en_original)
        shutil.copyfile(zh_source, zh_original)

        en_blocks = self.docx_service.extract_blocks(en_original, Side.EN)
        zh_blocks = self.docx_service.extract_blocks(zh_original, Side.ZH)
        mappings, warnings = build_order_mapping(en_blocks, zh_blocks)
        state = ProjectState(
            projectId=project_id,
            enFilename=en_filename,
            zhFilename=zh_filename,
            enBlocks=en_blocks,
            zhBlocks=zh_blocks,
            mappings=mappings,
            warnings=warnings,
        )
        self.projects[project_id] = StoredProject(
            state=state,
            root=root,
            en_original=en_original,
            zh_original=zh_original,
        )
        return state

    def get_project(self, project_id: str) -> StoredProject:
        if project_id not in self.projects:
            raise KeyError(project_id)
        return self.projects[project_id]

    def update_block(
        self,
        project_id: str,
        block_id: str,
        text: str,
        status: BlockStatus,
    ) -> TextBlock:
        project = self.get_project(project_id)
        for block in [*project.state.en_blocks, *project.state.zh_blocks]:
            if block.id == block_id:
                block.text = text
                block.status = status
                return block
        raise KeyError(block_id)

    def export_project(self, project_id: str) -> tuple[Path, Path]:
        project = self.get_project(project_id)
        export_dir = project.root / "exports"
        en_output = export_dir / "updated-en.docx"
        zh_output = export_dir / "updated-zh.docx"

        en_replacements = {
            block.path: block.text
            for block in project.state.en_blocks
            if block.status == BlockStatus.MODIFIED
        }
        zh_replacements = {
            block.path: block.text
            for block in project.state.zh_blocks
            if block.status == BlockStatus.MODIFIED
        }
        self.docx_service.export_with_replacements(project.en_original, en_output, en_replacements)
        self.docx_service.export_with_replacements(project.zh_original, zh_output, zh_replacements)
        return en_output, zh_output
