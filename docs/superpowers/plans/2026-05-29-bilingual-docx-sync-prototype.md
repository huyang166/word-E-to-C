# Bilingual DOCX Sync Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Chinese-language web prototype that uploads paired English/Chinese DOCX manuscripts, maps editable text blocks by order, generates bidirectional AI sync suggestions, confirms paragraph-level write-back, and exports updated DOCX files.

**Architecture:** Use a FastAPI backend for upload, DOCX parsing, project state, model calls, and DOCX export. Use a React/Vite frontend for the side-by-side Simplified Chinese editing workflow. Keep DOCX originals as the base files and apply confirmed replacements only during export.

**Tech Stack:** Python 3.11+, FastAPI, python-docx, lxml, OpenAI-compatible HTTP API, pytest, React, TypeScript, Vite, Vitest, Testing Library.

---

## File Structure

Create this structure:

```text
backend/
  requirements.txt
  pytest.ini
  app/
    __init__.py
    ai_client.py
    config.py
    docx_service.py
    main.py
    mapper.py
    models.py
    project_store.py
  tests/
    conftest.py
    test_ai_client.py
    test_api.py
    test_docx_service.py
    test_mapper.py
frontend/
  index.html
  package.json
  tsconfig.json
  tsconfig.node.json
  vite.config.ts
  src/
    App.css
    App.test.tsx
    App.tsx
    api.ts
    main.tsx
    statusLabels.ts
    types.ts
.env.example
README.md
```

Responsibilities:

- `backend/app/docx_service.py`: parse DOCX files into editable blocks and export confirmed replacements.
- `backend/app/mapper.py`: order-based English/Chinese text-block mapping.
- `backend/app/project_store.py`: local project directories and in-memory prototype project state.
- `backend/app/ai_client.py`: OpenAI-compatible model call and prompt construction.
- `backend/app/main.py`: FastAPI routes.
- `frontend/src/App.tsx`: side-by-side Chinese UI workflow.
- `frontend/src/api.ts`: frontend API wrapper.
- `frontend/src/statusLabels.ts`: internal status to Simplified Chinese label mapping.

---

### Task 1: Backend Project Skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/models.py`
- Create: `backend/app/config.py`
- Create: `.env.example`

- [ ] **Step 1: Write the failing model/config tests**

Create `backend/tests/test_api.py` with:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Create `backend/tests/test_ai_client.py` with:

```python
import pytest

from app.config import Settings


def test_settings_default_openai_base_url():
    settings = Settings(openai_api_key="test-key", openai_model="test-model")

    assert settings.openai_base_url == "https://api.openai.com/v1"


def test_settings_requires_api_key_for_ai_calls():
    settings = Settings(openai_api_key="", openai_model="test-model")

    assert not settings.has_openai_key
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
cd G:\softapp\word-E-to-C
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m pytest backend\tests\test_api.py backend\tests\test_ai_client.py -v
```

Expected: fail because `backend/requirements.txt`, `app.main`, and `app.config` do not exist yet.

- [ ] **Step 3: Add backend dependencies**

Create `backend/requirements.txt`:

```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.20
python-docx==1.1.2
lxml==5.3.0
openai==1.59.7
python-dotenv==1.0.1
pydantic-settings==2.7.1
pytest==8.3.4
pytest-asyncio==0.25.2
httpx==0.28.1
```

Create `backend/pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Add settings and models**

Create `backend/app/__init__.py`:

```python
"""Backend package for the bilingual DOCX sync prototype."""
```

Create `backend/app/config.py`:

```python
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="", alias="OPENAI_MODEL")
    data_dir: Path = Field(default=Path("data/projects"), alias="DATA_DIR")

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `backend/app/models.py`:

```python
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
```

- [ ] **Step 5: Add health route**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Bilingual DOCX Sync")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Create `.env.example`:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=
DATA_DIR=data/projects
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m pytest backend\tests\test_api.py backend\tests\test_ai_client.py -v
```

Expected: both tests pass.

- [ ] **Step 7: Commit**

```powershell
git add .env.example backend
git commit -m "feat: scaffold backend app"
```

---

### Task 2: DOCX Parsing Service

**Files:**
- Create: `backend/app/docx_service.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_docx_service.py`

- [ ] **Step 1: Write failing DOCX parsing tests**

Create `backend/tests/conftest.py`:

```python
from pathlib import Path
import pytest
from docx import Document


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    path = tmp_path / "sample.docx"
    doc = Document()
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph("First body paragraph.")
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Table cell text."
    doc.save(path)
    return path
```

Create `backend/tests/test_docx_service.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_docx_service.py::test_extracts_headings_body_paragraphs_and_table_cells -v
```

Expected: fail because `app.docx_service` does not exist.

- [ ] **Step 3: Implement DOCX block extraction**

Create `backend/app/docx_service.py`:

```python
from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph

from app.models import BlockKind, Side, TextBlock


class DocxService:
    def extract_blocks(self, path: Path, side: Side) -> list[TextBlock]:
        document = Document(path)
        blocks: list[TextBlock] = []

        for paragraph_index, paragraph in enumerate(document.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue
            blocks.append(
                self._block_from_paragraph(
                    paragraph=paragraph,
                    side=side,
                    index=len(blocks),
                    path=f"p:{paragraph_index}",
                    kind=self._paragraph_kind(paragraph),
                )
            )

        for table_index, table in enumerate(document.tables):
            for row_index, row in enumerate(table.rows):
                for cell_index, cell in enumerate(row.cells):
                    for paragraph_index, paragraph in enumerate(cell.paragraphs):
                        text = paragraph.text.strip()
                        if not text:
                            continue
                        blocks.append(
                            self._block_from_paragraph(
                                paragraph=paragraph,
                                side=side,
                                index=len(blocks),
                                path=f"table:{table_index}:row:{row_index}:cell:{cell_index}:p:{paragraph_index}",
                                kind=BlockKind.TABLE_CELL,
                            )
                        )

        return blocks

    def _block_from_paragraph(
        self,
        paragraph: Paragraph,
        side: Side,
        index: int,
        path: str,
        kind: BlockKind,
    ) -> TextBlock:
        return TextBlock(
            id=f"{side.value}-{index:05d}",
            side=side,
            kind=kind,
            index=index,
            text=paragraph.text.strip(),
            path=path,
            mappedId=None,
        )

    def _paragraph_kind(self, paragraph: Paragraph) -> BlockKind:
        style_name = paragraph.style.name.lower() if paragraph.style and paragraph.style.name else ""
        if style_name.startswith("heading"):
            return BlockKind.HEADING
        return BlockKind.PARAGRAPH
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_docx_service.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/docx_service.py backend/tests/conftest.py backend/tests/test_docx_service.py
git commit -m "feat: parse docx text blocks"
```

---

### Task 3: Order-Based Mapping

**Files:**
- Create: `backend/app/mapper.py`
- Create: `backend/tests/test_mapper.py`

- [ ] **Step 1: Write failing mapping tests**

Create `backend/tests/test_mapper.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_mapper.py -v
```

Expected: fail because `app.mapper` does not exist.

- [ ] **Step 3: Implement mapping**

Create `backend/app/mapper.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_mapper.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/mapper.py backend/tests/test_mapper.py
git commit -m "feat: map bilingual text blocks"
```

---

### Task 4: DOCX Paragraph-Level Write-Back

**Files:**
- Modify: `backend/app/docx_service.py`
- Modify: `backend/tests/test_docx_service.py`

- [ ] **Step 1: Add failing write-back tests**

Append to `backend/tests/test_docx_service.py`:

```python
from docx import Document


def test_replaces_body_paragraph_and_preserves_other_text(sample_docx, tmp_path):
    service = DocxService()
    output = tmp_path / "updated.docx"

    service.export_with_replacements(
        source_path=sample_docx,
        output_path=output,
        replacements={"p:1": "Updated body paragraph."},
    )

    doc = Document(output)
    assert doc.paragraphs[0].text == "Introduction"
    assert doc.paragraphs[1].text == "Updated body paragraph."
    assert doc.tables[0].cell(0, 0).text == "Table cell text."


def test_replaces_table_cell_paragraph(sample_docx, tmp_path):
    service = DocxService()
    output = tmp_path / "updated-table.docx"

    service.export_with_replacements(
        source_path=sample_docx,
        output_path=output,
        replacements={"table:0:row:0:cell:0:p:0": "Updated table text."},
    )

    doc = Document(output)
    assert doc.tables[0].cell(0, 0).text == "Updated table text."
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_docx_service.py -v
```

Expected: fail because `export_with_replacements` does not exist.

- [ ] **Step 3: Implement paragraph replacement**

Update `backend/app/docx_service.py`:

```python
from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph

from app.models import BlockKind, Side, TextBlock


class DocxService:
    def extract_blocks(self, path: Path, side: Side) -> list[TextBlock]:
        document = Document(path)
        blocks: list[TextBlock] = []

        for paragraph_index, paragraph in enumerate(document.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue
            blocks.append(
                self._block_from_paragraph(
                    paragraph=paragraph,
                    side=side,
                    index=len(blocks),
                    path=f"p:{paragraph_index}",
                    kind=self._paragraph_kind(paragraph),
                )
            )

        for table_index, table in enumerate(document.tables):
            for row_index, row in enumerate(table.rows):
                for cell_index, cell in enumerate(row.cells):
                    for paragraph_index, paragraph in enumerate(cell.paragraphs):
                        text = paragraph.text.strip()
                        if not text:
                            continue
                        blocks.append(
                            self._block_from_paragraph(
                                paragraph=paragraph,
                                side=side,
                                index=len(blocks),
                                path=f"table:{table_index}:row:{row_index}:cell:{cell_index}:p:{paragraph_index}",
                                kind=BlockKind.TABLE_CELL,
                            )
                        )

        return blocks

    def export_with_replacements(
        self,
        source_path: Path,
        output_path: Path,
        replacements: dict[str, str],
    ) -> None:
        document = Document(source_path)
        for block_path, replacement_text in replacements.items():
            paragraph = self._resolve_paragraph(document, block_path)
            self._replace_paragraph_text(paragraph, replacement_text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(output_path)

    def _resolve_paragraph(self, document: Document, block_path: str) -> Paragraph:
        parts = block_path.split(":")
        if parts[0] == "p":
            return document.paragraphs[int(parts[1])]
        if parts[0] == "table":
            table_index = int(parts[1])
            row_index = int(parts[3])
            cell_index = int(parts[5])
            paragraph_index = int(parts[7])
            return document.tables[table_index].rows[row_index].cells[cell_index].paragraphs[paragraph_index]
        raise ValueError(f"Unsupported block path: {block_path}")

    def _replace_paragraph_text(self, paragraph: Paragraph, text: str) -> None:
        if paragraph.runs:
            paragraph.runs[0].text = text
            for run in paragraph.runs[1:]:
                run.text = ""
            return
        paragraph.add_run(text)

    def _block_from_paragraph(
        self,
        paragraph: Paragraph,
        side: Side,
        index: int,
        path: str,
        kind: BlockKind,
    ) -> TextBlock:
        return TextBlock(
            id=f"{side.value}-{index:05d}",
            side=side,
            kind=kind,
            index=index,
            text=paragraph.text.strip(),
            path=path,
            mappedId=None,
        )

    def _paragraph_kind(self, paragraph: Paragraph) -> BlockKind:
        style_name = paragraph.style.name.lower() if paragraph.style and paragraph.style.name else ""
        if style_name.startswith("heading"):
            return BlockKind.HEADING
        return BlockKind.PARAGRAPH
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_docx_service.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/docx_service.py backend/tests/test_docx_service.py
git commit -m "feat: write docx paragraph replacements"
```

---

### Task 5: Project Store and API Routes

**Files:**
- Create: `backend/app/project_store.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Add failing API tests**

Replace `backend/tests/test_api.py` with:

```python
from pathlib import Path
from fastapi.testclient import TestClient
from docx import Document

from app.config import Settings
from app.main import create_app


def make_docx(path: Path, heading: str, body: str) -> None:
    doc = Document()
    doc.add_heading(heading, level=1)
    doc.add_paragraph(body)
    doc.save(path)


def test_health_endpoint_returns_ok(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, openai_api_key="", openai_model=""))
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_uploads_and_parses_paired_docx(tmp_path):
    en_path = tmp_path / "en.docx"
    zh_path = tmp_path / "zh.docx"
    make_docx(en_path, "Introduction", "English body.")
    make_docx(zh_path, "引言", "中文正文。")
    app = create_app(Settings(data_dir=tmp_path / "projects", openai_api_key="", openai_model=""))
    client = TestClient(app)

    with en_path.open("rb") as en_file, zh_path.open("rb") as zh_file:
        response = client.post(
            "/api/projects",
            files={
                "en_file": ("en.docx", en_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                "zh_file": ("zh.docx", zh_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["projectId"]
    assert payload["enBlocks"][0]["text"] == "Introduction"
    assert payload["zhBlocks"][1]["text"] == "中文正文。"
    assert payload["mappings"][0]["enId"] == "en-00000"
    assert payload["mappings"][0]["zhId"] == "zh-00000"


def test_rejects_non_docx_uploads(tmp_path):
    txt_path = tmp_path / "bad.txt"
    txt_path.write_text("not a docx", encoding="utf-8")
    docx_path = tmp_path / "zh.docx"
    make_docx(docx_path, "引言", "正文")
    app = create_app(Settings(data_dir=tmp_path / "projects", openai_api_key="", openai_model=""))
    client = TestClient(app)

    with txt_path.open("rb") as en_file, docx_path.open("rb") as zh_file:
        response = client.post(
            "/api/projects",
            files={
                "en_file": ("bad.txt", en_file, "text/plain"),
                "zh_file": ("zh.docx", zh_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "请上传 .docx 格式的 Word 文件。"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py -v
```

Expected: fail because `create_app`, upload route, and project store do not exist.

- [ ] **Step 3: Implement project store**

Create `backend/app/project_store.py`:

```python
from pathlib import Path
from uuid import uuid4
import shutil

from app.docx_service import DocxService
from app.mapper import build_order_mapping
from app.models import ProjectState, Side, StoredProject, TextBlock


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

    def update_block(self, project_id: str, block_id: str, text: str, status: str) -> TextBlock:
        project = self.get_project(project_id)
        for block in [*project.state.en_blocks, *project.state.zh_blocks]:
            if block.id == block_id:
                block.text = text
                block.status = status
                return block
        raise KeyError(block_id)
```

- [ ] **Step 4: Implement FastAPI routes**

Replace `backend/app/main.py` with:

```python
from tempfile import NamedTemporaryFile
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.docx_service import DocxService
from app.models import ProjectState, TextBlock, UpdateBlockRequest
from app.project_store import ProjectStore


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    store = ProjectStore(resolved_settings.data_dir, DocxService())
    app = FastAPI(title="Bilingual DOCX Sync")
    app.state.project_store = store

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/projects", response_model=ProjectState)
    async def create_project(
        en_file: UploadFile = File(...),
        zh_file: UploadFile = File(...),
    ) -> ProjectState:
        _validate_docx(en_file)
        _validate_docx(zh_file)
        en_temp = await _save_temp_upload(en_file)
        zh_temp = await _save_temp_upload(zh_file)
        return store.create_project(
            en_source=en_temp,
            zh_source=zh_temp,
            en_filename=en_file.filename or "english.docx",
            zh_filename=zh_file.filename or "chinese.docx",
        )

    @app.patch("/api/projects/{project_id}/blocks/{block_id}", response_model=TextBlock)
    def update_block(project_id: str, block_id: str, request: UpdateBlockRequest) -> TextBlock:
        try:
            return store.update_block(project_id, block_id, request.text, request.status)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到对应段落。")

    return app


def _validate_docx(file: UploadFile) -> None:
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="请上传 .docx 格式的 Word 文件。")


async def _save_temp_upload(file: UploadFile):
    with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        return tmp.name


app = create_app()
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/main.py backend/app/project_store.py backend/tests/test_api.py
git commit -m "feat: add project upload api"
```

---

### Task 6: AI Suggestion Client and Route

**Files:**
- Create: `backend/app/ai_client.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_ai_client.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Add failing AI client tests**

Replace `backend/tests/test_ai_client.py` with:

```python
import pytest

from app.ai_client import AIClient, MissingApiKeyError, build_sync_prompt
from app.config import Settings


def test_settings_default_openai_base_url():
    settings = Settings(openai_api_key="test-key", openai_model="test-model")

    assert settings.openai_base_url == "https://api.openai.com/v1"


def test_settings_requires_api_key_for_ai_calls():
    settings = Settings(openai_api_key="", openai_model="test-model")

    assert not settings.has_openai_key


def test_builds_english_to_chinese_prompt():
    messages = build_sync_prompt(
        direction="en_to_zh",
        source_text="The revised English paragraph.",
        target_text="原中文段落。",
    )

    assert messages[0]["role"] == "system"
    assert "只返回建议段落文本" in messages[0]["content"]
    assert "英文修改后段落" in messages[1]["content"]
    assert "当前中文对应段落" in messages[1]["content"]


@pytest.mark.asyncio
async def test_missing_api_key_raises_clear_error():
    client = AIClient(Settings(openai_api_key="", openai_model="test-model"))

    with pytest.raises(MissingApiKeyError):
        await client.suggest(
            direction="en_to_zh",
            source_text="A",
            target_text="甲",
        )
```

- [ ] **Step 2: Add failing suggest route test**

Append to `backend/tests/test_api.py`:

```python
def test_suggest_without_api_key_returns_chinese_error(tmp_path):
    app = create_app(Settings(data_dir=tmp_path / "projects", openai_api_key="", openai_model="test-model"))
    client = TestClient(app)

    response = client.post(
        "/api/projects/demo/suggest",
        json={
            "direction": "en_to_zh",
            "sourceBlockId": "en-00000",
            "targetBlockId": "zh-00000",
            "sourceText": "Updated English.",
            "targetText": "原中文。",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "未配置 API Key，请在 .env 中设置。"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_ai_client.py backend\tests\test_api.py::test_suggest_without_api_key_returns_chinese_error -v
```

Expected: fail because `app.ai_client` and suggest route do not exist.

- [ ] **Step 4: Implement AI client**

Create `backend/app/ai_client.py`:

```python
from openai import AsyncOpenAI

from app.config import Settings


class MissingApiKeyError(RuntimeError):
    pass


def build_sync_prompt(direction: str, source_text: str, target_text: str) -> list[dict[str, str]]:
    if direction == "en_to_zh":
        user_content = (
            "英文修改后段落：\n"
            f"{source_text}\n\n"
            "当前中文对应段落：\n"
            f"{target_text}\n\n"
            "请生成忠实反映英文修改的中文论文段落。"
        )
    elif direction == "zh_to_en":
        user_content = (
            "中文修改后段落：\n"
            f"{source_text}\n\n"
            "当前英文对应段落：\n"
            f"{target_text}\n\n"
            "Please generate an English manuscript paragraph that faithfully reflects the Chinese revision."
        )
    else:
        raise ValueError(f"Unsupported direction: {direction}")

    return [
        {
            "role": "system",
            "content": (
                "你是论文双语同步助手。保持学术论文语气，忠实反映修改，"
                "不要添加原文没有的新信息，不要解释，不要使用 Markdown，只返回建议段落文本。"
            ),
        },
        {"role": "user", "content": user_content},
    ]


class AIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def suggest(self, direction: str, source_text: str, target_text: str) -> str:
        if not self.settings.has_openai_key:
            raise MissingApiKeyError("OPENAI_API_KEY is not configured")
        if not self.settings.openai_model.strip():
            raise MissingApiKeyError("OPENAI_MODEL is not configured")

        client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
        )
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=build_sync_prompt(direction, source_text, target_text),
            temperature=0.2,
        )
        suggestion = response.choices[0].message.content or ""
        return suggestion.strip()
```

- [ ] **Step 5: Wire suggest route**

Update `backend/app/main.py` to import and use AI client:

```python
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, File, HTTPException, UploadFile

from app.ai_client import AIClient, MissingApiKeyError
from app.config import Settings, get_settings
from app.docx_service import DocxService
from app.models import ProjectState, SuggestRequest, SuggestResponse, TextBlock, UpdateBlockRequest
from app.project_store import ProjectStore


def create_app(settings: Settings | None = None, ai_client: AIClient | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    store = ProjectStore(resolved_settings.data_dir, DocxService())
    resolved_ai_client = ai_client or AIClient(resolved_settings)
    app = FastAPI(title="Bilingual DOCX Sync")
    app.state.project_store = store

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/projects", response_model=ProjectState)
    async def create_project(
        en_file: UploadFile = File(...),
        zh_file: UploadFile = File(...),
    ) -> ProjectState:
        _validate_docx(en_file)
        _validate_docx(zh_file)
        en_temp = await _save_temp_upload(en_file)
        zh_temp = await _save_temp_upload(zh_file)
        return store.create_project(
            en_source=en_temp,
            zh_source=zh_temp,
            en_filename=en_file.filename or "english.docx",
            zh_filename=zh_file.filename or "chinese.docx",
        )

    @app.post("/api/projects/{project_id}/suggest", response_model=SuggestResponse)
    async def suggest(project_id: str, request: SuggestRequest) -> SuggestResponse:
        try:
            suggestion = await resolved_ai_client.suggest(
                direction=request.direction,
                source_text=request.source_text,
                target_text=request.target_text,
            )
        except MissingApiKeyError:
            raise HTTPException(status_code=400, detail="未配置 API Key，请在 .env 中设置。")
        except Exception:
            raise HTTPException(status_code=502, detail="同步建议生成失败，请稍后重试。")
        if not suggestion:
            raise HTTPException(status_code=502, detail="模型返回内容为空，请重试。")
        return SuggestResponse(suggestion=suggestion)

    @app.patch("/api/projects/{project_id}/blocks/{block_id}", response_model=TextBlock)
    def update_block(project_id: str, block_id: str, request: UpdateBlockRequest) -> TextBlock:
        try:
            return store.update_block(project_id, block_id, request.text, request.status)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到对应段落。")

    return app


def _validate_docx(file: UploadFile) -> None:
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="请上传 .docx 格式的 Word 文件。")


async def _save_temp_upload(file: UploadFile):
    with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        return tmp.name


app = create_app()
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_ai_client.py backend\tests\test_api.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/ai_client.py backend/app/main.py backend/tests/test_ai_client.py backend/tests/test_api.py
git commit -m "feat: add ai sync suggestions"
```

---

### Task 7: Export API

**Files:**
- Modify: `backend/app/project_store.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Add failing export API test**

Append to `backend/tests/test_api.py`:

```python
def test_exports_updated_docx_after_confirmed_replacement(tmp_path):
    en_path = tmp_path / "en.docx"
    zh_path = tmp_path / "zh.docx"
    make_docx(en_path, "Introduction", "English body.")
    make_docx(zh_path, "引言", "中文正文。")
    app = create_app(Settings(data_dir=tmp_path / "projects", openai_api_key="", openai_model=""))
    client = TestClient(app)

    with en_path.open("rb") as en_file, zh_path.open("rb") as zh_file:
        created = client.post(
            "/api/projects",
            files={
                "en_file": ("en.docx", en_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                "zh_file": ("zh.docx", zh_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            },
        ).json()

    project_id = created["projectId"]
    target_block_id = created["zhBlocks"][1]["id"]
    client.patch(
        f"/api/projects/{project_id}/blocks/{target_block_id}",
        json={"text": "更新后的中文正文。", "status": "modified"},
    )

    response = client.post(f"/api/projects/{project_id}/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["zhDownloadUrl"].endswith("/updated-zh.docx")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py::test_exports_updated_docx_after_confirmed_replacement -v
```

Expected: fail because export route does not exist.

- [ ] **Step 3: Implement project export**

Update `backend/app/project_store.py`:

```python
from pathlib import Path
from uuid import uuid4
import shutil

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

    def update_block(self, project_id: str, block_id: str, text: str, status: str) -> TextBlock:
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
```

- [ ] **Step 4: Add export and download routes**

Update imports and routes in `backend/app/main.py`:

```python
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.ai_client import AIClient, MissingApiKeyError
from app.config import Settings, get_settings
from app.docx_service import DocxService
from app.models import ExportResponse, ProjectState, SuggestRequest, SuggestResponse, TextBlock, UpdateBlockRequest
from app.project_store import ProjectStore
```

Add before `return app`:

```python
    @app.post("/api/projects/{project_id}/export", response_model=ExportResponse)
    def export(project_id: str) -> ExportResponse:
        try:
            store.export_project(project_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到项目。")
        return ExportResponse(
            enDownloadUrl=f"/api/projects/{project_id}/download/updated-en.docx",
            zhDownloadUrl=f"/api/projects/{project_id}/download/updated-zh.docx",
        )

    @app.get("/api/projects/{project_id}/download/{filename}")
    def download(project_id: str, filename: str) -> FileResponse:
        if filename not in {"updated-en.docx", "updated-zh.docx"}:
            raise HTTPException(status_code=404, detail="未找到导出文件。")
        try:
            project = store.get_project(project_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到项目。")
        path = project.root / "exports" / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="请先导出更新后的 Word。")
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/main.py backend/app/project_store.py backend/tests/test_api.py
git commit -m "feat: export updated docx files"
```

---

### Task 8: Frontend Skeleton and Chinese Status Labels

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/statusLabels.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.css`
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Create `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { statusLabel } from "./statusLabels";

describe("中文界面", () => {
  it("显示中文上传和操作按钮", () => {
    render(<App />);

    expect(screen.getByText("上传英文 Word")).toBeInTheDocument();
    expect(screen.getByText("上传中文 Word")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "解析文档" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "导出更新后的 Word" })).toBeInTheDocument();
  });

  it("把内部状态映射为中文", () => {
    expect(statusLabel.clean).toBe("未修改");
    expect(statusLabel.edited).toBe("已编辑，待同步");
    expect(statusLabel.suggested).toBe("有同步建议，待确认");
    expect(statusLabel.modified).toBe("已确认写回");
    expect(statusLabel.error).toBe("处理失败");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
npm --prefix frontend install
npm --prefix frontend test -- --run
```

Expected: fail because frontend files do not exist.

- [ ] **Step 3: Add frontend package and Vite config**

Create `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc && vite build",
    "test": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "typescript": "latest",
    "react": "latest",
    "react-dom": "latest",
    "lucide-react": "latest"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "latest",
    "@testing-library/react": "latest",
    "@testing-library/user-event": "latest",
    "vitest": "latest",
    "jsdom": "latest"
  }
}
```

Create `frontend/index.html`:

```html
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

Create `frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["@testing-library/jest-dom/vitest"],
  },
});
```

- [ ] **Step 4: Add minimal Chinese UI**

Create `frontend/src/types.ts`:

```ts
export type BlockStatus = "clean" | "edited" | "suggested" | "modified" | "error";
export type Side = "en" | "zh";

export interface TextBlock {
  id: string;
  side: Side;
  kind: "paragraph" | "heading" | "table_cell" | "unsupported";
  index: number;
  text: string;
  path: string;
  mappedId: string | null;
  status: BlockStatus;
}

export interface MappingPair {
  enId: string | null;
  zhId: string | null;
  index: number;
  mapped: boolean;
}

export interface ProjectState {
  projectId: string;
  enFilename: string;
  zhFilename: string;
  enBlocks: TextBlock[];
  zhBlocks: TextBlock[];
  mappings: MappingPair[];
  warnings: string[];
}
```

Create `frontend/src/statusLabels.ts`:

```ts
import type { BlockStatus } from "./types";

export const statusLabel: Record<BlockStatus, string> = {
  clean: "未修改",
  edited: "已编辑，待同步",
  suggested: "有同步建议，待确认",
  modified: "已确认写回",
  error: "处理失败",
};
```

Create `frontend/src/App.tsx`:

```tsx
import "./App.css";

export default function App() {
  return (
    <main className="app-shell">
      <header className="toolbar">
        <label className="file-button">
          上传英文 Word
          <input type="file" accept=".docx" />
        </label>
        <label className="file-button">
          上传中文 Word
          <input type="file" accept=".docx" />
        </label>
        <button type="button">解析文档</button>
        <button type="button">导出更新后的 Word</button>
      </header>
      <section className="editor-grid">
        <article className="panel">
          <h2>英文原稿</h2>
          <p className="empty">请先上传并解析英文 Word。</p>
        </article>
        <article className="panel">
          <h2>中文原稿</h2>
          <p className="empty">请先上传并解析中文 Word。</p>
        </article>
      </section>
      <section className="suggestion-panel">
        <h2>同步建议</h2>
        <p>选择一组对应段落后，可以生成并确认另一侧的同步建议。</p>
      </section>
    </main>
  );
}
```

Create `frontend/src/App.css`:

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
  color: #1f2937;
  background: #f4f6f8;
}

button,
.file-button {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #1f2937;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 14px;
  cursor: pointer;
}

.file-button input {
  display: none;
}

.app-shell {
  min-height: 100vh;
  padding: 18px;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.panel,
.suggestion-panel {
  background: #ffffff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
  padding: 16px;
}

.panel h2,
.suggestion-panel h2 {
  margin: 0 0 12px;
  font-size: 18px;
}

.empty {
  color: #64748b;
}

.suggestion-panel {
  margin-top: 16px;
}
```

Create `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
npm --prefix frontend install
npm --prefix frontend test -- --run
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend
git commit -m "feat: scaffold chinese frontend"
```

---

### Task 9: Frontend API Integration and Editing Workflow

**Files:**
- Create: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add failing interaction tests**

Append to `frontend/src/App.test.tsx`:

```tsx
it("上传解析后显示双栏段落并允许生成同步建议", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          projectId: "demo",
          enFilename: "en.docx",
          zhFilename: "zh.docx",
          enBlocks: [
            { id: "en-00000", side: "en", kind: "paragraph", index: 0, text: "English text.", path: "p:0", mappedId: "zh-00000", status: "clean" },
          ],
          zhBlocks: [
            { id: "zh-00000", side: "zh", kind: "paragraph", index: 0, text: "中文文本。", path: "p:0", mappedId: "en-00000", status: "clean" },
          ],
          mappings: [{ enId: "en-00000", zhId: "zh-00000", index: 0, mapped: true }],
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "en-00000",
          side: "en",
          kind: "paragraph",
          index: 0,
          text: "Updated English.",
          path: "p:0",
          mappedId: "zh-00000",
          status: "modified",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ suggestion: "更新后的中文。" }),
      }),
  );

  render(<App />);
  const enInput = screen.getByLabelText("上传英文 Word");
  const zhInput = screen.getByLabelText("上传中文 Word");
  await user.upload(enInput, new File(["en"], "en.docx"));
  await user.upload(zhInput, new File(["zh"], "zh.docx"));
  await user.click(screen.getByRole("button", { name: "解析文档" }));

  expect(await screen.findByText("English text.")).toBeInTheDocument();
  await user.click(screen.getByText("English text."));
  await user.clear(screen.getByLabelText("英文段落内容"));
  await user.type(screen.getByLabelText("英文段落内容"), "Updated English.");
  await user.click(screen.getByRole("button", { name: "同步到中文" }));

  expect(await screen.findByDisplayValue("更新后的中文。")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm --prefix frontend test -- --run
```

Expected: fail because upload parsing, editing, and suggest integration are not implemented.

- [ ] **Step 3: Add API wrapper**

Create `frontend/src/api.ts`:

```ts
import type { BlockStatus, ProjectState } from "./types";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "请求失败，请稍后重试。");
  }
  return response.json() as Promise<T>;
}

export async function createProject(enFile: File, zhFile: File): Promise<ProjectState> {
  const form = new FormData();
  form.append("en_file", enFile);
  form.append("zh_file", zhFile);
  return readJson<ProjectState>(await fetch("/api/projects", { method: "POST", body: form }));
}

export async function requestSuggestion(input: {
  projectId: string;
  direction: "en_to_zh" | "zh_to_en";
  sourceBlockId: string;
  targetBlockId: string;
  sourceText: string;
  targetText: string;
}): Promise<string> {
  const payload = await readJson<{ suggestion: string }>(
    await fetch(`/api/projects/${input.projectId}/suggest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
  return payload.suggestion;
}

export async function updateBlock(input: {
  projectId: string;
  blockId: string;
  text: string;
  status: BlockStatus;
}) {
  return readJson(
    await fetch(`/api/projects/${input.projectId}/blocks/${input.blockId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input.text, status: input.status }),
    }),
  );
}
```

- [ ] **Step 4: Implement side-by-side editor workflow**

Replace `frontend/src/App.tsx` with:

```tsx
import { useMemo, useState } from "react";
import { createProject, requestSuggestion, updateBlock } from "./api";
import "./App.css";
import { statusLabel } from "./statusLabels";
import type { BlockStatus, ProjectState, TextBlock } from "./types";

type Direction = "en_to_zh" | "zh_to_en";

export default function App() {
  const [enFile, setEnFile] = useState<File | null>(null);
  const [zhFile, setZhFile] = useState<File | null>(null);
  const [project, setProject] = useState<ProjectState | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [draftEn, setDraftEn] = useState("");
  const [draftZh, setDraftZh] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [suggestionTarget, setSuggestionTarget] = useState<TextBlock | null>(null);
  const [direction, setDirection] = useState<Direction>("en_to_zh");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const selectedPair = useMemo(() => {
    if (!project) return null;
    const pair = project.mappings[selectedIndex];
    return {
      en: project.enBlocks.find((block) => block.id === pair?.enId) ?? null,
      zh: project.zhBlocks.find((block) => block.id === pair?.zhId) ?? null,
      mapped: pair?.mapped ?? false,
    };
  }, [project, selectedIndex]);

  async function parseDocuments() {
    if (!enFile || !zhFile) {
      setMessage("请先上传英文 Word 和中文 Word。");
      return;
    }
    setBusy(true);
    try {
      const created = await createProject(enFile, zhFile);
      setProject(created);
      setSelectedIndex(0);
      setDraftEn(created.enBlocks[0]?.text ?? "");
      setDraftZh(created.zhBlocks[0]?.text ?? "");
      setMessage(created.warnings[0] ?? "文档解析完成。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "文档解析失败。");
    } finally {
      setBusy(false);
    }
  }

  function selectPair(index: number) {
    if (!project) return;
    const pair = project.mappings[index];
    const en = project.enBlocks.find((block) => block.id === pair.enId);
    const zh = project.zhBlocks.find((block) => block.id === pair.zhId);
    setSelectedIndex(index);
    setDraftEn(en?.text ?? "");
    setDraftZh(zh?.text ?? "");
    setSuggestion("");
    setSuggestionTarget(null);
  }

  function replaceProjectBlock(
    current: ProjectState,
    blockId: string,
    text: string,
    status: BlockStatus,
  ): ProjectState {
    return {
      ...current,
      enBlocks: current.enBlocks.map((block) =>
        block.id === blockId ? { ...block, text, status } : block,
      ),
      zhBlocks: current.zhBlocks.map((block) =>
        block.id === blockId ? { ...block, text, status } : block,
      ),
    };
  }

  async function sync(nextDirection: Direction) {
    if (!project || !selectedPair?.en || !selectedPair.zh || !selectedPair.mapped) {
      setMessage("当前段落未建立映射，无法同步。");
      return;
    }
    setBusy(true);
    setDirection(nextDirection);
    try {
      const source = nextDirection === "en_to_zh" ? selectedPair.en : selectedPair.zh;
      const target = nextDirection === "en_to_zh" ? selectedPair.zh : selectedPair.en;
      const sourceText = nextDirection === "en_to_zh" ? draftEn : draftZh;
      const targetText = nextDirection === "en_to_zh" ? draftZh : draftEn;
      await updateBlock({
        projectId: project.projectId,
        blockId: source.id,
        text: sourceText,
        status: "modified",
      });
      setProject(replaceProjectBlock(project, source.id, sourceText, "modified"));
      const nextSuggestion = await requestSuggestion({
        projectId: project.projectId,
        direction: nextDirection,
        sourceBlockId: source.id,
        targetBlockId: target.id,
        sourceText,
        targetText,
      });
      setSuggestion(nextSuggestion);
      setSuggestionTarget(target);
      setMessage("已生成同步建议，请确认后写回。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "同步建议生成失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  async function confirmSuggestion() {
    if (!project || !suggestionTarget) return;
    await updateBlock({
      projectId: project.projectId,
      blockId: suggestionTarget.id,
      text: suggestion,
      status: "modified",
    });
    setProject(replaceProjectBlock(project, suggestionTarget.id, suggestion, "modified"));
    if (suggestionTarget.side === "en") setDraftEn(suggestion);
    if (suggestionTarget.side === "zh") setDraftZh(suggestion);
    setSuggestion("");
    setSuggestionTarget(null);
    setMessage("已确认写回。");
  }

  function renderBlock(block: TextBlock | null, index: number, language: "英文" | "中文") {
    if (!block) {
      return (
        <button type="button" className="block-row unmapped" disabled>
          <span>{language}段落 {index + 1}</span>
          <span>未映射</span>
        </button>
      );
    }

    return (
      <button
        type="button"
        className={`block-row ${selectedIndex === index ? "selected" : ""}`}
        onClick={() => selectPair(index)}
      >
        <span className="block-index">{language} {index + 1}</span>
        <span className="block-preview">{block.text}</span>
        <span className="status-pill">{statusLabel[block.status]}</span>
      </button>
    );
  }

  return (
    <main className="app-shell">
      <header className="toolbar">
        <label className="file-button">
          上传英文 Word
          <input
            aria-label="上传英文 Word"
            type="file"
            accept=".docx"
            onChange={(event) => setEnFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <label className="file-button">
          上传中文 Word
          <input
            aria-label="上传中文 Word"
            type="file"
            accept=".docx"
            onChange={(event) => setZhFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="button" onClick={parseDocuments} disabled={busy}>
          解析文档
        </button>
        <button type="button" disabled={!project || busy}>
          导出更新后的 Word
        </button>
      </header>

      {message && <div className="message">{message}</div>}

      <section className="editor-grid">
        <article className="panel">
          <h2>英文原稿</h2>
          <div className="block-list">
            {project
              ? project.mappings.map((pair, index) =>
                  renderBlock(project.enBlocks.find((block) => block.id === pair.enId) ?? null, index, "英文"),
                )
              : <p className="empty">请先上传并解析英文 Word。</p>}
          </div>
          <label className="editor-label" htmlFor="en-editor">
            英文段落内容
          </label>
          <textarea
            id="en-editor"
            value={draftEn}
            onChange={(event) => setDraftEn(event.target.value)}
            disabled={!selectedPair?.en}
          />
          <button type="button" onClick={() => sync("en_to_zh")} disabled={!selectedPair?.mapped || busy}>
            同步到中文
          </button>
        </article>

        <article className="panel">
          <h2>中文原稿</h2>
          <div className="block-list">
            {project
              ? project.mappings.map((pair, index) =>
                  renderBlock(project.zhBlocks.find((block) => block.id === pair.zhId) ?? null, index, "中文"),
                )
              : <p className="empty">请先上传并解析中文 Word。</p>}
          </div>
          <label className="editor-label" htmlFor="zh-editor">
            中文段落内容
          </label>
          <textarea
            id="zh-editor"
            value={draftZh}
            onChange={(event) => setDraftZh(event.target.value)}
            disabled={!selectedPair?.zh}
          />
          <button type="button" onClick={() => sync("zh_to_en")} disabled={!selectedPair?.mapped || busy}>
            同步到英文
          </button>
        </article>
      </section>

      <section className="suggestion-panel">
        <h2>同步建议</h2>
        <p>{direction === "en_to_zh" ? "当前方向：英文同步到中文" : "当前方向：中文同步到英文"}</p>
        <textarea
          aria-label="同步建议内容"
          value={suggestion}
          onChange={(event) => setSuggestion(event.target.value)}
          placeholder="生成同步建议后会显示在这里。"
        />
        <button type="button" onClick={confirmSuggestion} disabled={!suggestionTarget || !suggestion || busy}>
          确认写回
        </button>
      </section>
    </main>
  );
}
```

Replace `frontend/src/App.css` with:

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
  color: #1f2937;
  background: #f4f6f8;
}

button,
.file-button {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #1f2937;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 14px;
  cursor: pointer;
}

button:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}

.file-button input {
  display: none;
}

.app-shell {
  min-height: 100vh;
  padding: 18px;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.message {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 16px;
}

.editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.panel,
.suggestion-panel {
  background: #ffffff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
  padding: 16px;
}

.panel h2,
.suggestion-panel h2 {
  margin: 0 0 12px;
  font-size: 18px;
}

.block-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
  margin-bottom: 12px;
}

.block-row {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  text-align: left;
}

.block-row.selected {
  border-color: #2563eb;
  background: #eff6ff;
}

.block-row.unmapped {
  background: #f8fafc;
}

.block-index,
.status-pill {
  white-space: nowrap;
  font-size: 12px;
  color: #475569;
}

.block-preview {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-label {
  display: block;
  margin: 10px 0 6px;
  font-weight: 600;
}

textarea {
  width: 100%;
  min-height: 150px;
  resize: vertical;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 10px;
  font: inherit;
  line-height: 1.5;
}

.empty {
  color: #64748b;
}

.suggestion-panel {
  margin-top: 16px;
}

.suggestion-panel textarea {
  min-height: 120px;
  margin-bottom: 10px;
}
```

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
npm --prefix frontend test -- --run
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src
git commit -m "feat: connect frontend editing workflow"
```

---

### Task 10: Export Button, README, and End-to-End Verification

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `README.md`

- [ ] **Step 1: Add frontend export API helper**

Modify `frontend/src/api.ts`:

```ts
export async function exportProject(projectId: string): Promise<{
  enDownloadUrl: string;
  zhDownloadUrl: string;
}> {
  return readJson(
    await fetch(`/api/projects/${projectId}/export`, {
      method: "POST",
    }),
  );
}
```

- [ ] **Step 2: Wire `导出更新后的 Word`**

Modify the import in `frontend/src/App.tsx`:

```tsx
import { createProject, exportProject, requestSuggestion, updateBlock } from "./api";
```

Add state near the existing `useState` calls:

```tsx
const [downloadLinks, setDownloadLinks] = useState<{
  enDownloadUrl: string;
  zhDownloadUrl: string;
} | null>(null);
```

Add this function before `return`:

```tsx
async function exportDocuments() {
  if (!project) {
    setMessage("请先上传并解析 Word。");
    return;
  }
  setBusy(true);
  try {
    const links = await exportProject(project.projectId);
    setDownloadLinks(links);
    setMessage("导出完成，请下载更新后的 Word 文件。");
  } catch (error) {
    setMessage(error instanceof Error ? error.message : "导出失败，请稍后重试。");
  } finally {
    setBusy(false);
  }
}
```

Replace the export button with:

```tsx
<button type="button" onClick={exportDocuments} disabled={!project || busy}>
  导出更新后的 Word
</button>
```

Render download links after the message block:

```tsx
{downloadLinks && (
  <div className="download-links">
    <a href={downloadLinks.enDownloadUrl}>下载更新后的英文 Word</a>
    <a href={downloadLinks.zhDownloadUrl}>下载更新后的中文 Word</a>
  </div>
)}
```

Add CSS:

```css
.download-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.download-links a {
  color: #1d4ed8;
  background: #ffffff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  padding: 8px 10px;
  text-decoration: none;
}
```

- [ ] **Step 3: Add README**

Create `README.md`:

````markdown
# word-E-to-C

本地双语 Word 论文同步修改原型。上传英文版论文和中文版论文后，可以在网页里按段落双栏编辑；修改任意一侧后，系统调用 OpenAI 或 OpenAI-compatible API 生成另一侧同步建议，用户确认后再写回对应 Word 段落。

## 功能范围

- 上传英文 `.docx` 和中文 `.docx`
- 解析正文段落、标题、表格单元格
- 按段落顺序建立中英映射
- 英文改动同步生成中文建议
- 中文改动同步生成英文建议
- 确认后段落级写回
- 导出更新后的 Word 文件

第一版不处理图片、公式、复杂文本框、脚注、交叉引用等复杂内容的语义同步，只尽量保留原 DOCX 结构。

## 环境配置

复制 `.env.example` 为 `.env`：

```env
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=你的模型名
DATA_DIR=data/projects
```

如果使用 OpenAI-compatible 服务，修改 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`。

## 启动后端

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

## 启动前端

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

打开前端显示的本地地址，通常是 `http://127.0.0.1:5173`。

## 测试

```powershell
.\.venv\Scripts\python -m pytest backend\tests -v
npm --prefix frontend test -- --run
npm --prefix frontend run build
```
````

- [ ] **Step 4: Run full verification**

Run:

```powershell
.\.venv\Scripts\python -m pytest backend\tests -v
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Expected: all pass.

- [ ] **Step 5: Start local dev servers**

Run backend:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Run frontend:

```powershell
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Expected:

- Backend health: `http://127.0.0.1:8000/api/health`
- Frontend app: `http://127.0.0.1:5173`

- [ ] **Step 6: Manual browser verification**

Use the browser to verify:

- Chinese UI text is visible.
- Upload controls accept `.docx`.
- Parsing shows side-by-side paragraph lists.
- Editing English enables `同步到中文`.
- Editing Chinese enables `同步到英文`.
- Suggestion appears without auto-applying.
- `确认写回` updates the target side only after confirmation.
- Export returns updated Word download URLs.

- [ ] **Step 7: Commit**

```powershell
git add README.md frontend/src frontend/package.json frontend/index.html frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts
git commit -m "feat: finish local prototype workflow"
```

---

## Final Verification Checklist

- [ ] Backend tests pass.
- [ ] Frontend tests pass.
- [ ] Frontend build passes.
- [ ] Local backend starts.
- [ ] Local frontend starts.
- [ ] Browser verification completed.
- [ ] `.env` is not committed.
- [ ] Uploaded and exported DOCX files are not committed.
- [ ] All visible UI copy is Simplified Chinese.
- [ ] Git status is clean or only contains intentional local runtime files ignored by `.gitignore`.
