from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .extractor import analisar_paragrafo
from .models import AnalysisRequest, AnalysisResponse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = PROJECT_ROOT / "dist"

app = FastAPI(
    title="Interpretador de Proposições",
    version="0.4.0",
    description="Grafo explicável de proposições, referências, operadores e atribuições em português.",
)
app.mount("/static", StaticFiles(directory=DIST_DIR), name="static")


@app.get("/", include_in_schema=False)
def interface() -> FileResponse:
    return FileResponse(DIST_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analisar", response_model=AnalysisResponse)
def analisar(entrada: AnalysisRequest) -> AnalysisResponse:
    return analisar_paragrafo(entrada.paragrafo, entrada.contexto_anterior)

