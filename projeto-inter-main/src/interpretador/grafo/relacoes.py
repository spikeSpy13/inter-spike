from __future__ import annotations

import re

from ..models import Proposition, Span
from ..referencias.models import Mention
from .models import GraphEvidence, PropositionRelation


def _evidencia(texto: str, inicio: int, fim: int) -> GraphEvidence:
    return GraphEvidence(texto=texto[inicio:fim], intervalo=Span(inicio=inicio, fim=fim))


def _marcador(texto: str, padrao: str, inicio: int, fim: int) -> tuple[str, GraphEvidence] | None:
    match = re.search(padrao, texto[inicio:fim], re.IGNORECASE)
    if not match:
        return None
    absoluto_inicio = inicio + match.start()
    absoluto_fim = inicio + match.end()
    return texto[absoluto_inicio:absoluto_fim], _evidencia(texto, absoluto_inicio, absoluto_fim)


def extrair_relacoes(
    texto: str,
    proposicoes: list[Proposition],
    mencoes: list[Mention],
    referente_por_mencao: dict[str, str],
) -> list[PropositionRelation]:
    relacoes: list[PropositionRelation] = []
    chaves: set[tuple[str, str, str]] = set()

    def adicionar(tipo: str, origem: str, destino: str, achado, confianca: float, alternativas=None):
        if not achado:
            return
        chave = (tipo, origem, destino)
        if chave in chaves:
            return
        marcador, evidencia = achado
        relacoes.append(PropositionRelation(
            id=f"L{len(relacoes) + 1}",
            tipo=tipo,
            origem_id=origem,
            destino_id=destino,
            marcador=marcador,
            evidencia=evidencia,
            confianca=confianca,
            alternativas=alternativas or [],
        ))
        chaves.add(chave)

    ordenadas = sorted(proposicoes, key=lambda item: item.predicado_intervalo.inicio)
    verbos_atitude = {"acreditar", "pensar", "imaginar", "perceber", "dizer", "afirmar", "contar"}
    for atual, proxima in zip(ordenadas, ordenadas[1:]):
        inicio = atual.predicado_intervalo.fim
        fim = proxima.predicado_intervalo.inicio
        adicionar(
            "coordenacao_negativa", atual.id, proxima.id,
            _marcador(texto, r"\bnem\b", inicio, fim),
            0.98,
        )
        adicionar(
            "justificativa_causal", atual.id, proxima.id,
            _marcador(texto, r"\b(?:pois|porque)\b", inicio, fim),
            0.93,
        )
        if atual.predicado in verbos_atitude:
            adicionar(
                "conteudo_atitudinal", atual.id, proxima.id,
                _marcador(texto, r"\bque\b", inicio, fim),
                0.88,
            )
        adicionar(
            "complemento_modal", atual.id, proxima.id,
            _marcador(texto, r"\bcapaz\s+de\b", inicio, fim),
            0.96,
        )
        if (
            proxima.forma_textual.casefold().endswith(("ando", "endo", "indo"))
            and proxima.evidencia.intervalo == atual.evidencia.intervalo
        ):
            adicionar(
                "modo_processo", atual.id, proxima.id,
                (proxima.forma_textual, _evidencia(texto, proxima.predicado_intervalo.inicio, proxima.predicado_intervalo.fim)),
                0.82,
            )

    for proposicao in ordenadas:
        complexa = next((
            item for item in mencoes
            if item.origem == "paragrafo"
            and item.tipo == "descricao_complexa"
            and item.intervalo.inicio < proposicao.predicado_intervalo.inicio < item.intervalo.fim
        ), None)
        if not complexa or proposicao.forma_textual.casefold().endswith(("ando", "endo", "indo")):
            continue
        referente_id = proposicao.participantes[0].referente_id if proposicao.participantes else None
        if referente_id:
            adicionar(
                "caracterizacao_referente", proposicao.id, referente_id,
                _marcador(texto, r"\bque\b", complexa.intervalo.inicio, proposicao.predicado_intervalo.inicio),
                0.89,
            )

    concessao = next((
        item for item in mencoes
        if item.origem == "paragrafo" and item.intervalo.inicio < 40
        and texto[:item.intervalo.inicio].casefold().strip().startswith("apesar")
    ), None)
    if concessao and ordenadas and referente_por_mencao.get(concessao.id):
        adicionar(
            "concessao", referente_por_mencao[concessao.id], ordenadas[0].id,
            _marcador(texto, r"\bApesar\b", 0, ordenadas[0].predicado_intervalo.inicio),
            0.91,
        )
    return relacoes
