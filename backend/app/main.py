from fastapi import FastAPI

app = FastAPI(title="Bilingual DOCX Sync")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
