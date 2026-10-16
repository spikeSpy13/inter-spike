from pathlib import Path
import sysconfig

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .extractor import analisar_paragrafo
from .models import AnalysisRequest, AnalysisResponse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIST_DIR = PROJECT_ROOT / "dist"
INSTALLED_DIST_DIR = Path(sysconfig.get_path("data")) / "share" / "interpretador-proposicoes"
DIST_DIR = SOURCE_DIST_DIR if SOURCE_DIST_DIR.is_dir() else INSTALLED_DIST_DIR

app = FastAPI(
    title="Interpretador de Proposições",
    version="0.4.1",
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

