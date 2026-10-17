from typing import Literal

from pydantic import BaseModel, Field

from ..models import Span


MentionOrigin = Literal["contexto_anterior", "paragrafo"]
MentionType = Literal[
    "nome_proprio",
    "descricao_nominal",
    "descricao_complexa",
    "pronome_pessoal",
    "pronome_possessivo",
]

ResolutionState = Literal["resolvida", "ambigua", "nao_resolvida", "novo_referente"]
ReferenceRelation = Literal["identidade", "possuidor", "introducao"]
PendingReason = Literal[
    "ambiguidade",
    "ausencia_antecedente",
    "candidatos_incompativeis",
    "evidencia_insuficiente",
    "exoforia",
    "fonte_fala_desconhecida",
]
ReferentType = Literal["entidade_textual", "participante_discursivo"]


class MentionFeatures(BaseModel):
    classe_semantica: Literal["pessoa", "objeto", "lugar", "evento", "desconhecida"]
    genero: Literal["feminino", "masculino", "indeterminado"]
    numero: Literal["singular", "plural", "indeterminado"]


class Mention(BaseModel):
    id: str
    texto: str
    tipo: MentionType
    origem: MentionOrigin
    intervalo: Span
    caracteristicas: MentionFeatures
    confianca_deteccao: float = Field(ge=0, le=1)
    mencao_pai_id: str | None = None


class ReferenceEvidence(BaseModel):
    mencao_id: str
    texto: str
    origem: MentionOrigin
    intervalo: Span


class ReferenceCandidate(BaseModel):
    antecedente_mencao_id: str
    referente_id: str
    pontuacao: float = Field(ge=0, le=1)
    razoes: list[str]


class ReferenceResolution(BaseModel):
    mencao_id: str
    referente_id: str | None = None
    estado: ResolutionState
    tipo_relacao: ReferenceRelation
    confianca: float = Field(ge=0, le=1)
    antecedente_mencao_id: str | None = None
    motivo_pendencia: PendingReason | None = None
    razoes: list[str]
    alternativas: list[ReferenceCandidate] = Field(default_factory=list)
    evidencias: list[ReferenceEvidence] = Field(default_factory=list)


class Referent(BaseModel):
    id: str
    rotulo: str
    classe_semantica: Literal["pessoa", "objeto", "lugar", "evento", "desconhecida"]
    tipo: ReferentType = "entidade_textual"
    mencoes: list[str]
    confianca: float = Field(ge=0, le=1)

