from typing import Literal

from pydantic import BaseModel, Field

from ..models import Span


class GraphEvidence(BaseModel):
    texto: str
    intervalo: Span
    origem: Literal["paragrafo", "contexto_anterior"] = "paragrafo"


class ScopeOperator(BaseModel):
    id: str
    tipo: Literal["negacao", "modalidade"]
    subtipo: str
    marcador: str
    escopo: list[str]
    evidencia: GraphEvidence
    confianca: float = Field(ge=0, le=1)


class AttributionSource(BaseModel):
    tipo: Literal["referente", "participante_discursivo", "nao_resolvida"]
    id: str
    rotulo: str


class AttributionFrame(BaseModel):
    id: str
    fonte: AttributionSource
    modo: Literal["assercao_narrativa", "pergunta", "pressuposicao", "fala_citada", "percepcao", "atitude_mental"]
    estado: Literal["afirmada", "questionada", "pressuposta", "citada", "percebida"]
    escopo: list[str]
    evidencias: list[GraphEvidence]
    confianca: float = Field(ge=0, le=1)


class PropositionRelation(BaseModel):
    id: str
    tipo: Literal[
        "coordenacao_negativa",
        "justificativa_causal",
        "conteudo_atitudinal",
        "complemento_modal",
        "caracterizacao_referente",
        "modo_processo",
        "concessao",
    ]
    origem_id: str
    destino_id: str
    marcador: str | None = None
    evidencia: GraphEvidence
    confianca: float = Field(ge=0, le=1)
    alternativas: list[str] = Field(default_factory=list)
