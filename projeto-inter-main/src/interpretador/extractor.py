from __future__ import annotations

import re
from dataclasses import dataclass

from .models import (
    AnalysisResponse,
    AnalysisSummary,
    Attribution,
    Evidence,
    Operators,
    Participant,
    Proposition,
    Span,
)
from .referencias.detector import detectar_mencoes
from .referencias.models import Mention
from .referencias.resolvedor import resolver_referencias
from .grafo import construir_grafo


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


@dataclass(frozen=True)
class DetectedParticipant:
    texto: str
    inicio: int
    fim: int


VERBOS = {
    "abandonou": "abandonar", "acredita": "acreditar", "assinasse": "assinar",
    "assinado": "assinar", "assinou": "assinar", "bombardeou": "bombardear",
    "construiu": "construir", "desistiu": "desistir", "encontrada": "encontrar",
    "encontrado": "encontrar", "enviou": "enviar", "enviado": "enviar",
    "esgotando": "esgotar", "frear": "frear", "havia": "haver", "morreu": "morrer",
    "morria": "morrer", "murmurou": "murmurar", "percebeu": "perceber",
    "perder": "perder", "revisando": "revisar", "sentou": "sentar", "seria": "ser",
    "tivesse": "ter", "transformando": "transformar", "foi": "ser", "era": "ser", "sido": "ser",
    "é": "ser", "são": "ser", "está": "estar", "estava": "estar", "pode": "poder",
    "poderia": "poder", "deve": "dever", "deveria": "dever", "quer": "querer",
    "queria": "querer", "disse": "dizer", "afirmou": "afirmar", "contou": "contar",
    "pensou": "pensar", "imaginou": "imaginar", "viu": "ver", "ouviu": "ouvir",
    "chegou": "chegar", "fez": "fazer", "tinha": "ter", "tem": "ter",
    "terá": "ter", "sofreu": "sofrer", "reagiu": "reagir",
}

AUXILIARES = {"havia", "tivesse", "foi", "era", "seria", "estava", "está", "tinha", "terá", "sido"}
VERBOS_FALA = {"dizer", "afirmar", "contar", "murmurar", "perguntar"}
VERBOS_COGNICAO = {"perceber", "acreditar", "pensar", "imaginar", "ver", "ouvir"}
MODAIS = {
    "pode": "possível", "poderia": "hipotética", "seria": "hipotética",
    "talvez": "possível", "possivelmente": "possível", "deve": "provável/necessária",
    "deveria": "esperada", "capaz": "capacidade",
}
PRONOMES_SUJEITO = {"eu", "tu", "você", "nós", "vocês", "ele", "ela", "eles", "elas"}
INICIOS_NAO_NOMINAIS = {"Quando", "Durante", "Apesar", "No", "Na", "Você", "Claro", "Enquanto", "Embora", "Porque", "Pois"}
NOMES_DE_PAPEL = {"gerente", "engenheira", "profissional", "diretor", "auditores", "bateria", "documento", "burocracia", "alguém"}
NAO_VERBOS = {
    "quando", "enquanto", "segundo", "comando", "demanda", "anda", "ainda",
    "conteúdo", "sentido", "partido", "estado", "resultado", "cuidado",
}

TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", re.UNICODE)
SENTENCE_RE = re.compile(r"\s*[^.!?]+(?:[.!?]+(?=[\"”»']?(?:\s|$))|$)", re.UNICODE)
CONNECTOR_RE = re.compile(r"[,;:]|\b(?:quando|embora|porque|pois|enquanto|apesar\s+de|mas)\b", re.IGNORECASE)


def tokenizar(texto: str) -> list[Token]:
    return [Token(match.group(), match.start(), match.end()) for match in TOKEN_RE.finditer(texto)]


def segmentar_periodos(texto: str) -> list[Sentence]:
    periodos: list[Sentence] = []
    for match in SENTENCE_RE.finditer(texto):
        bruto = match.group()
        esquerda = len(bruto) - len(bruto.lstrip())
        inicio = match.start() + esquerda
        fim = match.end()
        if inicio < fim:
            periodos.append(Sentence(texto[inicio:fim], inicio, fim))
    return periodos or [Sentence(texto, 0, len(texto))]


def lematizar(token: Token) -> str | None:
    palavra = token.normalizado
    if palavra in NAO_VERBOS:
        return None
    if palavra in VERBOS:
        return VERBOS[palavra]
    if palavra.endswith("ando") and len(palavra) > 5:
        return palavra[:-4] + "ar"
    if palavra.endswith("endo") and len(palavra) > 5:
        return palavra[:-4] + "er"
    if palavra.endswith("indo") and len(palavra) > 5:
        return palavra[:-4] + "ir"
    if re.search(r"(?:aram|eram|iram|avam)$", palavra) and len(palavra) > 6:
        return palavra[:-4] + "r"
    if re.search(r"(?:asse|esse|isse)$", palavra) and len(palavra) > 6:
        return palavra[:-4] + "r"
    if palavra.endswith("ou") and len(palavra) > 4:
        return palavra[:-2] + "ar"
    return None


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


def participante_mais_proximo(
    texto: str, tokens: list[Token], indice_verbo: int, inicio_periodo: int
) -> DetectedParticipant | None:
    candidatos = [token for token in tokens[:indice_verbo] if token.inicio >= inicio_periodo]
    for indice in range(len(candidatos) - 1, -1, -1):
        token = candidatos[indice]
        if token.texto[:1].isupper() and token.texto not in INICIOS_NAO_NOMINAIS:
            return DetectedParticipant(token.texto, token.inicio, token.fim)
        if token.normalizado in PRONOMES_SUJEITO:
            return DetectedParticipant(token.texto, token.inicio, token.fim)
        if token.normalizado in NOMES_DE_PAPEL:
            inicio = token.inicio
            if indice > 0 and candidatos[indice - 1].normalizado in {"o", "a", "os", "as", "um", "uma"}:
                inicio = candidatos[indice - 1].inicio
            return DetectedParticipant(texto[inicio:token.fim], inicio, token.fim)
    return None


def participante_anteposto(
    texto: str, inicio_periodo: int, inicio_verbo: int
) -> DetectedParticipant | None:
    base = max(inicio_periodo, inicio_verbo - 110)
    trecho = texto[base:inicio_verbo]
    match = re.search(
        r"\b((?:nenhum|nenhuma|o|a|os|as|um|uma)\s+[^\s,.;]+"
        r"(?:\s+(?!(?:não|nem|já|havia|tivesse|tenha|foi|era|sido|estava)\b)[^\s,.;]+)?)"
        r"(?:\s+já)?\s+(?:(?:não\s+)?(?:havia|tivesse|tenha|foi|era|sido|estava)\s+)*(?:se\s+)?$",
        trecho,
        re.IGNORECASE,
    )
    if not match:
        return None
    inicio = base + match.start(1)
    fim = base + match.end(1)
    return DetectedParticipant(texto[inicio:fim], inicio, fim)


def participante_de_descricao_complexa(
    mencoes: list[Mention], token: Token
) -> DetectedParticipant | None:
    complexas = [
        mencao for mencao in mencoes
        if mencao.tipo == "descricao_complexa"
        and mencao.intervalo.inicio < token.inicio < mencao.intervalo.fim
    ]
    if not complexas:
        return None
    complexa = min(complexas, key=lambda item: item.intervalo.fim - item.intervalo.inicio)
    nucleos = [
        mencao for mencao in mencoes
        if mencao.mencao_pai_id == complexa.id and mencao.texto.casefold() == "alguém"
    ]
    if not nucleos:
        return None
    nucleo = nucleos[0]
    return DetectedParticipant(nucleo.texto, nucleo.intervalo.inicio, nucleo.intervalo.fim)


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


def participante_posposto(texto: str, inicio: int, fim: int) -> DetectedParticipant | None:
    trecho = texto[inicio:fim]
    match = re.search(
        r"\b(o|a|os|as|um|uma)\s+(gerente|engenheira|profissional|diretor|auditores)\b",
        trecho,
        re.IGNORECASE,
    )
    if not match:
        return None
    inicio_absoluto = inicio + match.start()
    fim_absoluto = inicio + match.end()
    return DetectedParticipant(texto[inicio_absoluto:fim_absoluto], inicio_absoluto, fim_absoluto)


def extrair_operadores(texto: str, token: Token, inicio_evidencia: int, fim_evidencia: int) -> Operators:
    esquerda = texto[max(inicio_evidencia, token.inicio - 55):token.inicio].casefold()
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


def encontrar_mencao(
    mencoes: list[Mention], participante: DetectedParticipant
) -> Mention | None:
    exatas = [
        mencao for mencao in mencoes
        if mencao.origem == "paragrafo"
        and mencao.intervalo.inicio == participante.inicio
        and mencao.intervalo.fim == participante.fim
    ]
    if exatas:
        return exatas[0]
    continentes = [
        mencao for mencao in mencoes
        if mencao.origem == "paragrafo"
        and mencao.intervalo.inicio <= participante.inicio
        and mencao.intervalo.fim >= participante.fim
    ]
    return min(
        continentes,
        key=lambda mencao: mencao.intervalo.fim - mencao.intervalo.inicio,
        default=None,
    )


def analisar_paragrafo(texto: str, contexto_anterior: str | None = None) -> AnalysisResponse:
    texto = texto.strip()
    if not texto:
        raise ValueError("O parágrafo não pode estar vazio.")
    contexto_anterior = contexto_anterior.strip() if contexto_anterior else None

    mencoes_contexto = (
        detectar_mencoes(contexto_anterior, "contexto_anterior", 1)
        if contexto_anterior else []
    )
    mencoes_paragrafo = detectar_mencoes(
        texto,
        "paragrafo",
        len(mencoes_contexto) + 1,
    )
    mencoes = [*mencoes_contexto, *mencoes_paragrafo]
    resultado_referencias = resolver_referencias(mencoes)

    tokens = tokenizar(texto)
    periodos = segmentar_periodos(texto)
    proposicoes: list[Proposition] = []

    for indice, token in enumerate(tokens):
        lema = lematizar(token)
        if not lema:
            continue
        proximo = tokens[indice + 1] if indice + 1 < len(tokens) else None
        if proximo and proximo.normalizado == "se" and indice + 2 < len(tokens):
            proximo = tokens[indice + 2]
        if token.normalizado in AUXILIARES and proximo and lematizar(proximo) and proximo.inicio - token.fim < 18:
            continue

        periodo = next((item for item in periodos if item.inicio <= token.inicio < item.fim), periodos[0])
        inicio, fim = intervalo_evidencia(texto, periodo, token)
        participante_detectado = (
            participante_de_descricao_complexa(mencoes_paragrafo, token)
            or participante_anteposto(texto, periodo.inicio, token.inicio)
            or participante_mais_proximo(texto, tokens, indice, periodo.inicio)
        )
        if participante_detectado is None and lema in VERBOS_FALA:
            participante_detectado = participante_posposto(texto, token.fim, periodo.fim)
        participante = participante_detectado.texto if participante_detectado else "participante não resolvido"
        objeto = complemento(texto, token, fim)
        operadores = extrair_operadores(texto, token, inicio, fim)
        atribuicao = extrair_atribuicao(texto, token, lema, periodo, participante)
        descricao = f"{participante} · {lema}" + (f" · {objeto}" if objeto else "")
        mencao = encontrar_mencao(mencoes_paragrafo, participante_detectado) if participante_detectado else None
        participantes = []
        if participante_detectado and mencao:
            participantes.append(Participant(
                papel="participante_principal",
                mencao=mencao.texto,
                mencao_id=mencao.id,
                intervalo=Span(inicio=mencao.intervalo.inicio, fim=mencao.intervalo.fim),
                referente_id=resultado_referencias.referente_por_mencao.get(mencao.id),
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
        ))

    grafo = construir_grafo(
        texto,
        contexto_anterior,
        proposicoes,
        mencoes,
        resultado_referencias,
    )

    alertas: list[str] = []
    if not proposicoes:
        alertas.append("Nenhum predicado foi identificado com segurança; revisão manual necessária.")
    if any(not prop.participantes for prop in proposicoes):
        alertas.append("Há proposições cujo participante principal ainda não foi localizado como menção.")
    ambiguas = [item for item in resultado_referencias.resolucoes if item.estado == "ambigua"]
    nao_resolvidas = [item for item in resultado_referencias.resolucoes if item.estado == "nao_resolvida"]
    if ambiguas:
        alertas.append(f"{len(ambiguas)} resolução referencial permaneceu ambígua.")
    if nao_resolvidas:
        alertas.append(f"{len(nao_resolvidas)} menção pronominal permaneceu sem referente textual seguro.")

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
        ),
        alertas=alertas,
    )

