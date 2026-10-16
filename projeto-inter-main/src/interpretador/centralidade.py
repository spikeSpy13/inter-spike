"""Seleção explicável de uma hipótese de ideia central."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .grafo.models import PropositionRelation
from .models import (
    CentralIdea,
    CentralIdeaAlternative,
    Evidence,
    Proposition,
    Span,
)


@dataclass
class _Candidato:
    proposicoes: list[Proposition]
    inicio: int
    fim: int
    texto: str
    pontuacao: float = 0
    razoes: list[str] | None = None

    @property
    def ids(self) -> list[str]:
        return [item.id for item in self.proposicoes]

    def evidencia(self) -> Evidence:
        return Evidence(
            texto=self.texto,
            intervalo=Span(inicio=self.inicio, fim=self.fim),
        )


PESOS_RELACOES = {
    "coordenacao_negativa": 0.09,
    "justificativa_causal": 0.08,
    "conteudo_atitudinal": 0.08,
    "complemento_modal": 0.07,
    "concessao": 0.08,
    "modo_processo": 0.05,
    "caracterizacao_referente": 0.03,
}

PREDICADOS_SUPORTE = {"ser", "estar", "ter", "haver"}


def _agrupar(proposicoes: list[Proposition]) -> list[_Candidato]:
    grupos: dict[tuple[int, int], list[Proposition]] = {}
    for proposicao in proposicoes:
        intervalo = proposicao.evidencia.intervalo
        grupos.setdefault((intervalo.inicio, intervalo.fim), []).append(proposicao)
    return [
        _Candidato(
            proposicoes=grupo,
            inicio=inicio,
            fim=fim,
            texto=grupo[0].evidencia.texto,
        )
        for (inicio, fim), grupo in sorted(grupos.items())
    ]


def _pontuar(
    candidatos: list[_Candidato],
    proposicoes: list[Proposition],
    relacoes: list[PropositionRelation],
) -> None:
    if not candidatos:
        return
    primeira_posicao = min(item.inicio for item in candidatos)
    ultima_posicao = max(item.inicio for item in candidatos)
    frequencia_referentes = Counter(
        participante.referente_id
        for proposicao in proposicoes
        for participante in proposicao.participantes
        if participante.referente_id
    )

    for candidato in candidatos:
        ids = set(candidato.ids)
        media_confianca = sum(item.confianca for item in candidato.proposicoes) / len(candidato.proposicoes)
        pontuacao = 0.28 + 0.35 * media_confianca
        razoes: list[str] = []

        if candidato.inicio == primeira_posicao:
            pontuacao += 0.07
            razoes.append("O trecho introduz o desenvolvimento proposicional do parágrafo.")
        if candidato.inicio == ultima_posicao and len(candidatos) > 1:
            pontuacao += 0.04
            razoes.append("O trecho ocupa a posição de fechamento do parágrafo.")
        if len(candidato.proposicoes) > 1:
            pontuacao += min(0.06, 0.02 * (len(candidato.proposicoes) - 1))
            razoes.append(
                f"O mesmo trecho sustenta {len(candidato.proposicoes)} proposições relacionadas."
            )

        estados = {item.atribuicao.estado for item in candidato.proposicoes}
        if "afirmada" in estados:
            pontuacao += 0.06
            razoes.append("O conteúdo é apresentado como afirmado no registro discursivo.")
        elif "percebida" in estados:
            pontuacao += 0.04
            razoes.append("O conteúdo integra um quadro explícito de percepção.")
        elif estados == {"questionada"}:
            pontuacao += 0.01
            razoes.append("O conteúdo aparece como pergunta e exige revisão de sua força discursiva.")
        if estados == {"pressuposta"}:
            pontuacao -= 0.10
            razoes.append("O trecho funciona como informação pressuposta de apoio.")
        if estados == {"citada"}:
            pontuacao -= 0.06
            razoes.append("O trecho pertence a uma fala citada, com fonte separada do narrador.")

        if any(item.polaridade == "negativa" for item in candidato.proposicoes):
            pontuacao += 0.05
            razoes.append("A polaridade negativa é estrutural para o conteúdo deste trecho.")
        if all(item.predicado in PREDICADOS_SUPORTE for item in candidato.proposicoes):
            pontuacao -= 0.06
            razoes.append("O grupo contém apenas predicados de suporte semântico.")

        referentes_do_grupo = {
            participante.referente_id
            for item in candidato.proposicoes
            for participante in item.participantes
            if participante.referente_id
        }
        if any(frequencia_referentes[referente_id] > 1 for referente_id in referentes_do_grupo):
            pontuacao += 0.04
            razoes.append("O trecho retoma um participante recorrente no parágrafo.")

        tipos_relacionados: set[str] = set()
        bonus_relacoes = 0.0
        for relacao in relacoes:
            origem_no_grupo = relacao.origem_id in ids
            destino_no_grupo = relacao.destino_id in ids
            if not origem_no_grupo and not destino_no_grupo:
                continue
            peso = PESOS_RELACOES.get(relacao.tipo, 0.02)
            if origem_no_grupo and destino_no_grupo:
                bonus_relacoes += peso
            elif relacao.tipo == "justificativa_causal":
                bonus_relacoes += peso if origem_no_grupo else peso * 0.35
            elif relacao.tipo in {"conteudo_atitudinal", "complemento_modal"}:
                bonus_relacoes += peso if destino_no_grupo else peso * 0.30
            elif relacao.tipo == "modo_processo":
                bonus_relacoes += peso if origem_no_grupo else peso * 0.30
            elif relacao.tipo == "concessao":
                bonus_relacoes += peso if destino_no_grupo else peso * 0.25
            else:
                bonus_relacoes += peso * 0.50
            tipos_relacionados.add(relacao.tipo)
        if tipos_relacionados:
            pontuacao += min(0.16, bonus_relacoes)
            tipos = ", ".join(sorted(tipo.replace("_", " ") for tipo in tipos_relacionados))
            razoes.append(f"O grafo liga o trecho por: {tipos}.")

        candidato.pontuacao = round(max(0.05, min(0.98, pontuacao)), 3)
        candidato.razoes = razoes or ["O trecho contém uma proposição com evidência textual válida."]


def _alternativa(candidato: _Candidato) -> CentralIdeaAlternative:
    return CentralIdeaAlternative(
        texto=candidato.texto,
        proposicao_ids=candidato.ids,
        evidencias=[candidato.evidencia()],
        pontuacao=candidato.pontuacao,
        razoes=candidato.razoes or [],
    )


def propor_ideia_central(
    texto: str,
    proposicoes: list[Proposition],
    relacoes: list[PropositionRelation],
) -> tuple[CentralIdea, list[str]]:
    """Propõe conteúdo central sem inventar texto além dos trechos de evidência."""

    if not proposicoes:
        return (
            CentralIdea(
                estado="indeterminada",
                confianca=0,
                razoes=["Não há proposições suficientes para propor uma ideia central."],
            ),
            [],
        )

    candidatos = _agrupar(proposicoes)
    _pontuar(candidatos, proposicoes, relacoes)
    candidatos.sort(key=lambda item: (-item.pontuacao, item.inicio, item.fim))
    principal = candidatos[0]
    segunda_pontuacao = candidatos[1].pontuacao if len(candidatos) > 1 else 0
    margem = max(0.0, principal.pontuacao - segunda_pontuacao)
    confianca = round(
        max(0.45, min(0.90, 0.38 + 0.35 * principal.pontuacao + 0.60 * margem)),
        2,
    )
    razoes = list(principal.razoes or [])
    if len(candidatos) > 1 and margem < 0.05:
        razoes.append("A alternativa mais próxima recebeu pontuação semelhante; a escolha requer revisão.")

    ideia = CentralIdea(
        estado="proposta",
        texto=principal.texto,
        proposicao_ids=principal.ids,
        evidencias=[principal.evidencia()],
        confianca=confianca,
        razoes=razoes,
        alternativas=[_alternativa(item) for item in candidatos[1:3]],
    )
    conteudo_essencial_ids = principal.ids
    validar_ideia_central(texto, proposicoes, ideia, conteudo_essencial_ids)
    return ideia, conteudo_essencial_ids


def validar_ideia_central(
    texto: str,
    proposicoes: list[Proposition],
    ideia: CentralIdea,
    conteudo_essencial_ids: list[str],
) -> None:
    ids_validos = {item.id for item in proposicoes}
    if len(conteudo_essencial_ids) != len(set(conteudo_essencial_ids)):
        raise ValueError("O conteúdo essencial contém IDs duplicados.")
    if not set(conteudo_essencial_ids) <= ids_validos:
        raise ValueError("O conteúdo essencial aponta para proposição inexistente.")
    if ideia.proposicao_ids != conteudo_essencial_ids:
        raise ValueError("A ideia central e o conteúdo essencial devem apontar para os mesmos IDs.")
    for evidencia in ideia.evidencias:
        intervalo = evidencia.intervalo
        if texto[intervalo.inicio : intervalo.fim] != evidencia.texto:
            raise ValueError("A evidência da ideia central diverge do texto original.")
    for alternativa in ideia.alternativas:
        if not set(alternativa.proposicao_ids) <= ids_validos:
            raise ValueError("Uma alternativa aponta para proposição inexistente.")
        for evidencia in alternativa.evidencias:
            intervalo = evidencia.intervalo
            if texto[intervalo.inicio : intervalo.fim] != evidencia.texto:
                raise ValueError("A evidência de uma alternativa diverge do texto original.")
