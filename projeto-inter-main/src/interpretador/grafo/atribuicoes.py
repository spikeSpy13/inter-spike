from __future__ import annotations

import re

from ..models import Attribution, Proposition
from ..referencias.models import Mention, ReferenceEvidence
from ..referencias.resolvedor import ResolutionResult
from ..referencias.validator import validar_referencias
from .models import AttributionFrame, AttributionSource, GraphEvidence


VERBOS_FALA = r"(?:murmurou|disse|afirmou|contou|perguntou)"


def _evidencia_mencao(mencao: Mention) -> ReferenceEvidence:
    return ReferenceEvidence(
        mencao_id=mencao.id,
        texto=mencao.texto,
        origem=mencao.origem,
        intervalo=mencao.intervalo,
    )


def _ligar_mencao_a_fonte(
    mencao: Mention,
    fonte: Mention,
    resultado: ResolutionResult,
    confianca: float,
    razao: str,
) -> None:
    referente_id = resultado.referente_por_mencao.get(fonte.id)
    if not referente_id:
        return
    resolucao = next(item for item in resultado.resolucoes if item.mencao_id == mencao.id)
    referente = next(item for item in resultado.referentes if item.id == referente_id)
    anterior = resultado.referente_por_mencao.get(mencao.id)
    if anterior and anterior != referente_id:
        outro = next(item for item in resultado.referentes if item.id == anterior)
        outro.mencoes = [item for item in outro.mencoes if item != mencao.id]
    if mencao.id not in referente.mencoes:
        referente.mencoes.append(mencao.id)
    resultado.referente_por_mencao[mencao.id] = referente_id
    resolucao.referente_id = referente_id
    resolucao.estado = "resolvida"
    resolucao.tipo_relacao = "possuidor"
    resolucao.confianca = confianca
    resolucao.antecedente_mencao_id = fonte.id
    resolucao.razoes = [razao, "fonte da enunciação vinculada a um referente textual"]
    resolucao.evidencias = [_evidencia_mencao(fonte), _evidencia_mencao(mencao)]


def vincular_possessivos_a_fontes(
    contexto: str | None,
    mencoes: list[Mention],
    resultado: ResolutionResult,
) -> None:
    if not contexto:
        return
    mencoes_contexto = [item for item in mencoes if item.origem == "contexto_anterior"]
    for citacao in re.finditer(r'["“]([^"”]+)["”]', contexto, re.DOTALL):
        cauda_fim = contexto.find(".", citacao.end())
        if cauda_fim == -1:
            cauda_fim = min(len(contexto), citacao.end() + 180)
        cauda = contexto[citacao.end():cauda_fim]
        verbo = re.search(VERBOS_FALA, cauda, re.IGNORECASE)
        if not verbo:
            continue
        inicio_fonte = citacao.end() + verbo.end()
        fontes = [
            item for item in mencoes_contexto
            if item.caracteristicas.classe_semantica == "pessoa"
            and inicio_fonte <= item.intervalo.inicio < cauda_fim
            and resultado.referente_por_mencao.get(item.id)
        ]
        if not fontes:
            continue
        fonte = min(fontes, key=lambda item: item.intervalo.inicio)
        primeira_pessoa = [
            item for item in mencoes_contexto
            if citacao.start() < item.intervalo.inicio < citacao.end()
            and item.texto.casefold() in {"meu", "minha", "meus", "minhas"}
        ]
        for mencao in primeira_pessoa:
            _ligar_mencao_a_fonte(mencao, fonte, resultado, 0.94, "possessivo de primeira pessoa ligado ao falante da citação")

        continuidade = [
            item for item in mencoes_contexto
            if fonte.intervalo.fim < item.intervalo.inicio < cauda_fim
            and item.texto.casefold() in {"seu", "sua", "seus", "suas"}
        ]
        for mencao in continuidade:
            _ligar_mencao_a_fonte(mencao, fonte, resultado, 0.82, "possessivo retomado na continuidade do quadro de fala")
    resultado.referentes[:] = [item for item in resultado.referentes if item.mencoes]
    resolucoes_por_mencao = {item.mencao_id: item for item in resultado.resolucoes}
    for referente in resultado.referentes:
        referente.mencoes.sort(key=lambda item: int(item[1:]))
        valores = [
            resolucoes_por_mencao[item].confianca
            for item in referente.mencoes
            if item in resolucoes_por_mencao and resolucoes_por_mencao[item].referente_id == referente.id
        ]
        if valores:
            referente.confianca = round(sum(valores) / len(valores), 2)
    validar_referencias(mencoes, resultado.referentes, resultado.resolucoes)


def _dentro_de_descricao_complexa(proposicao: Proposition, mencoes: list[Mention]) -> bool:
    return any(
        item.origem == "paragrafo"
        and item.tipo == "descricao_complexa"
        and item.intervalo.inicio < proposicao.predicado_intervalo.inicio < item.intervalo.fim
        for item in mencoes
    )


def construir_quadros_atribuicao(
    texto: str,
    proposicoes: list[Proposition],
    mencoes: list[Mention],
) -> list[AttributionFrame]:
    grupos: dict[tuple[str, str, str], list[Proposition]] = {}
    for proposicao in proposicoes:
        if _dentro_de_descricao_complexa(proposicao, mencoes):
            chave = ("pressuposicao", "pressuposta", "ENUNCIADOR")
            proposicao.atribuicao = Attribution(
                fonte="enunciador",
                modo="informação de fundo",
                estado="afirmada",
            )
        elif "?" in proposicao.evidencia.texto:
            chave = ("pergunta", "questionada", "ENUNCIADOR")
            proposicao.atribuicao = Attribution(fonte="enunciador", modo="pergunta", estado="questionada")
        elif proposicao.atribuicao.modo in {"percepção", "conteúdo percebido"}:
            chave = ("percepcao", "percebida", "FONTE_NAO_RESOLVIDA")
        elif proposicao.atribuicao.modo == "atitude mental":
            chave = ("atitude_mental", "afirmada", "FONTE_NAO_RESOLVIDA")
        else:
            chave = ("assercao_narrativa", "afirmada", "NARRADOR")
        grupos.setdefault(chave, []).append(proposicao)

    quadros: list[AttributionFrame] = []
    for (modo, estado, fonte_id), escopo in grupos.items():
        tipo_fonte = "participante_discursivo" if fonte_id in {"NARRADOR", "ENUNCIADOR"} else "nao_resolvida"
        rotulo = "narrador" if fonte_id == "NARRADOR" else "enunciador" if fonte_id == "ENUNCIADOR" else "fonte não resolvida"
        evidencias: list[GraphEvidence] = []
        vistos: set[tuple[int, int]] = set()
        for proposicao in escopo:
            chave_intervalo = (proposicao.evidencia.intervalo.inicio, proposicao.evidencia.intervalo.fim)
            if chave_intervalo not in vistos:
                evidencias.append(GraphEvidence(
                    texto=proposicao.evidencia.texto,
                    intervalo=proposicao.evidencia.intervalo,
                ))
                vistos.add(chave_intervalo)
        quadro = AttributionFrame(
            id=f"A{len(quadros) + 1}",
            fonte=AttributionSource(tipo=tipo_fonte, id=fonte_id, rotulo=rotulo),
            modo=modo,
            estado=estado,
            escopo=[item.id for item in escopo],
            evidencias=evidencias,
            confianca=0.94 if tipo_fonte == "participante_discursivo" else 0.68,
        )
        quadros.append(quadro)
        for proposicao in escopo:
            proposicao.atribuicao_id = quadro.id
    return quadros
