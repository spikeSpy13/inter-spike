from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisRequest(BaseModel):
    paragrafo: str = Field(max_length=5_000)
    contexto_anterior: str | None = Field(default=None, max_length=10_000)

    @field_validator("paragrafo")
    @classmethod
    def validar_paragrafo(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O parágrafo não pode estar vazio.")
        return value

    @field_validator("contexto_anterior")
    @classmethod
    def normalizar_contexto(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value if value.strip() else None


class Span(BaseModel):
    inicio: int = Field(ge=0)
    fim: int = Field(gt=0)
    unidade: Literal["pontos_de_codigo_unicode"] = "pontos_de_codigo_unicode"

    @model_validator(mode="after")
    def validar_ordem(self) -> Self:
        if self.fim <= self.inicio:
            raise ValueError("O fim do intervalo deve ser maior que o início.")
        return self


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
    estado: Literal["afirmada", "percebida", "citada", "questionada", "hipotetica", "pressuposta"]


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


class CentralIdeaAlternative(BaseModel):
    texto: str
    proposicao_ids: list[str]
    evidencias: list[Evidence]
    pontuacao: float = Field(ge=0, le=1)
    razoes: list[str]


class CentralIdea(BaseModel):
    estado: Literal["proposta", "indeterminada"]
    texto: str | None = None
    proposicao_ids: list[str] = Field(default_factory=list)
    evidencias: list[Evidence] = Field(default_factory=list)
    confianca: float = Field(ge=0, le=1)
    razoes: list[str]
    alternativas: list[CentralIdeaAlternative] = Field(default_factory=list)
    metodo: Literal["heuristica_explicavel_v1"] = "heuristica_explicavel_v1"


class SynthesisCoverage(BaseModel):
    proposicao_ids: list[str]
    operador_ids: list[str]
    relacao_ids: list[str]
    mencao_ids: list[str]


class Synthesis(BaseModel):
    estado: Literal["gerada", "indeterminada"]
    texto: str | None = None
    estrategia: Literal["extrativa_conteudo_essencial_v1"] = "extrativa_conteudo_essencial_v1"
    evidencias: list[Evidence] = Field(default_factory=list)
    cobertura: SynthesisCoverage
    confianca: float = Field(ge=0, le=1)
    alertas: list[str] = Field(default_factory=list)


class ParaphraseTransformation(BaseModel):
    tipo: Literal["equivalencia_discursiva"] = "equivalencia_discursiva"
    original: Evidence
    substituicao: str
    preserva_operador_ids: list[str] = Field(default_factory=list)
    preserva_relacao_ids: list[str] = Field(default_factory=list)


class Paraphrase(BaseModel):
    id: str
    texto: str
    proposicao_ids: list[str]
    evidencias: list[Evidence]
    cobertura: SynthesisCoverage
    transformacoes: list[ParaphraseTransformation]
    estrategia: Literal["substituicao_discursiva_controlada_v1"] = (
        "substituicao_discursiva_controlada_v1"
    )
    confianca: float = Field(ge=0, le=1)
    alertas: list[str] = Field(default_factory=list)


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
    conteudo_essencial: int
    sintese_caracteres: int
    parafrases: int


class AnalysisResponse(BaseModel):
    schema_version: Literal["0.8.0"] = "0.8.0"
    paragrafo: str
    contexto_anterior: str | None = None
    proposicoes: list[Proposition]
    mencoes: list["Mention"]
    referentes: list["Referent"]
    resolucoes: list["ReferenceResolution"]
    operadores_escopo: list["ScopeOperator"]
    quadros_atribuicao: list["AttributionFrame"]
    relacoes: list["PropositionRelation"]
    ideia_central: CentralIdea
    conteudo_essencial_ids: list[str]
    sintese: Synthesis
    parafrases: list[Paraphrase] = Field(default_factory=list)
    resumo: AnalysisSummary
    alertas: list[str]


class DocumentSource(BaseModel):
    documento_id: int | str
    schema_version: Literal["1.0.0"]
    etapa: Literal["09_vetorizacao"]
    caracteres_original: int


class DocumentParagraph(BaseModel):
    id: str
    rotulo: str
    ordem: int = Field(ge=0)
    texto: str
    intervalo_original: Span
    representacao_id: str
    artefato_id: str


class IngestionSummary(BaseModel):
    paragrafos: int
    periodos: int
    tokens: int
    representacoes: int
    artefatos: int
    dimensao_vetores: int


class IngestionResponse(BaseModel):
    schema_version: Literal["0.5.0"] = "0.5.0"
    fonte: DocumentSource
    paragrafos: list[DocumentParagraph]
    resumo: IngestionSummary


class JsonAnalysisRequest(BaseModel):
    documento: dict[str, Any]
    paragrafo_id: str = Field(min_length=1, max_length=500)


class JsonAnalysisResponse(BaseModel):
    schema_version: Literal["0.8.0"] = "0.8.0"
    fonte: DocumentSource
    paragrafo: DocumentParagraph
    analise: AnalysisResponse


from .referencias.models import Mention, Referent, ReferenceResolution  # noqa: E402
from .grafo.models import AttributionFrame, PropositionRelation, ScopeOperator  # noqa: E402

AnalysisResponse.model_rebuild()

