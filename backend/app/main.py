from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile

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


async def _save_temp_upload(file: UploadFile) -> Path:
    with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        return Path(tmp.name)


app = create_app()
