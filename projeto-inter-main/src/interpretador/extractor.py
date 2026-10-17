from __future__ import annotations

from dataclasses import dataclass
import re
from time import perf_counter

from .models import (
    AnalysisResponse,
    AnalysisSummary,
    Attribution,
    Evidence,
    ExecutionCosts,
    ExecutionMetadata,
    ExecutionParameters,
    LinguisticAnalysis,
    Operators,
    Participant,
    Proposition,
    Span,
    SubjectSelection,
)
from .referencias.detector import detectar_mencoes
from .referencias.resolvedor import resolver_referencias
from .grafo import construir_grafo
from .centralidade import propor_ideia_central
from .geracao import gerar_parafrases, gerar_sintese
from .fidelidade import checar_fidelidade
from .linguistica import (
    BaseLinguistica, DiagnosticoLinguistico, VERBOS, analisar_texto, lematizar_palavra,
)
from .sujeitos import selecionar_sujeito


@dataclass(frozen=True)
class Token:
    texto: str
    inicio: int
    fim: int

    @property
    def normalizado(self) -> str:
        return self.texto.casefold()


@dataclass(frozen=True)
class Sentence:
    texto: str
    inicio: int
    fim: int


AUXILIARES = {"havia", "tivesse", "foi", "era", "seria", "estava", "está", "tinha", "terá", "sido"}
AUXILIARES_MODAIS = {"pode", "poderia", "deve", "deveria", "quer", "queria"}
VERBOS_FALA = {"dizer", "afirmar", "contar", "murmurar", "perguntar"}
VERBOS_COGNICAO = {"perceber", "acreditar", "pensar", "imaginar", "ver", "ouvir"}
MODAIS = {
    "pode": "possível", "poderia": "hipotética", "seria": "hipotética",
    "talvez": "possível", "possivelmente": "possível", "deve": "provável/necessária",
    "deveria": "esperada", "capaz": "capacidade",
}
TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", re.UNICODE)
CONNECTOR_RE = re.compile(r"[,;:]|\b(?:quando|embora|porque|pois|enquanto|apesar\s+de|até\s+que|mas)\b", re.IGNORECASE)


def tokenizar(texto: str) -> list[Token]:
    return [Token(match.group(), match.start(), match.end()) for match in TOKEN_RE.finditer(texto)]


def segmentar_periodos(texto: str) -> list[Sentence]:
    return [Sentence(item.texto, item.inicio, item.fim) for item in analisar_texto(texto).periodos]


def lematizar(token: Token) -> str | None:
    return lematizar_palavra(token.normalizado)


def intervalo_evidencia(texto: str, periodo: Sentence, token: Token) -> tuple[int, int]:
    indice_local = token.inicio - periodo.inicio
    inicio_local = 0
    fim_local = len(periodo.texto)
    for match in CONNECTOR_RE.finditer(periodo.texto):
        if match.start() < indice_local:
            inicio_local = match.end()
        else:
            fim_local = match.start()
            break

    inicio = periodo.inicio + inicio_local
    fim = periodo.inicio + fim_local
    while inicio < fim and texto[inicio].isspace():
        inicio += 1
    while fim > inicio and texto[fim - 1].isspace():
        fim -= 1
    return inicio, fim


def complemento(texto: str, token: Token, fim_evidencia: int) -> str | None:
    cauda = texto[token.fim:fim_evidencia]
    cauda = re.sub(r"^\s+(?:a|o|ao|à|os|as|um|uma|de|do|da)\s+", "", cauda, flags=re.IGNORECASE)
    formas_verbais = "|".join(sorted((re.escape(item) for item in VERBOS), key=len, reverse=True))
    cauda = re.split(
        rf"\s+(?:e|nem|mas)\s+(?=(?:{formas_verbais})\b)",
        cauda,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    cauda = re.sub(r"[.,;!?\"”]+$", "", cauda).strip()
    if len(cauda) < 3:
        return None
    return cauda if len(cauda) <= 86 else cauda[:83].rstrip() + "…"


def extrair_operadores(texto: str, token: Token, inicio_evidencia: int, fim_evidencia: int) -> Operators:
    esquerda = texto[max(inicio_evidencia, token.inicio - 90):token.inicio].casefold()
    if lematizar(token) == token.normalizado:
        complemento_infinitivo = re.search(r"\b(?:de|para|a)\s+((?:(?:não|nunca|jamais)\s+)?)$", esquerda)
        if complemento_infinitivo:
            # 'nem desistiu de buscar' nega desistir, sem afirmar 'não buscar'.
            esquerda = complemento_infinitivo.group(1)
    coordenadores = list(re.finditer(r"\b(?:e|mas|porém)\b", esquerda, re.IGNORECASE))
    if coordenadores:
        esquerda = esquerda[coordenadores[-1].end():]
    negacoes = re.findall(r"\b(não|nunca|jamais|nenhum|nenhuma|nem)\b", esquerda)
    return Operators(negacao=negacoes[-1] if negacoes else None, modalidade=None)


def dentro_de_aspas(texto: str, indice: int) -> bool:
    anterior = texto[:indice]
    return anterior.count('"') % 2 == 1 or anterior.count("“") > anterior.count("”")


def extrair_atribuicao(texto: str, token: Token, lema: str, periodo: Sentence, participante: str) -> Attribution:
    if dentro_de_aspas(texto, token.inicio):
        return Attribution(fonte="falante não resolvido", modo="fala citada", estado="citada")
    if "?" in periodo.texto:
        return Attribution(fonte="enunciador", modo="pergunta", estado="questionada")
    if lema in VERBOS_FALA:
        return Attribution(fonte=participante, modo="fala", estado="afirmada")
    if lema in VERBOS_COGNICAO:
        modo = "percepção" if lema == "perceber" else "atitude mental"
        return Attribution(fonte=participante, modo=modo, estado="afirmada")
    prefixo = periodo.texto[:token.inicio - periodo.inicio]
    if re.search(r"percebeu\s+que", prefixo, re.IGNORECASE):
        return Attribution(fonte="experienciador não resolvido", modo="conteúdo percebido", estado="percebida")
    return Attribution(fonte="narrador", modo="asserção narrativa", estado="afirmada")


def calcular_confianca(participante: str, lema: str, operadores: Operators, atribuicao: Attribution) -> float:
    confianca = 0.86 if lema in VERBOS.values() else 0.76
    if participante == "participante não resolvido":
        confianca -= 0.13
    if atribuicao.estado in {"citada", "questionada"}:
        confianca -= 0.04
    if operadores.modalidade:
        confianca += 0.02
    return round(max(0.51, min(0.96, confianca)), 2)


def analisar_paragrafo(
    texto: str,
    contexto_anterior: str | None = None,
    *,
    base_linguistica: BaseLinguistica | None = None,
    base_contexto: BaseLinguistica | None = None,
) -> AnalysisResponse:
    inicio_execucao = perf_counter()
    if not texto.strip():
        raise ValueError("O parágrafo não pode estar vazio.")
    contexto_anterior = contexto_anterior if contexto_anterior and contexto_anterior.strip() else None
    base = base_linguistica.model_copy(deep=True) if base_linguistica else analisar_texto(texto)
    if base.texto != texto:
        raise ValueError("A base linguística diverge do parágrafo analisado.")
    contexto = (base_contexto or analisar_texto(contexto_anterior)) if contexto_anterior else None
    if contexto and contexto.texto != contexto_anterior:
        raise ValueError("A base linguística diverge do contexto anterior.")

    mencoes_contexto = (
        detectar_mencoes(contexto_anterior, "contexto_anterior", 1, contexto)
        if contexto_anterior else []
    )
    mencoes_paragrafo = detectar_mencoes(
        texto,
        "paragrafo",
        len(mencoes_contexto) + 1,
        base,
    )
    mencoes = [*mencoes_contexto, *mencoes_paragrafo]
    resultado_referencias = resolver_referencias(mencoes)

    tokens = tokenizar(texto)
    periodos = [Sentence(item.texto, item.inicio, item.fim) for item in base.periodos]
    por_id = {item.id: item for item in base.tokens}

    def lema_do_token(token: Token) -> str | None:
        anotado = base.token_em(token.inicio, token.fim)
        return anotado.lema if anotado and anotado.pos in {"VERB", "AUX"} else None
    proposicoes: list[Proposition] = []

    for indice, token in enumerate(tokens):
        anotado = base.token_em(token.inicio, token.fim)
        lema = lema_do_token(token)
        if not lema:
            continue
        if anotado and anotado.pos == "AUX" and anotado.dependencia == "aux":
            cabeca = por_id.get(anotado.cabeca_id)
            if cabeca and cabeca.pos in {"VERB", "AUX"} and cabeca.lema:
                continue
        if anotado and anotado.dependencia in {"acl", "xcomp", "amod"}:
            recebida = (anotado.recebida or {}).get("morfologia") or {}
            if recebida.get("morfologia", {}).get("VerbForm") == "Part":
                # Particípios descritivos não são ações autônomas comprovadas.
                anotado.decisoes.append("participio_descritivo_sem_proposicao_autonoma")
                base.diagnosticos.append(DiagnosticoLinguistico(
                    codigo="participio_descritivo_omitido",
                    caminho="$.analise_linguistica.paragrafo.tokens",
                    mensagem="Particípio em construção descritiva; não foi inferida uma ação autônoma.",
                    token_id=anotado.id, inicio=anotado.inicio, fim=anotado.fim,
                ))
                continue
        proximo = tokens[indice + 1] if indice + 1 < len(tokens) else None
        if proximo and proximo.normalizado == "se" and indice + 2 < len(tokens):
            proximo = tokens[indice + 2]
        if token.normalizado in AUXILIARES and proximo and lema_do_token(proximo) and proximo.inicio - token.fim < 18:
            continue
        if token.normalizado in AUXILIARES_MODAIS and proximo and lema_do_token(proximo) and proximo.inicio - token.fim < 18:
            continue

        periodo = next((item for item in periodos if item.inicio <= token.inicio < item.fim), periodos[0])
        inicio, fim = intervalo_evidencia(texto, periodo, token)
        selecao = selecionar_sujeito(base, anotado, mencoes_paragrafo)
        mencao = selecao.mencao
        participante = mencao.texto if mencao else "participante não resolvido"
        objeto = complemento(texto, token, fim)
        operadores = extrair_operadores(texto, token, inicio, fim)
        atribuicao = extrair_atribuicao(texto, token, lema, periodo, participante)
        descricao = f"{participante} · {lema}" + (f" · {objeto}" if objeto else "")
        participantes = []
        if mencao:
            participantes.append(Participant(
                papel="participante_principal",
                mencao=mencao.texto,
                mencao_id=mencao.id,
                intervalo=Span(inicio=mencao.intervalo.inicio, fim=mencao.intervalo.fim),
                referente_id=resultado_referencias.referente_por_mencao.get(mencao.id),
                funcao_sintatica="sujeito",
            ))
        proposicoes.append(Proposition(
            id=f"P{len(proposicoes) + 1}",
            predicado=lema,
            forma_textual=token.texto,
            predicado_intervalo=Span(inicio=token.inicio, fim=token.fim),
            descricao=descricao,
            participantes=participantes,
            operadores=operadores,
            atribuicao=atribuicao,
            evidencia=Evidence(texto=texto[inicio:fim], intervalo=Span(inicio=inicio, fim=fim)),
            confianca=calcular_confianca(participante, lema, operadores, atribuicao),
            sujeito=SubjectSelection(
                estado="identificado" if mencao else "indeterminado",
                metodo=selecao.metodo,
                mencao_id=mencao.id if mencao else None,
                razoes=selecao.razoes,
                candidato_ids=selecao.candidato_ids,
                evidencias=[
                    Evidence(texto=texto[a:b], intervalo=Span(inicio=a, fim=b))
                    for a, b in selecao.evidencias
                ],
            ),
        ))

    grafo = construir_grafo(
        texto,
        contexto_anterior,
        proposicoes,
        mencoes,
        resultado_referencias,
    )
    ideia_central, conteudo_essencial_ids = propor_ideia_central(
        texto,
        proposicoes,
        grafo.relacoes,
    )
    sintese = gerar_sintese(
        texto,
        proposicoes,
        conteudo_essencial_ids,
        grafo.operadores,
        grafo.relacoes,
        ideia_central,
    )
    parafrases = gerar_parafrases(
        texto,
        proposicoes,
        grafo.operadores,
        grafo.relacoes,
        sintese,
    )
    checagem = checar_fidelidade(
        texto,
        proposicoes,
        conteudo_essencial_ids,
        grafo.operadores,
        grafo.relacoes,
        sintese,
        parafrases,
    )

    alertas: list[str] = []
    if not proposicoes:
        alertas.append("Nenhum predicado foi identificado com segurança; revisão manual necessária.")
    if any(prop.sujeito and prop.sujeito.estado == "indeterminado" for prop in proposicoes):
        alertas.append("Há proposições com sujeito indeterminado; objetos e destinatários não substituem o sujeito ausente.")
    ambiguas = [item for item in resultado_referencias.resolucoes if item.estado == "ambigua"]
    nao_resolvidas = [item for item in resultado_referencias.resolucoes if item.estado == "nao_resolvida"]
    if ambiguas:
        alertas.append(
            "1 resolução referencial permaneceu ambígua." if len(ambiguas) == 1
            else f"{len(ambiguas)} resoluções referenciais permaneceram ambíguas."
        )
    if nao_resolvidas:
        alertas.append(
            "1 menção pronominal permaneceu sem referente textual seguro." if len(nao_resolvidas) == 1
            else f"{len(nao_resolvidas)} menções pronominais permaneceram sem referente textual seguro."
        )
    diagnosticos = [*base.diagnosticos, *(contexto.diagnosticos if contexto else [])]
    if diagnosticos:
        alertas.append(
            f"A base linguística registra {len(diagnosticos)} diagnóstico(s); "
            "consulte as limitações e os conflitos antes de aceitar a interpretação."
        )
    alertas.append(
        "Participantes, referências, escopos e relações usam regras heurísticas em revisão; "
        "a checagem estrutural da geração não valida toda a interpretação."
    )
    if ideia_central.estado == "indeterminada":
        alertas.append("A ideia central não pôde ser proposta com o registro disponível.")
    elif ideia_central.alternativas and ideia_central.confianca < 0.72:
        alertas.append("A ideia central possui alternativa próxima e deve ser revisada.")

    execucao = ExecutionMetadata(
        duracao_ms=round((perf_counter() - inicio_execucao) * 1_000, 3),
        parametros=ExecutionParameters(
            estrategia_centralidade=ideia_central.metodo,
            estrategia_sintese=sintese.estrategia,
            estrategia_parafrase="substituicao_discursiva_controlada_v1",
            metodo_checagem=checagem.metodo,
            regras_parafrase=["coordenacao_negativa", "justificativa_causal"],
            limite_alternativas_ideia_central=2,
            usa_contexto_anterior=contexto_anterior is not None,
            origem_linguistica=base.origem,
            adaptador_linguistico="base_linguistica_v1",
            seletor_sujeito="oracoes_sujeitos_v1",
        ),
        custos=ExecutionCosts(
            chamadas_externas=0,
            tokens_entrada=0,
            tokens_saida=0,
            custo_estimado=0,
            observacao="Motor heurístico local; nenhuma chamada externa ou cobrança por token.",
        ),
    )

    return AnalysisResponse(
        paragrafo=texto,
        contexto_anterior=contexto_anterior,
        proposicoes=proposicoes,
        mencoes=mencoes,
        referentes=resultado_referencias.referentes,
        resolucoes=resultado_referencias.resolucoes,
        operadores_escopo=grafo.operadores,
        quadros_atribuicao=grafo.quadros_atribuicao,
        relacoes=grafo.relacoes,
        ideia_central=ideia_central,
        conteudo_essencial_ids=conteudo_essencial_ids,
        sintese=sintese,
        parafrases=parafrases,
        checagem=checagem,
        execucao=execucao,
        analise_linguistica=LinguisticAnalysis(paragrafo=base, contexto_anterior=contexto),
        resumo=AnalysisSummary(
            proposicoes=len(proposicoes),
            mencoes=len(mencoes),
            referentes=len(resultado_referencias.referentes),
            resolucoes_resolvidas=sum(
                item.estado == "resolvida" for item in resultado_referencias.resolucoes
            ),
            resolucoes_ambiguas=len(ambiguas),
            operadores=len(grafo.operadores),
            relacoes=len(grafo.relacoes),
            negacoes=sum(prop.operadores.negacao is not None for prop in proposicoes),
            atribuicoes_marcadas=sum(prop.atribuicao.modo != "asserção narrativa" for prop in proposicoes),
            conteudo_essencial=len(conteudo_essencial_ids),
            sintese_caracteres=len(sintese.texto or ""),
            parafrases=len(parafrases),
            achados_fidelidade=len(checagem.achados),
        ),
        alertas=alertas,
    )

