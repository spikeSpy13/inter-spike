from __future__ import annotations

from dataclasses import dataclass

from ..models import Proposition
from ..referencias.models import Mention
from ..referencias.resolvedor import ResolutionResult
from .atribuicoes import construir_quadros_atribuicao, vincular_possessivos_a_fontes
from .models import AttributionFrame, PropositionRelation, ScopeOperator
from .operadores import extrair_operadores_escopo
from .participantes import enriquecer_participantes
from .relacoes import extrair_relacoes
from .validator import validar_grafo


@dataclass(frozen=True)
class GraphResult:
    operadores: list[ScopeOperator]
    quadros_atribuicao: list[AttributionFrame]
    relacoes: list[PropositionRelation]


def construir_grafo(
    texto: str,
    contexto_anterior: str | None,
    proposicoes: list[Proposition],
    mencoes: list[Mention],
    referencias: ResolutionResult,
) -> GraphResult:
    vincular_possessivos_a_fontes(contexto_anterior, mencoes, referencias)
    enriquecer_participantes(texto, proposicoes, mencoes, referencias.referente_por_mencao)
    operadores = extrair_operadores_escopo(texto, proposicoes)
    quadros = construir_quadros_atribuicao(texto, proposicoes, mencoes)
    relacoes = extrair_relacoes(texto, proposicoes, mencoes, referencias.referente_por_mencao)
    validar_grafo(texto, proposicoes, referencias.referentes, operadores, quadros, relacoes)
    return GraphResult(operadores, quadros, relacoes)
