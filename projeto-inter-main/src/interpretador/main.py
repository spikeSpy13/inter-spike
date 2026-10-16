from pathlib import Path
import sysconfig
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .extractor import analisar_paragrafo
from .ingestao import DocumentoIngerido, ErroIngestao, ParagrafoIngerido, validar_documento
from .models import (
    AnalysisRequest,
    AnalysisResponse,
    DocumentParagraph,
    DocumentSource,
    IngestionResponse,
    IngestionSummary,
    JsonAnalysisRequest,
    JsonAnalysisResponse,
    Span,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIST_DIR = PROJECT_ROOT / "dist"
INSTALLED_DIST_DIR = Path(sysconfig.get_path("data")) / "share" / "interpretador-proposicoes"
DIST_DIR = SOURCE_DIST_DIR if SOURCE_DIST_DIR.is_dir() else INSTALLED_DIST_DIR

app = FastAPI(
    title="Interpretador de Proposições",
    version="1.0.0",
    description="Interpretação fundamentada de parágrafos com geração e checagem explicáveis.",
)
app.mount("/static", StaticFiles(directory=DIST_DIR), name="static")


@app.get("/", include_in_schema=False)
def interface() -> FileResponse:
    return FileResponse(DIST_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(ErroIngestao)
async def erro_de_ingestao(_request: Request, erro: ErroIngestao) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": [problema.serializar() for problema in erro.problemas]},
    )


def _fonte(documento: DocumentoIngerido) -> DocumentSource:
    return DocumentSource(
        documento_id=documento.documento_id,
        schema_version=documento.schema_version,
        etapa=documento.etapa,
        caracteres_original=len(documento.texto_original),
    )


def _paragrafo(paragrafo: ParagrafoIngerido) -> DocumentParagraph:
    return DocumentParagraph(
        id=paragrafo.id,
        rotulo=paragrafo.rotulo,
        ordem=paragrafo.ordem,
        texto=paragrafo.texto,
        intervalo_original=Span(
            inicio=paragrafo.inicio_original,
            fim=paragrafo.fim_original,
        ),
        representacao_id=paragrafo.representacao_id,
        artefato_id=paragrafo.artefato_id,
    )


def validar_json(documento_bruto: Any) -> IngestionResponse:
    documento = validar_documento(documento_bruto)
    return IngestionResponse(
        fonte=_fonte(documento),
        paragrafos=[_paragrafo(item) for item in documento.paragrafos],
        resumo=IngestionSummary(
            paragrafos=len(documento.paragrafos),
            periodos=documento.periodos_total,
            tokens=documento.tokens_total,
            representacoes=documento.representacoes_total,
            artefatos=documento.artefatos_total,
            dimensao_vetores=documento.dimensao_vetores,
        ),
    )


@app.post("/api/documentos/validar", response_model=IngestionResponse)
def validar_documento_vetorizado(documento: dict[str, Any]) -> IngestionResponse:
    return validar_json(documento)


@app.post("/api/analisar", response_model=AnalysisResponse)
def analisar(entrada: AnalysisRequest) -> AnalysisResponse:
    return analisar_paragrafo(entrada.paragrafo, entrada.contexto_anterior)


@app.post("/api/analisar-json", response_model=JsonAnalysisResponse)
def analisar_json(entrada: JsonAnalysisRequest) -> JsonAnalysisResponse:
    documento = validar_documento(entrada.documento)
    paragrafo = documento.selecionar(entrada.paragrafo_id)
    analise = analisar_paragrafo(
        paragrafo.texto,
        documento.contexto_anterior(paragrafo),
    )
    return JsonAnalysisResponse(
        fonte=_fonte(documento),
        paragrafo=_paragrafo(paragrafo),
        analise=analise,
    )

