"""Geração extrativa de síntese com cobertura verificável."""

from __future__ import annotations

import re

from .grafo.models import PropositionRelation, ScopeOperator
from .models import (
    CentralIdea,
    Evidence,
    Proposition,
    Span,
    Synthesis,
    SynthesisCoverage,
)


SENTENCE_RE = re.compile(r"\s*[^.!?]+(?:[.!?]+(?=[\"”»']?(?:\s|$))|$)", re.UNICODE)


def _periodos(texto: str) -> list[tuple[int, int]]:
    periodos: list[tuple[int, int]] = []
    for match in SENTENCE_RE.finditer(texto):
        bruto = match.group()
        esquerda = len(bruto) - len(bruto.lstrip())
        inicio = match.start() + esquerda
        fim = match.end()
        if inicio < fim:
            periodos.append((inicio, fim))
    return periodos or [(0, len(texto))]


def _periodo_da_evidencia(
    periodos: list[tuple[int, int]],
    inicio: int,
    fim: int,
) -> tuple[int, int]:
    return next(
        (
            (inicio_periodo, fim_periodo)
            for inicio_periodo, fim_periodo in periodos
            if inicio_periodo <= inicio and fim <= fim_periodo
        ),
        (inicio, fim),
    )


def _ids_unicos(valores: list[str]) -> list[str]:
    return list(dict.fromkeys(valores))


def _abrange(evidencias: list[Evidence], inicio: int, fim: int) -> bool:
    return any(
        evidencia.intervalo.inicio <= inicio and fim <= evidencia.intervalo.fim
        for evidencia in evidencias
    )


def gerar_sintese(
    texto: str,
    proposicoes: list[Proposition],
    conteudo_essencial_ids: list[str],
    operadores: list[ScopeOperator],
    relacoes: list[PropositionRelation],
    ideia_central: CentralIdea,
) -> Synthesis:
    """Seleciona períodos originais que cobrem o conteúdo essencial e seus vínculos."""

    cobertura_vazia = SynthesisCoverage(
        proposicao_ids=[],
        operador_ids=[],
        relacao_ids=[],
        mencao_ids=[],
    )
    if not conteudo_essencial_ids:
        return Synthesis(
            estado="indeterminada",
            cobertura=cobertura_vazia,
            confianca=0,
            alertas=["Não há conteúdo essencial suficiente para gerar uma síntese."],
        )

    proposicoes_por_id = {item.id: item for item in proposicoes}
    ids_ausentes = [item for item in conteudo_essencial_ids if item not in proposicoes_por_id]
    if ids_ausentes:
        raise ValueError(f"Conteúdo essencial inexistente na geração: {ids_ausentes!r}.")
    essenciais = [proposicoes_por_id[item] for item in conteudo_essencial_ids]
    ids_essenciais = set(conteudo_essencial_ids)
    operadores_essenciais = [
        item for item in operadores if ids_essenciais.intersection(item.escopo)
    ]
    relacoes_essenciais = [
        item
        for item in relacoes
        if item.origem_id in ids_essenciais or item.destino_id in ids_essenciais
    ]
    mencao_ids = _ids_unicos(
        [
            participante.mencao_id
            for proposicao in essenciais
            for participante in proposicao.participantes
        ]
    )

    intervalos_necessarios = [
        (item.evidencia.intervalo.inicio, item.evidencia.intervalo.fim)
        for item in essenciais
    ]
    intervalos_necessarios.extend(
        (item.evidencia.intervalo.inicio, item.evidencia.intervalo.fim)
        for item in operadores_essenciais
    )
    intervalos_necessarios.extend(
        (item.evidencia.intervalo.inicio, item.evidencia.intervalo.fim)
        for item in relacoes_essenciais
    )

    periodos = _periodos(texto)
    intervalos_selecionados = sorted(
        {
            _periodo_da_evidencia(periodos, inicio, fim)
            for inicio, fim in intervalos_necessarios
        }
    )
    evidencias = [
        Evidence(
            texto=texto[inicio:fim],
            intervalo=Span(inicio=inicio, fim=fim),
        )
        for inicio, fim in intervalos_selecionados
    ]
    texto_sintese = " ".join(item.texto for item in evidencias)
    cobertura = SynthesisCoverage(
        proposicao_ids=conteudo_essencial_ids,
        operador_ids=[item.id for item in operadores_essenciais],
        relacao_ids=[item.id for item in relacoes_essenciais],
        mencao_ids=mencao_ids,
    )

    alertas: list[str] = []
    if len(evidencias) > 1:
        alertas.append(
            f"A síntese reúne {len(evidencias)} períodos não contíguos do original."
        )
    if any(
        evidencia.intervalo.inicio < proposicao.evidencia.intervalo.inicio
        or proposicao.evidencia.intervalo.fim < evidencia.intervalo.fim
        for proposicao in essenciais
        for evidencia in evidencias
        if _abrange(
            [evidencia],
            proposicao.evidencia.intervalo.inicio,
            proposicao.evidencia.intervalo.fim,
        )
    ):
        alertas.append(
            "O período completo foi preservado para manter o contexto do conteúdo essencial."
        )
    if ideia_central.confianca < 0.72:
        alertas.append("A síntese herda uma hipótese de ideia central que requer revisão.")

    sintese = Synthesis(
        estado="gerada",
        texto=texto_sintese,
        evidencias=evidencias,
        cobertura=cobertura,
        confianca=ideia_central.confianca,
        alertas=alertas,
    )
    validar_sintese(
        texto,
        proposicoes,
        conteudo_essencial_ids,
        operadores,
        relacoes,
        sintese,
    )
    return sintese


def validar_sintese(
    texto: str,
    proposicoes: list[Proposition],
    conteudo_essencial_ids: list[str],
    operadores: list[ScopeOperator],
    relacoes: list[PropositionRelation],
    sintese: Synthesis,
) -> None:
    if sintese.estado == "indeterminada":
        if sintese.texto is not None or sintese.evidencias:
            raise ValueError("Síntese indeterminada não pode conter texto ou evidências.")
        return
    if not sintese.texto or not sintese.evidencias:
        raise ValueError("Síntese gerada deve conter texto e evidências.")
    for evidencia in sintese.evidencias:
        intervalo = evidencia.intervalo
        if texto[intervalo.inicio : intervalo.fim] != evidencia.texto:
            raise ValueError("A evidência da síntese diverge do texto original.")
    if sintese.texto != " ".join(item.texto for item in sintese.evidencias):
        raise ValueError("A síntese contém texto sem apoio nas evidências selecionadas.")

    proposicoes_por_id = {item.id: item for item in proposicoes}
    if sintese.cobertura.proposicao_ids != conteudo_essencial_ids:
        raise ValueError("A síntese não declara todo o conteúdo essencial.")
    for proposicao_id in conteudo_essencial_ids:
        proposicao = proposicoes_por_id.get(proposicao_id)
        if proposicao is None:
            raise ValueError("A síntese aponta para proposição inexistente.")
        intervalo = proposicao.evidencia.intervalo
        if not _abrange(sintese.evidencias, intervalo.inicio, intervalo.fim):
            raise ValueError(f"A síntese não cobre a proposição essencial {proposicao_id}.")

    ids_essenciais = set(conteudo_essencial_ids)
    operadores_esperados = [
        item for item in operadores if ids_essenciais.intersection(item.escopo)
    ]
    relacoes_esperadas = [
        item
        for item in relacoes
        if item.origem_id in ids_essenciais or item.destino_id in ids_essenciais
    ]
    if sintese.cobertura.operador_ids != [item.id for item in operadores_esperados]:
        raise ValueError("A síntese não declara todos os operadores essenciais.")
    if sintese.cobertura.relacao_ids != [item.id for item in relacoes_esperadas]:
        raise ValueError("A síntese não declara todas as relações essenciais.")
    for item in [*operadores_esperados, *relacoes_esperadas]:
        intervalo = item.evidencia.intervalo
        if not _abrange(sintese.evidencias, intervalo.inicio, intervalo.fim):
            raise ValueError(f"A síntese não cobre a evidência de {item.id}.")

    mencoes_esperadas = _ids_unicos(
        [
            participante.mencao_id
            for proposicao_id in conteudo_essencial_ids
            for participante in proposicoes_por_id[proposicao_id].participantes
        ]
    )
    if sintese.cobertura.mencao_ids != mencoes_esperadas:
        raise ValueError("A síntese não declara todos os participantes essenciais.")
    for proposicao_id in conteudo_essencial_ids:
        for participante in proposicoes_por_id[proposicao_id].participantes:
            if not _abrange(
                sintese.evidencias,
                participante.intervalo.inicio,
                participante.intervalo.fim,
            ):
                raise ValueError(
                    f"A síntese não cobre o participante {participante.mencao_id}."
                )
