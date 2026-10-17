from __future__ import annotations

import re

from ..models import Participant, Proposition, Span
from ..referencias.models import Mention


PAPEL_PRINCIPAL = {
    "acreditar": "experienciador",
    "perceber": "experienciador",
    "pensar": "experienciador",
    "imaginar": "experienciador",
    "ver": "experienciador",
    "ouvir": "experienciador",
    "sentir": "experienciador",
    "gostar": "experienciador",
    "detestar": "experienciador",
    "esgotar": "tema",
    "ser": "tema",
    "estar": "tema",
    "ficar": "tema",
    "parecer": "tema",
    "permanecer": "tema",
    "morrer": "tema",
    "abandonar": "agente",
    "desistir": "agente",
    "frear": "agente",
    "construir": "agente",
    "transformar": "agente",
}

VERBOS_DE_ACAO = {
    "acenar", "achar", "afirmar", "apontar", "arrumar", "assinar", "atrasar",
    "atualizar", "bombardear", "buscar", "chamar", "chegar", "construir",
    "contar", "correr", "criticar", "dar", "decidir", "deixar", "demonstrar",
    "desistir", "dizer", "encontrar", "enviar", "enxugar", "escrever", "esperar",
    "exigir", "falar", "fazer", "imprimir", "insistir", "inspecionar", "ler",
    "mudar", "murmurar", "olhar", "passar", "pegar", "perguntar", "perder",
    "reagir", "responder", "retornar", "revisar", "sair", "secar", "segurar",
    "sentar", "tentar", "terminar", "tomar", "trabalhar", "viajar", "voltar",
}


def _participante(
    mencao: Mention, papel: str, referente_por_mencao: dict[str, str],
    funcao_sintatica: str | None = None,
) -> Participant:
    return Participant(
        papel=papel,
        mencao=mencao.texto,
        mencao_id=mencao.id,
        intervalo=Span(inicio=mencao.intervalo.inicio, fim=mencao.intervalo.fim),
        referente_id=referente_por_mencao.get(mencao.id),
        funcao_sintatica=funcao_sintatica,
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
        r"\b(?:foi|foram|era|eram|é|são|seria|seriam|ser|estava|estavam|sido|sendo)\s*$",
        prefixo,
        re.IGNORECASE,
    ))


def enriquecer_participantes(
    texto: str,
    proposicoes: list[Proposition],
    mencoes: list[Mention],
    referente_por_mencao: dict[str, str],
) -> None:
    passivas: dict[str, bool] = {}
    for indice, proposicao in enumerate(proposicoes):
        passiva = _esta_na_voz_passiva(texto, proposicao)
        if not passiva and proposicao.participantes and proposicao.forma_textual.casefold().endswith(("ado", "ada", "ados", "adas", "ido", "ida", "idos", "idas", "to", "ta", "tos", "tas")):
            anterior = next((
                item for item in reversed(proposicoes[:indice])
                if item.participantes
                and item.participantes[0].mencao_id == proposicao.participantes[0].mencao_id
            ), None)
            if anterior and passivas.get(anterior.id):
                entre = texto[anterior.predicado_intervalo.fim:proposicao.predicado_intervalo.inicio]
                passiva = bool(re.fullmatch(r"\s*(?:,|e|ou)\s+(?:não\s+)?", entre, re.IGNORECASE))
        passivas[proposicao.id] = passiva
        if proposicao.participantes:
            principal = proposicao.participantes[0]
            mencao_principal = next((item for item in mencoes if item.id == principal.mencao_id), None)
            if mencao_principal:
                papel = PAPEL_PRINCIPAL.get(proposicao.predicado, "participante_principal")
                if proposicao.predicado in VERBOS_DE_ACAO and mencao_principal.caracteristicas.classe_semantica == "pessoa":
                    papel = "agente"
                if passiva:
                    papel = "paciente"
                proposicao.participantes[0] = _participante(
                    mencao_principal, papel, referente_por_mencao, principal.funcao_sintatica,
                )

        existentes = {item.mencao_id for item in proposicao.participantes}
        proximo_predicado = min((
            item.predicado_intervalo.inicio for item in proposicoes
            if item.predicado_intervalo.inicio > proposicao.predicado_intervalo.inicio
        ), default=len(texto))
        limite_argumentos = proximo_predicado
        for posterior in proposicoes[indice + 1:]:
            if posterior.predicado_intervalo.inicio > proximo_predicado:
                break
            for sujeito in posterior.participantes:
                if sujeito.funcao_sintatica != "sujeito" or sujeito.intervalo.inicio <= proposicao.predicado_intervalo.fim:
                    continue
                entre = texto[proposicao.predicado_intervalo.fim:sujeito.intervalo.inicio]
                if re.search(r"\b(?:e|nem|mas|porém|ou)\b", entre, re.IGNORECASE):
                    limite_argumentos = min(limite_argumentos, sujeito.intervalo.inicio)
        candidatas = [
            item for item in _mencoes_na_evidencia(proposicao, mencoes)
            if item.id not in existentes
            and item.mencao_pai_id is None
            and item.intervalo.inicio >= proposicao.predicado_intervalo.fim
            and item.intervalo.fim <= limite_argumentos
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
