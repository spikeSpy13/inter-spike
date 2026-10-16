from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Mention, MentionFeatures, MentionOrigin, MentionType
from .validator import validar_mencoes
from ..models import Span


@dataclass(frozen=True)
class Token:
    texto: str
    inicio: int
    fim: int

    @property
    def normalizado(self) -> str:
        return self.texto.casefold()


@dataclass(frozen=True)
class Candidate:
    texto: str
    inicio: int
    fim: int
    tipo: MentionType
    origem: MentionOrigin
    confianca: float


TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", re.UNICODE)

PRONOMES_PESSOAIS = {"eu", "tu", "você", "nós", "vocês", "ele", "ela", "eles", "elas"}
PRONOMES_POSSESSIVOS = {"dele", "dela", "deles", "delas", "seu", "sua", "seus", "suas", "meu", "minha", "meus", "minhas"}
DETERMINANTES = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas", "nenhum", "nenhuma",
    "aquele", "aquela", "aqueles", "aquelas", "daquele", "daquela",
}
PREPOSICOES_INTERNAS = {"de", "do", "da", "dos", "das"}
LIMITES = {
    "não", "nunca", "jamais", "nem", "e", "ou", "mas", "porém", "porque", "pois",
    "quando", "enquanto", "embora", "que", "como", "com", "sem", "por", "para", "através",
    "ao", "à", "aos", "às", "pelo", "pela", "pelos", "pelas",
    "havia", "tivesse", "tenha", "foi", "era", "seria", "sido", "estava", "está",
    "sentou", "percebeu", "assinou", "assinado", "bombardeou", "encontrada", "encontrado",
    "perder", "revisando", "murmurou", "morria", "abandonou", "desistiu", "enviado",
    "acredita", "construiu", "transformando", "frear", "já", "enviou",
    "respondeu", "criticou", "desistiria", "insistiu", "revisou",
}
INICIOS_DE_PERIODO = {"Quando", "Durante", "Apesar", "No", "Na", "Você", "Claro", "Enquanto", "Embora", "Porque", "Pois"}

TERMOS_PESSOA = {"gerente", "engenheira", "profissional", "diretor", "auditor", "auditores", "mensageiro", "alguém", "pessoa"}
TERMOS_LUGAR = {"praça", "banco", "campo"}
TERMOS_EVENTO = {"reunião", "revés", "crise"}
TERMOS_OBJETO = {"contrato", "proposta", "cálculos", "planilhas", "bateria", "celular", "documento", "projeto", "recursos", "argumentos"}
NOMES_FEMININOS = {"helena", "ana", "maria", "clara", "beatriz", "luísa", "luisa"}
NOMES_MASCULINOS = {"joão", "joao", "josé", "jose", "paulo", "carlos", "pedro"}


def _tokens(texto: str) -> list[Token]:
    return [Token(match.group(), match.start(), match.end()) for match in TOKEN_RE.finditer(texto)]


def _eh_limite_nominal(token: Token) -> bool:
    if token.normalizado in LIMITES:
        return True
    return bool(re.search(r"(?:ou|aram|eram|iram|ava|avam|iam|iria)$", token.normalizado))


def _classe_semantica(texto: str, tipo: MentionType) -> str:
    palavras = {token.casefold() for token in TOKEN_RE.findall(texto)}
    if tipo in {"pronome_pessoal", "nome_proprio"} or palavras & TERMOS_PESSOA:
        return "pessoa"
    if palavras & TERMOS_LUGAR:
        return "lugar"
    if palavras & TERMOS_EVENTO:
        return "evento"
    if palavras & TERMOS_OBJETO:
        return "objeto"
    return "desconhecida"


def _genero(texto: str, tipo: MentionType) -> str:
    primeira = texto.split(maxsplit=1)[0].casefold()
    if tipo == "nome_proprio" and primeira in NOMES_FEMININOS:
        return "feminino"
    if tipo == "nome_proprio" and primeira in NOMES_MASCULINOS:
        return "masculino"
    if primeira in {"seu", "sua", "seus", "suas", "meu", "minha", "meus", "minhas"}:
        return "indeterminado"
    if primeira in {"a", "uma", "nenhuma", "aquela", "daquela", "ela", "dela"}:
        return "feminino"
    if primeira in {"o", "um", "nenhum", "aquele", "daquele", "ele", "dele"}:
        return "masculino"
    return "indeterminado"


def _numero(texto: str, tipo: MentionType) -> str:
    primeira = texto.split(maxsplit=1)[0].casefold()
    if primeira in {"seu", "sua", "seus", "suas", "meu", "minha", "meus", "minhas"}:
        return "indeterminado"
    if primeira in {"os", "as", "uns", "umas", "aqueles", "aquelas", "eles", "elas", "deles", "delas", "seus", "suas", "meus", "minhas"}:
        return "plural"
    if primeira in DETERMINANTES | PRONOMES_PESSOAIS | PRONOMES_POSSESSIVOS:
        return "singular"
    if tipo == "descricao_nominal" and texto.casefold().split()[-1].endswith("s"):
        return "plural"
    return "indeterminado"


def _adicionar(candidatos: dict[tuple[int, int, str], Candidate], candidato: Candidate) -> None:
    chave = (candidato.inicio, candidato.fim, candidato.tipo)
    existente = candidatos.get(chave)
    if existente is None or candidato.confianca > existente.confianca:
        candidatos[chave] = candidato


def _detectar_pronomes(texto: str, origem: MentionOrigin, candidatos: dict[tuple[int, int, str], Candidate]) -> None:
    for token in _tokens(texto):
        if token.normalizado in PRONOMES_PESSOAIS:
            _adicionar(candidatos, Candidate(token.texto, token.inicio, token.fim, "pronome_pessoal", origem, 0.99))
        elif token.normalizado in PRONOMES_POSSESSIVOS:
            _adicionar(candidatos, Candidate(token.texto, token.inicio, token.fim, "pronome_possessivo", origem, 0.99))


def _detectar_nomes(texto: str, origem: MentionOrigin, candidatos: dict[tuple[int, int, str], Candidate]) -> None:
    for token in _tokens(texto):
        if (
            token.texto[:1].isupper()
            and token.texto not in INICIOS_DE_PERIODO
            and token.normalizado not in PRONOMES_PESSOAIS | PRONOMES_POSSESSIVOS | DETERMINANTES | TERMOS_PESSOA
        ):
            _adicionar(candidatos, Candidate(token.texto, token.inicio, token.fim, "nome_proprio", origem, 0.93))


def _detectar_descricoes(texto: str, origem: MentionOrigin, candidatos: dict[tuple[int, int, str], Candidate]) -> None:
    tokens = _tokens(texto)
    for indice, token in enumerate(tokens):
        if token.normalizado not in DETERMINANTES:
            continue

        fim_indice = indice
        palavras_conteudo = 0
        for atual in range(indice + 1, min(len(tokens), indice + 8)):
            anterior = tokens[atual - 1]
            proximo = tokens[atual]
            separador = texto[anterior.fim:proximo.inicio]
            if re.search(r"[,.!?;:\"“”]", separador):
                break
            if _eh_limite_nominal(proximo):
                break
            if proximo.normalizado in PREPOSICOES_INTERNAS or proximo.normalizado in PRONOMES_POSSESSIVOS:
                fim_indice = atual
                continue
            palavras_conteudo += 1
            fim_indice = atual
            if palavras_conteudo >= 4:
                break

        if fim_indice == indice:
            continue
        inicio = token.inicio
        fim = tokens[fim_indice].fim
        trecho = texto[inicio:fim]
        _adicionar(candidatos, Candidate(trecho, inicio, fim, "descricao_nominal", origem, 0.82))


def _detectar_descricoes_complexas(texto: str, origem: MentionOrigin, candidatos: dict[tuple[int, int, str], Candidate]) -> None:
    padrao = re.compile(r"\balguém\s+que\s+[^,.!?;]+", re.IGNORECASE)
    for match in padrao.finditer(texto):
        trecho = match.group().strip()
        fim = match.start() + len(trecho)
        _adicionar(candidatos, Candidate(trecho, match.start(), fim, "descricao_complexa", origem, 0.78))


def _detectar_papeis_humanos(texto: str, origem: MentionOrigin, candidatos: dict[tuple[int, int, str], Candidate]) -> None:
    tokens = _tokens(texto)
    for indice, token in enumerate(tokens):
        if token.normalizado not in TERMOS_PESSOA:
            continue
        contido = any(
            candidato.inicio <= token.inicio and candidato.fim >= token.fim
            for candidato in candidatos.values()
        )
        if contido and token.normalizado != "alguém":
            continue
        fim = token.fim
        for proximo in tokens[indice + 1:indice + 3]:
            separador = texto[fim:proximo.inicio]
            if re.search(r"[,.!?;:\"“”]", separador) or _eh_limite_nominal(proximo) or proximo.normalizado in PREPOSICOES_INTERNAS:
                break
            fim = proximo.fim
        trecho = texto[token.inicio:fim]
        _adicionar(candidatos, Candidate(trecho, token.inicio, fim, "descricao_nominal", origem, 0.78))


def detectar_mencoes(texto: str, origem: MentionOrigin = "paragrafo", inicio_id: int = 1) -> list[Mention]:
    candidatos: dict[tuple[int, int, str], Candidate] = {}
    _detectar_pronomes(texto, origem, candidatos)
    _detectar_nomes(texto, origem, candidatos)
    _detectar_descricoes(texto, origem, candidatos)
    _detectar_descricoes_complexas(texto, origem, candidatos)
    _detectar_papeis_humanos(texto, origem, candidatos)

    ordenados = sorted(candidatos.values(), key=lambda item: (item.inicio, -(item.fim - item.inicio), item.tipo))
    mencoes: list[Mention] = []
    for deslocamento, candidato in enumerate(ordenados):
        mencoes.append(Mention(
            id=f"M{inicio_id + deslocamento}",
            texto=candidato.texto,
            tipo=candidato.tipo,
            origem=candidato.origem,
            intervalo=Span(inicio=candidato.inicio, fim=candidato.fim),
            caracteristicas=MentionFeatures(
                classe_semantica=_classe_semantica(candidato.texto, candidato.tipo),
                genero=_genero(candidato.texto, candidato.tipo),
                numero=_numero(candidato.texto, candidato.tipo),
            ),
            confianca_deteccao=candidato.confianca,
        ))

    for mencao in mencoes:
        pais = [
            candidata for candidata in mencoes
            if candidata.id != mencao.id
            and candidata.intervalo.inicio <= mencao.intervalo.inicio
            and candidata.intervalo.fim >= mencao.intervalo.fim
        ]
        if pais:
            pai = min(pais, key=lambda item: item.intervalo.fim - item.intervalo.inicio)
            mencao.mencao_pai_id = pai.id
    validar_mencoes(texto, mencoes)
    return mencoes

