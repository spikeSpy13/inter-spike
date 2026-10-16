from __future__ import annotations

import re

from ..models import Proposition, Span
from .models import GraphEvidence, ScopeOperator


def _evidencia(texto: str, inicio: int, fim: int) -> GraphEvidence:
    return GraphEvidence(texto=texto[inicio:fim], intervalo=Span(inicio=inicio, fim=fim))


def _proxima(proposicoes: list[Proposition], atual: Proposition) -> Proposition | None:
    posteriores = [
        item for item in proposicoes
        if item.predicado_intervalo.inicio > atual.predicado_intervalo.inicio
        and item.evidencia.intervalo == atual.evidencia.intervalo
    ]
    return min(posteriores, key=lambda item: item.predicado_intervalo.inicio, default=None)


def extrair_operadores_escopo(texto: str, proposicoes: list[Proposition]) -> list[ScopeOperator]:
    operadores: list[ScopeOperator] = []
    modalidades_por_proposicao: dict[str, list[str]] = {item.id: [] for item in proposicoes}

    for proposicao in proposicoes:
        marcador = proposicao.operadores.negacao
        if marcador:
            janela_inicio = proposicao.evidencia.intervalo.inicio
            janela = texto[janela_inicio:proposicao.predicado_intervalo.inicio]
            ocorrencias = list(re.finditer(rf"\b{re.escape(marcador)}\b", janela, re.IGNORECASE))
            if ocorrencias:
                match = ocorrencias[-1]
                inicio = janela_inicio + match.start()
                fim = janela_inicio + match.end()
                operadores.append(ScopeOperator(
                    id=f"O{len(operadores) + 1}",
                    tipo="negacao",
                    subtipo="sentencial" if marcador != "nem" else "coordenada",
                    marcador=texto[inicio:fim],
                    escopo=[proposicao.id],
                    evidencia=_evidencia(texto, inicio, fim),
                    confianca=0.96,
                ))
                proposicao.polaridade = "negativa"

        forma = proposicao.forma_textual.casefold()
        if forma in {"seria", "poderia", "deveria"}:
            escopo = [proposicao.id]
            complemento = _proxima(proposicoes, proposicao)
            entre = texto[proposicao.predicado_intervalo.fim:complemento.predicado_intervalo.inicio].casefold() if complemento else ""
            if complemento and re.search(r"\b(?:capaz\s+de|de)\b", entre):
                escopo.append(complemento.id)
            subtipo = "irrealis_condicional" if forma == "seria" else "possibilidade" if forma == "poderia" else "expectativa"
            operadores.append(ScopeOperator(
                id=f"O{len(operadores) + 1}",
                tipo="modalidade",
                subtipo=subtipo,
                marcador=proposicao.forma_textual,
                escopo=escopo,
                evidencia=_evidencia(texto, proposicao.predicado_intervalo.inicio, proposicao.predicado_intervalo.fim),
                confianca=0.91,
            ))
            for proposicao_id in escopo:
                modalidades_por_proposicao[proposicao_id].append(subtipo)

        trecho = texto[proposicao.predicado_intervalo.fim:proposicao.evidencia.intervalo.fim]
        capaz = re.search(r"\bcapaz\s+de\b", trecho, re.IGNORECASE)
        complemento = _proxima(proposicoes, proposicao)
        if capaz and complemento and proposicao.predicado == "ser":
            inicio = proposicao.predicado_intervalo.fim + capaz.start()
            fim = proposicao.predicado_intervalo.fim + capaz.end()
            operadores.append(ScopeOperator(
                id=f"O{len(operadores) + 1}",
                tipo="modalidade",
                subtipo="capacidade_dinamica",
                marcador=texto[inicio:fim],
                escopo=[complemento.id],
                evidencia=_evidencia(texto, inicio, fim),
                confianca=0.95,
            ))
            modalidades_por_proposicao[complemento.id].append("capacidade_dinamica")

        prefixo = texto[proposicao.evidencia.intervalo.inicio:proposicao.predicado_intervalo.inicio]
        talvez = list(re.finditer(r"\btalvez\b", prefixo, re.IGNORECASE))
        if talvez:
            match = talvez[-1]
            inicio = proposicao.evidencia.intervalo.inicio + match.start()
            fim = proposicao.evidencia.intervalo.inicio + match.end()
            operadores.append(ScopeOperator(
                id=f"O{len(operadores) + 1}",
                tipo="modalidade",
                subtipo="possibilidade_epistemica",
                marcador=texto[inicio:fim],
                escopo=[proposicao.id],
                evidencia=_evidencia(texto, inicio, fim),
                confianca=0.94,
            ))
            modalidades_por_proposicao[proposicao.id].append("possibilidade_epistemica")

    for proposicao in proposicoes:
        modalidades = modalidades_por_proposicao[proposicao.id]
        proposicao.operadores.modalidade = " + ".join(modalidades) if modalidades else None
    return operadores
