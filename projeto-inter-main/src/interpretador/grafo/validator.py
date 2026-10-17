from __future__ import annotations

from ..models import Proposition
from ..referencias.models import Mention, Referent
from .models import AttributionFrame, PropositionRelation, ScopeOperator


def validar_grafo(
    texto: str,
    proposicoes: list[Proposition],
    mencoes: list[Mention],
    referentes: list[Referent],
    operadores: list[ScopeOperator],
    quadros: list[AttributionFrame],
    relacoes: list[PropositionRelation],
) -> None:
    proposicao_ids = {item.id for item in proposicoes}
    mencoes_por_id = {item.id: item for item in mencoes}
    referente_ids = {item.id for item in referentes}
    quadro_ids = {item.id for item in quadros}
    for nome, itens in (
        ("proposição", proposicoes),
        ("operador", operadores),
        ("quadro", quadros),
        ("relação", relacoes),
    ):
        if len({item.id for item in itens}) != len(itens):
            raise ValueError(f"IDs de {nome} duplicados.")
    for proposicao in proposicoes:
        selecao = proposicao.sujeito
        if selecao:
            sujeitos = [item for item in proposicao.participantes if item.funcao_sintatica == "sujeito"]
            if selecao.estado == "identificado":
                mencao = mencoes_por_id.get(selecao.mencao_id)
                if not mencao or mencao.origem != "paragrafo":
                    raise ValueError(f"Sujeito de {proposicao.id} aponta para menção inválida.")
                if len(sujeitos) != 1 or sujeitos[0].mencao_id != selecao.mencao_id:
                    raise ValueError(f"Seleção e participante sujeito divergem em {proposicao.id}.")
            elif selecao.mencao_id is not None or sujeitos:
                raise ValueError(f"Sujeito indeterminado possui vínculo em {proposicao.id}.")
            for evidencia_sujeito in selecao.evidencias:
                intervalo = evidencia_sujeito.intervalo
                if texto[intervalo.inicio:intervalo.fim] != evidencia_sujeito.texto:
                    raise ValueError(f"Evidência do sujeito inválida em {proposicao.id}.")
        evidencia = proposicao.evidencia
        if texto[evidencia.intervalo.inicio:evidencia.intervalo.fim] != evidencia.texto:
            raise ValueError(f"Evidência inválida na proposição {proposicao.id}.")
        if texto[proposicao.predicado_intervalo.inicio:proposicao.predicado_intervalo.fim] != proposicao.forma_textual:
            raise ValueError(f"Intervalo do predicado inválido em {proposicao.id}.")
        for participante in proposicao.participantes:
            mencao = mencoes_por_id.get(participante.mencao_id)
            if mencao is None:
                raise ValueError(f"Participante de {proposicao.id} aponta para menção inexistente.")
            if participante.intervalo != mencao.intervalo or participante.mencao != mencao.texto:
                raise ValueError(f"Participante de {proposicao.id} diverge da menção original.")
            if participante.referente_id and participante.referente_id not in referente_ids:
                raise ValueError(f"Participante de {proposicao.id} aponta para referente inexistente.")
    for operador in operadores:
        if not set(operador.escopo) <= proposicao_ids:
            raise ValueError(f"Escopo inválido no operador {operador.id}.")
        intervalo = operador.evidencia.intervalo
        if texto[intervalo.inicio:intervalo.fim] != operador.evidencia.texto:
            raise ValueError(f"Evidência inválida no operador {operador.id}.")
    for quadro in quadros:
        if not set(quadro.escopo) <= proposicao_ids:
            raise ValueError(f"Escopo inválido no quadro {quadro.id}.")
        if quadro.fonte.tipo == "referente" and quadro.fonte.id not in referente_ids:
            raise ValueError(f"Fonte inexistente no quadro {quadro.id}.")
        for evidencia in quadro.evidencias:
            intervalo = evidencia.intervalo
            if texto[intervalo.inicio:intervalo.fim] != evidencia.texto:
                raise ValueError(f"Evidência inválida no quadro {quadro.id}.")
    for proposicao in proposicoes:
        if proposicao.atribuicao_id not in quadro_ids:
            raise ValueError(f"Proposição {proposicao.id} sem quadro de atribuição válido.")
        quadro = next(item for item in quadros if item.id == proposicao.atribuicao_id)
        if proposicao.atribuicao.estado != quadro.estado:
            raise ValueError(f"Estado de atribuição divergente em {proposicao.id}.")
    destinos_validos = proposicao_ids | referente_ids
    for relacao in relacoes:
        if relacao.origem_id not in destinos_validos or relacao.destino_id not in destinos_validos:
            raise ValueError(f"Extremidade inválida na relação {relacao.id}.")
        intervalo = relacao.evidencia.intervalo
        if texto[intervalo.inicio:intervalo.fim] != relacao.evidencia.texto:
            raise ValueError(f"Evidência inválida na relação {relacao.id}.")
