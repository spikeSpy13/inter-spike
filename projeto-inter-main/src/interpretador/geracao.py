"""Geração extrativa de síntese com cobertura verificável."""

from __future__ import annotations

import re

from .grafo.models import PropositionRelation, ScopeOperator
from .linguistica import analisar_texto
from .models import (
    CentralIdea,
    Evidence,
    Paraphrase,
    ParaphraseTransformation,
    Proposition,
    Span,
    Synthesis,
    SynthesisCoverage,
)


def _periodos(texto: str) -> list[tuple[int, int]]:
    return [(item.inicio, item.fim) for item in analisar_texto(texto).periodos]


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


def _evidencia_equivalente(
    evidencia: Evidence,
    inicio: int,
    fim: int,
) -> bool:
    return evidencia.intervalo.inicio == inicio and evidencia.intervalo.fim == fim


def _aplicar_transformacoes(
    texto: str,
    sintese: Synthesis,
    transformacoes: list[ParaphraseTransformation],
) -> str:
    partes: list[str] = []
    for evidencia in sintese.evidencias:
        inicio_evidencia = evidencia.intervalo.inicio
        fim_evidencia = evidencia.intervalo.fim
        aplicaveis = sorted(
            (
                item
                for item in transformacoes
                if inicio_evidencia <= item.original.intervalo.inicio
                and item.original.intervalo.fim <= fim_evidencia
            ),
            key=lambda item: item.original.intervalo.inicio,
        )
        cursor = inicio_evidencia
        trecho: list[str] = []
        for transformacao in aplicaveis:
            intervalo = transformacao.original.intervalo
            trecho.append(texto[cursor:intervalo.inicio])
            trecho.append(transformacao.substituicao)
            cursor = intervalo.fim
        trecho.append(texto[cursor:fim_evidencia])
        partes.append("".join(trecho))
    return " ".join(partes)


def gerar_parafrases(
    texto: str,
    proposicoes: list[Proposition],
    operadores: list[ScopeOperator],
    relacoes: list[PropositionRelation],
    sintese: Synthesis,
) -> list[Paraphrase]:
    """Gera apenas equivalências discursivas que podem ser validadas localmente."""

    if sintese.estado != "gerada":
        return []

    operadores_por_id = {item.id: item for item in operadores}
    relacoes_por_id = {item.id: item for item in relacoes}
    candidatos: list[ParaphraseTransformation] = []
    marcadores_processados: set[tuple[int, int]] = set()

    for operador_id in sintese.cobertura.operador_ids:
        operador = operadores_por_id[operador_id]
        if (
            operador.tipo == "negacao"
            and operador.subtipo == "coordenada"
            and operador.marcador.casefold() == "nem"
        ):
            intervalo = operador.evidencia.intervalo
            chave = (intervalo.inicio, intervalo.fim)
            if chave in marcadores_processados:
                continue
            relacao_ids = [
                item.id
                for item in relacoes
                if item.id in sintese.cobertura.relacao_ids
                and item.tipo == "coordenacao_negativa"
                and item.evidencia.intervalo == operador.evidencia.intervalo
            ]
            if relacao_ids:
                marcadores_processados.add(chave)
                operador_ids = [
                    item.id for item in operadores
                    if item.id in sintese.cobertura.operador_ids
                    and item.tipo == "negacao"
                    and item.subtipo == "coordenada"
                    and item.evidencia.intervalo == intervalo
                ]
                candidatos.append(ParaphraseTransformation(
                    original=Evidence(
                        texto=operador.evidencia.texto,
                        intervalo=operador.evidencia.intervalo,
                    ),
                    substituicao="e também não",
                    preserva_operador_ids=operador_ids,
                    preserva_relacao_ids=relacao_ids,
                ))

    equivalencias_causais = {"pois": "porque", "porque": "pois"}
    for relacao_id in sintese.cobertura.relacao_ids:
        relacao = relacoes_por_id[relacao_id]
        marcador = (relacao.marcador or "").casefold()
        if relacao.tipo != "justificativa_causal" or marcador not in equivalencias_causais:
            continue
        substituicao = equivalencias_causais[marcador]
        if relacao.marcador and relacao.marcador[0].isupper():
            substituicao = substituicao.capitalize()
        candidatos.append(ParaphraseTransformation(
            original=Evidence(
                texto=relacao.evidencia.texto,
                intervalo=relacao.evidencia.intervalo,
            ),
            substituicao=substituicao,
            preserva_relacao_ids=[relacao.id],
        ))

    parafrases: list[Paraphrase] = []
    for indice, transformacao in enumerate(candidatos, start=1):
        confiancas = [sintese.confianca]
        confiancas.extend(
            operadores_por_id[item].confianca
            for item in transformacao.preserva_operador_ids
        )
        confiancas.extend(
            relacoes_por_id[item].confianca
            for item in transformacao.preserva_relacao_ids
        )
        parafrase = Paraphrase(
            id=f"PF{indice}",
            texto=_aplicar_transformacoes(texto, sintese, [transformacao]),
            proposicao_ids=list(sintese.cobertura.proposicao_ids),
            evidencias=list(sintese.evidencias),
            cobertura=sintese.cobertura.model_copy(deep=True),
            transformacoes=[transformacao],
            confianca=round(max(0, min(confiancas) - 0.03), 2),
        )
        validar_parafrase(
            texto,
            proposicoes,
            operadores,
            relacoes,
            sintese,
            parafrase,
        )
        parafrases.append(parafrase)
    return parafrases


def validar_parafrase(
    texto: str,
    proposicoes: list[Proposition],
    operadores: list[ScopeOperator],
    relacoes: list[PropositionRelation],
    sintese: Synthesis,
    parafrase: Paraphrase,
) -> None:
    if sintese.estado != "gerada":
        raise ValueError("Não é possível validar paráfrase sem uma síntese gerada.")
    if not parafrase.texto or parafrase.texto == sintese.texto:
        raise ValueError("A paráfrase deve modificar a síntese de origem.")
    if not parafrase.transformacoes:
        raise ValueError("A paráfrase deve declarar ao menos uma transformação.")
    if parafrase.evidencias != sintese.evidencias:
        raise ValueError("A paráfrase deve manter as evidências da síntese de origem.")
    if parafrase.cobertura != sintese.cobertura:
        raise ValueError("A paráfrase deve manter toda a cobertura da síntese.")
    if parafrase.proposicao_ids != sintese.cobertura.proposicao_ids:
        raise ValueError("A paráfrase deve declarar todas as proposições essenciais.")

    proposicoes_por_id = {item.id: item for item in proposicoes}
    operadores_por_id = {item.id: item for item in operadores}
    relacoes_por_id = {item.id: item for item in relacoes}
    intervalos_anteriores: list[tuple[int, int]] = []
    for transformacao in sorted(
        parafrase.transformacoes,
        key=lambda item: item.original.intervalo.inicio,
    ):
        intervalo = transformacao.original.intervalo
        if texto[intervalo.inicio:intervalo.fim] != transformacao.original.texto:
            raise ValueError("A transformação da paráfrase diverge do texto original.")
        if not _abrange(parafrase.evidencias, intervalo.inicio, intervalo.fim):
            raise ValueError("A transformação fica fora das evidências da síntese.")
        if any(
            inicio < intervalo.fim and intervalo.inicio < fim
            for inicio, fim in intervalos_anteriores
        ):
            raise ValueError("As transformações da paráfrase não podem se sobrepor.")
        intervalos_anteriores.append((intervalo.inicio, intervalo.fim))

        for proposicao_id in parafrase.proposicao_ids:
            proposicao = proposicoes_por_id[proposicao_id]
            predicado = proposicao.predicado_intervalo
            if intervalo.inicio < predicado.fim and predicado.inicio < intervalo.fim:
                raise ValueError("A paráfrase não pode substituir um predicado essencial.")
            for participante in proposicao.participantes:
                participante_intervalo = participante.intervalo
                if (
                    intervalo.inicio < participante_intervalo.fim
                    and participante_intervalo.inicio < intervalo.fim
                ):
                    raise ValueError("A paráfrase não pode substituir um participante essencial.")

        original = transformacao.original.texto.casefold()
        substituicao = transformacao.substituicao.casefold()
        if original == "nem" and substituicao == "e também não":
            operadores_esperados = [
                item.id
                for item in operadores
                if item.id in parafrase.cobertura.operador_ids
                and item.tipo == "negacao"
                and item.subtipo == "coordenada"
                and _evidencia_equivalente(item.evidencia, intervalo.inicio, intervalo.fim)
            ]
            relacoes_esperadas = [
                item.id
                for item in relacoes
                if item.id in parafrase.cobertura.relacao_ids
                and item.tipo == "coordenacao_negativa"
                and _evidencia_equivalente(item.evidencia, intervalo.inicio, intervalo.fim)
            ]
        elif (original, substituicao) in {("pois", "porque"), ("porque", "pois")}:
            operadores_esperados = []
            relacoes_esperadas = [
                item.id
                for item in relacoes
                if item.id in parafrase.cobertura.relacao_ids
                and item.tipo == "justificativa_causal"
                and _evidencia_equivalente(item.evidencia, intervalo.inicio, intervalo.fim)
            ]
        else:
            raise ValueError("A paráfrase usa uma equivalência discursiva não autorizada.")

        if not operadores_esperados and not relacoes_esperadas:
            raise ValueError("A transformação não preserva um vínculo confirmado pelo grafo.")
        if transformacao.preserva_operador_ids != operadores_esperados:
            raise ValueError("A transformação não declara os operadores que preserva.")
        if transformacao.preserva_relacao_ids != relacoes_esperadas:
            raise ValueError("A transformação não declara as relações que preserva.")
        if not set(transformacao.preserva_operador_ids) <= operadores_por_id.keys():
            raise ValueError("A transformação aponta para operador inexistente.")
        if not set(transformacao.preserva_relacao_ids) <= relacoes_por_id.keys():
            raise ValueError("A transformação aponta para relação inexistente.")

    reconstruida = _aplicar_transformacoes(texto, sintese, parafrase.transformacoes)
    if parafrase.texto != reconstruida:
        raise ValueError("A paráfrase contém texto além das transformações declaradas.")
