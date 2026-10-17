from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Attribution, Proposition
from ..referencias.models import Mention, ReferenceEvidence
from ..referencias.resolvedor import ResolutionResult
from ..referencias.validator import validar_referencias
from .models import AttributionFrame, AttributionSource, GraphEvidence


VERBOS_FALA = r"(?:murmurou|disse|afirmou|contou|perguntou)"
_CITACOES = re.compile(r'"[^"]*"|“[^”]*”', re.DOTALL)
_VERBO_FALA = re.compile(rf"\b{VERBOS_FALA}\b", re.IGNORECASE)
_DESTINATARIO_ANTES_CITACAO = re.compile(
    r"\s+(?:a|ao|à|para)\s+(?:(?:o|a)\s+)?"
    r"(?:[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][^\W\d_]*(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][^\W\d_]*)*"
    r"|ele|ela|eles|elas|mim|ti|você)\s*:\s*",
)


@dataclass(frozen=True)
class _EnquadramentoCitacao:
    inicio: int
    fim: int
    verbo_inicio: int | None = None
    verbo_fim: int | None = None


def _enquadrar_citacoes(texto: str) -> list[_EnquadramentoCitacao]:
    """Liga somente relatoras adjacentes a um par efetivo de aspas.

    Uma relatora próxima em outra oração/período não basta para identificar
    o falante. O mesmo recorte sustenta o quadro do grafo e os possessivos.
    """
    citacoes = list(_CITACOES.finditer(texto))
    verbos = [
        verbo for verbo in _VERBO_FALA.finditer(texto)
        if not any(citacao.start() < verbo.start() < citacao.end() for citacao in citacoes)
    ]
    quadros = []
    for citacao in citacoes:
        posteriores = [
            verbo for verbo in verbos
            if verbo.start() >= citacao.end()
            and re.fullmatch(r"\s*[,—–-]\s*", texto[citacao.end():verbo.start()])
        ]
        anteriores = [
            verbo for verbo in verbos
            if verbo.end() <= citacao.start()
            and (
                re.fullmatch(r"\s*(?::|[,—–-])?\s*", texto[verbo.end():citacao.start()])
                or _DESTINATARIO_ANTES_CITACAO.fullmatch(texto[verbo.end():citacao.start()])
            )
        ]
        relatora = posteriores[0] if posteriores else anteriores[-1] if anteriores else None
        quadros.append(_EnquadramentoCitacao(
            inicio=citacao.start(), fim=citacao.end(),
            verbo_inicio=relatora.start() if relatora else None,
            verbo_fim=relatora.end() if relatora else None,
        ))
    return quadros


def _mencao_falante(
    texto: str,
    quadro: _EnquadramentoCitacao,
    mencoes: list[Mention],
    resultado: ResolutionResult,
) -> Mention | None:
    if quadro.verbo_inicio is None or quadro.verbo_fim is None:
        return None
    pessoas = [
        item for item in mencoes
        if item.caracteristicas.classe_semantica == "pessoa"
        and item.mencao_pai_id is None
        and resultado.referente_por_mencao.get(item.id)
        and not (quadro.inicio < item.intervalo.inicio < quadro.fim)
    ]
    # A fonte pode preceder a relatora ("Ana disse:") ou segui-la
    # ("..., disse Ana"). Não atravessamos outros constituintes.
    anteriores = [
        item for item in pessoas
        if item.intervalo.fim <= quadro.verbo_inicio
        and re.fullmatch(
            r"\s*(?:(?:não|então|ainda|também|finalmente)\s+)*",
            texto[item.intervalo.fim:quadro.verbo_inicio], re.IGNORECASE,
        )
    ]
    posteriores = [
        item for item in pessoas
        if item.intervalo.inicio >= quadro.verbo_fim
        and re.fullmatch(r"\s*", texto[quadro.verbo_fim:item.intervalo.inicio])
    ]
    if anteriores:
        return max(anteriores, key=lambda item: item.intervalo.fim)
    return min(posteriores, key=lambda item: item.intervalo.inicio) if posteriores else None


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
    texto: str,
    contexto: str | None,
    mencoes: list[Mention],
    resultado: ResolutionResult,
) -> None:
    fontes_textuais = [(texto, "paragrafo")]
    if contexto:
        fontes_textuais.insert(0, (contexto, "contexto_anterior"))
    for fonte_texto, origem in fontes_textuais:
        mencoes_origem = [item for item in mencoes if item.origem == origem]
        citacoes = _enquadrar_citacoes(fonte_texto)
        for citacao in citacoes:
            fonte = _mencao_falante(fonte_texto, citacao, mencoes_origem, resultado)
            if fonte is None:
                continue
            primeira_pessoa = [
                item for item in mencoes_origem
                if citacao.inicio < item.intervalo.inicio < citacao.fim
                and item.texto.casefold() in {"meu", "minha", "meus", "minhas"}
            ]
            for mencao in primeira_pessoa:
                _ligar_mencao_a_fonte(mencao, fonte, resultado, 0.94, "possessivo de primeira pessoa ligado ao falante da citação")

            # A continuidade do relato posposto termina no período, numa
            # nova citação ou numa mudança explícita de sujeito humano.
            if citacao.verbo_inicio is None or citacao.verbo_inicio < citacao.fim:
                continue
            limite = re.search(r"[.!?;]|\b(?:mas|porém|entretanto|contudo)\b", fonte_texto[fonte.intervalo.fim:], re.IGNORECASE)
            cauda_fim = fonte.intervalo.fim + limite.start() if limite else len(fonte_texto)
            cauda_fim = min([cauda_fim, *[item.inicio for item in citacoes if item.inicio >= fonte.intervalo.fim]])
            continuidade = [
                item for item in mencoes_origem
                if fonte.intervalo.fim < item.intervalo.inicio < cauda_fim
                and item.texto.casefold() in {"seu", "sua", "seus", "suas"}
                and not any(
                    outra.caracteristicas.classe_semantica == "pessoa"
                    and fonte.intervalo.fim < outra.intervalo.inicio < item.intervalo.inicio
                    and resultado.referente_por_mencao.get(outra.id) not in {
                        None, resultado.referente_por_mencao.get(fonte.id),
                    }
                    for outra in mencoes_origem
                )
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
    citacoes = _enquadrar_citacoes(texto)
    mencoes_por_id = {item.id: item for item in mencoes}
    rotulos_fontes: dict[str, str] = {}
    prioridades_rotulos: dict[str, int] = {}
    for proposicao in proposicoes:
        for participante in proposicao.participantes:
            if participante.referente_id:
                mencao = mencoes_por_id.get(participante.mencao_id)
                prioridade = (
                    3 if mencao and mencao.tipo == "nome_proprio"
                    else 2 if mencao and mencao.tipo in {"descricao_nominal", "descricao_complexa"}
                    else 1
                )
                if prioridade > prioridades_rotulos.get(participante.referente_id, 0):
                    prioridades_rotulos[participante.referente_id] = prioridade
                    rotulos_fontes[participante.referente_id] = participante.mencao

    def fonte_da_proposicao(proposicao: Proposition) -> str:
        return next(
            (
                participante.referente_id
                for participante in proposicao.participantes
                if participante.referente_id and participante.funcao_sintatica == "sujeito"
            ),
            "FONTE_NAO_RESOLVIDA",
        )

    def fonte_da_citacao(proposicao: Proposition) -> str:
        quadro = next((
            item for item in citacoes
            if item.inicio < proposicao.predicado_intervalo.inicio < item.fim
        ), None)
        if quadro is None or quadro.verbo_inicio is None:
            return "FONTE_NAO_RESOLVIDA"
        relatora = next((
            item for item in proposicoes
            if item.predicado_intervalo.inicio == quadro.verbo_inicio
            and item.predicado_intervalo.fim == quadro.verbo_fim
        ), None)
        if relatora is None:
            return "FONTE_NAO_RESOLVIDA"
        # Somente o sujeito da oração relatora é fonte; um objeto ou o
        # sujeito dentro da citação não pode ocupar seu lugar.
        return fonte_da_proposicao(relatora)

    for proposicao in proposicoes:
        if _dentro_de_descricao_complexa(proposicao, mencoes):
            chave = ("pressuposicao", "pressuposta", "ENUNCIADOR")
            proposicao.atribuicao = Attribution(
                fonte="enunciador",
                modo="informação de fundo",
                estado="pressuposta",
            )
        elif proposicao.atribuicao.modo == "fala citada":
            fonte_id = fonte_da_citacao(proposicao)
            chave = ("fala_citada", "citada", fonte_id)
            if fonte_id in rotulos_fontes:
                proposicao.atribuicao.fonte = rotulos_fontes[fonte_id]
        elif "?" in proposicao.evidencia.texto:
            chave = ("pergunta", "questionada", "ENUNCIADOR")
            proposicao.atribuicao = Attribution(fonte="enunciador", modo="pergunta", estado="questionada")
        elif proposicao.atribuicao.modo in {"percepção", "conteúdo percebido"}:
            chave = ("percepcao", "percebida", fonte_da_proposicao(proposicao))
            proposicao.atribuicao.estado = "percebida"
        elif proposicao.atribuicao.modo == "atitude mental":
            chave = ("atitude_mental", "afirmada", fonte_da_proposicao(proposicao))
        else:
            chave = ("assercao_narrativa", "afirmada", "NARRADOR")
            proposicao.atribuicao = Attribution(
                fonte="narrador",
                modo="asserção narrativa",
                estado="afirmada",
            )
        grupos.setdefault(chave, []).append(proposicao)

    quadros: list[AttributionFrame] = []
    for (modo, estado, fonte_id), escopo in grupos.items():
        tipo_fonte = (
            "participante_discursivo" if fonte_id in {"NARRADOR", "ENUNCIADOR"}
            else "referente" if fonte_id in rotulos_fontes
            else "nao_resolvida"
        )
        rotulo = (
            "narrador" if fonte_id == "NARRADOR"
            else "enunciador" if fonte_id == "ENUNCIADOR"
            else rotulos_fontes.get(fonte_id, "fonte não resolvida")
        )
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
            confianca=0.94 if tipo_fonte in {"participante_discursivo", "referente"} else 0.68,
        )
        quadros.append(quadro)
        for proposicao in escopo:
            proposicao.atribuicao_id = quadro.id
    return quadros
