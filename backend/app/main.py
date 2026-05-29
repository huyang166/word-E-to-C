from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.ai_client import AIClient, MissingApiKeyError
from app.config import Settings, get_settings
from app.docx_service import DocxService
from app.models import ExportResponse, ProjectState, SuggestRequest, SuggestResponse, TextBlock, UpdateBlockRequest
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

    @app.patch("/api/projects/{project_id}/blocks/{block_id}", response_model=TextBlock)
    def update_block(project_id: str, block_id: str, request: UpdateBlockRequest) -> TextBlock:
        try:
            return store.update_block(project_id, block_id, request.text, request.status)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到对应段落。")

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
