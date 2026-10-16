from __future__ import annotations

import re

from ..models import Participant, Proposition, Span
from ..referencias.models import Mention


PAPEL_PRINCIPAL = {
    "acreditar": "experienciador",
    "esgotar": "tema",
    "ser": "tema",
    "abandonar": "agente",
    "desistir": "agente",
    "frear": "agente",
    "construir": "agente",
    "transformar": "agente",
}


def _participante(mencao: Mention, papel: str, referente_por_mencao: dict[str, str]) -> Participant:
    return Participant(
        papel=papel,
        mencao=mencao.texto,
        mencao_id=mencao.id,
        intervalo=Span(inicio=mencao.intervalo.inicio, fim=mencao.intervalo.fim),
        referente_id=referente_por_mencao.get(mencao.id),
    )


def _mencoes_na_evidencia(proposicao: Proposition, mencoes: list[Mention]) -> list[Mention]:
    return sorted(
        [
            mencao for mencao in mencoes
            if mencao.origem == "paragrafo"
            and proposicao.evidencia.intervalo.inicio <= mencao.intervalo.inicio
            and mencao.intervalo.fim <= proposicao.evidencia.intervalo.fim
        ],
        key=lambda item: (item.intervalo.inicio, -(item.intervalo.fim - item.intervalo.inicio)),
    )


def _esta_na_voz_passiva(texto: str, proposicao: Proposition) -> bool:
    forma = proposicao.forma_textual.casefold()
    if not forma.endswith(("ado", "ada", "ados", "adas", "ido", "ida", "idos", "idas", "to", "ta", "tos", "tas")):
        return False
    prefixo = texto[proposicao.evidencia.intervalo.inicio:proposicao.predicado_intervalo.inicio]
    return bool(re.search(
        r"\b(?:foi|foram|era|eram|estava|estavam|tivesse|tinham|havia)"
        r"(?:\s+(?:sido|sendo))?\s*$",
        prefixo,
        re.IGNORECASE,
    ))


def enriquecer_participantes(
    texto: str,
    proposicoes: list[Proposition],
    mencoes: list[Mention],
    referente_por_mencao: dict[str, str],
) -> None:
    for proposicao in proposicoes:
        passiva = _esta_na_voz_passiva(texto, proposicao)
        if proposicao.participantes:
            principal = proposicao.participantes[0]
            mencao_principal = next((item for item in mencoes if item.id == principal.mencao_id), None)
            if mencao_principal:
                papel = "paciente" if passiva else PAPEL_PRINCIPAL.get(proposicao.predicado, "agente")
                proposicao.participantes[0] = _participante(mencao_principal, papel, referente_por_mencao)

        existentes = {item.mencao_id for item in proposicao.participantes}
        candidatas = [
            item for item in _mencoes_na_evidencia(proposicao, mencoes)
            if item.id not in existentes
            and item.mencao_pai_id is None
            and item.intervalo.inicio >= proposicao.predicado_intervalo.fim
            and not (
                item.intervalo.inicio <= proposicao.predicado_intervalo.inicio
                < item.intervalo.fim
            )
        ]

        for mencao in candidatas:
            entre = texto[proposicao.predicado_intervalo.fim:mencao.intervalo.inicio].casefold()
            papel: str | None = None
            if passiva and re.search(r"\b(?:por|pelo|pela|pelos|pelas)\s+$", entre):
                papel = "agente"
            elif proposicao.predicado == "enviar":
                if re.search(r"\bpor\s+$", entre):
                    papel = "agente"
                elif re.search(r"\b(?:ao|à|para)\s+$", entre):
                    papel = "destinatario"
                elif re.search(r"\b(?:através\s+de|por\s+meio\s+de)\s+$", entre):
                    papel = "meio"
                elif not passiva and not any(
                    item.papel == "paciente" for item in proposicao.participantes
                ):
                    papel = "paciente"
            elif proposicao.predicado in {"abandonar", "frear"}:
                papel = "paciente"
            elif proposicao.predicado in {"construir", "desistir"}:
                papel = "tema"

            if papel is None:
                continue
            proposicao.participantes.append(_participante(mencao, papel, referente_por_mencao))
            existentes.add(mencao.id)
            if proposicao.predicado != "enviar" and papel in {"paciente", "tema"}:
                break
