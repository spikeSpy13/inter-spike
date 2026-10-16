from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    paragrafo: str = Field(max_length=5_000)
    contexto_anterior: str | None = Field(default=None, max_length=10_000)

    @field_validator("paragrafo")
    @classmethod
    def validar_paragrafo(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O parágrafo não pode estar vazio.")
        return value

    @field_validator("contexto_anterior")
    @classmethod
    def normalizar_contexto(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class Span(BaseModel):
    inicio: int = Field(ge=0)
    fim: int = Field(gt=0)
    unidade: Literal["pontos_de_codigo_unicode"] = "pontos_de_codigo_unicode"


class Evidence(BaseModel):
    texto: str
    intervalo: Span


class Participant(BaseModel):
    papel: str
    mencao: str
    mencao_id: str
    intervalo: Span
    referente_id: str | None = None


class Operators(BaseModel):
    negacao: str | None = None
    modalidade: str | None = None


class Attribution(BaseModel):
    fonte: str
    modo: str
    estado: Literal["afirmada", "percebida", "citada", "questionada", "hipotetica"]


class Proposition(BaseModel):
    id: str
    predicado: str
    forma_textual: str
    predicado_intervalo: Span
    descricao: str
    participantes: list[Participant]
    operadores: Operators
    atribuicao: Attribution
    atribuicao_id: str | None = None
    polaridade: Literal["positiva", "negativa"] = "positiva"
    evidencia: Evidence
    confianca: float = Field(ge=0, le=1)


class AnalysisSummary(BaseModel):
    proposicoes: int
    mencoes: int
    referentes: int
    resolucoes_resolvidas: int
    resolucoes_ambiguas: int
    operadores: int
    relacoes: int
    negacoes: int
    atribuicoes_marcadas: int


class AnalysisResponse(BaseModel):
    schema_version: Literal["0.4.0"] = "0.4.0"
    paragrafo: str
    contexto_anterior: str | None = None
    proposicoes: list[Proposition]
    mencoes: list["Mention"]
    referentes: list["Referent"]
    resolucoes: list["ReferenceResolution"]
    operadores_escopo: list["ScopeOperator"]
    quadros_atribuicao: list["AttributionFrame"]
    relacoes: list["PropositionRelation"]
    resumo: AnalysisSummary
    alertas: list[str]


from .referencias.models import Mention, Referent, ReferenceResolution  # noqa: E402
from .grafo.models import AttributionFrame, PropositionRelation, ScopeOperator  # noqa: E402

AnalysisResponse.model_rebuild()

