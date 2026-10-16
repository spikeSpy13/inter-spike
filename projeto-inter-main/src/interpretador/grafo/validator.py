from __future__ import annotations

from ..models import Proposition
from ..referencias.models import Referent
from .models import AttributionFrame, PropositionRelation, ScopeOperator


def validar_grafo(
    texto: str,
    proposicoes: list[Proposition],
    referentes: list[Referent],
    operadores: list[ScopeOperator],
    quadros: list[AttributionFrame],
    relacoes: list[PropositionRelation],
) -> None:
    proposicao_ids = {item.id for item in proposicoes}
    referente_ids = {item.id for item in referentes}
    quadro_ids = {item.id for item in quadros}
    for operador in operadores:
        if not set(operador.escopo) <= proposicao_ids:
            raise ValueError(f"Escopo inválido no operador {operador.id}.")
        intervalo = operador.evidencia.intervalo
        if texto[intervalo.inicio:intervalo.fim] != operador.evidencia.texto:
            raise ValueError(f"Evidência inválida no operador {operador.id}.")
    for quadro in quadros:
        if not set(quadro.escopo) <= proposicao_ids:
            raise ValueError(f"Escopo inválido no quadro {quadro.id}.")
    for proposicao in proposicoes:
        if proposicao.atribuicao_id not in quadro_ids:
            raise ValueError(f"Proposição {proposicao.id} sem quadro de atribuição válido.")
    destinos_validos = proposicao_ids | referente_ids
    for relacao in relacoes:
        if relacao.origem_id not in destinos_validos or relacao.destino_id not in destinos_validos:
            raise ValueError(f"Extremidade inválida na relação {relacao.id}.")
        intervalo = relacao.evidencia.intervalo
        if texto[intervalo.inicio:intervalo.fim] != relacao.evidencia.texto:
            raise ValueError(f"Evidência inválida na relação {relacao.id}.")
