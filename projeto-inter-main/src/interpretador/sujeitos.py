"""Seleção conservadora do sujeito sintático de um predicado.

A proximidade de uma menção não é evidência de função sintática. Dependências
recebidas são hipóteses: só atravessamos coordenação e complementos cujo controle
é sustentado, sem atravessar períodos ou falas citadas. Nenhuma menção é criada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .linguistica.base import BaseLinguistica, TokenLinguistico
    from .referencias.models import Mention


@dataclass(frozen=True)
class ResultadoSujeito:
    mencao: Mention | None
    metodo: str
    razoes: list[str]
    evidencias: list[tuple[int, int]]
    candidato_ids: list[str] = field(default_factory=list)


_SUJEITOS_NOMINAIS = {"nsubj", "nsubj:pass"}
_NOMINAIS = {"NOUN", "PROPN", "PRON"}
_PRONOMES_SUJEITO = {"eu", "tu", "você", "nós", "vocês", "ele", "ela", "eles", "elas", "alguém"}
_COORDENADORES = {"e", "nem", "mas", "porém", "ou"}
_SUBORDINADORES = {"que", "quando", "enquanto", "embora", "porque", "pois", "para", "até"}
_PREPOSICOES = {"a", "ao", "aos", "à", "às", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "com", "sem", "por", "para", "pelo", "pela", "pelos", "pelas", "entre", "até"}
_CONTROLE_SUJEITO = {"tentar", "decidir", "conseguir", "querer", "poder", "dever", "desistir", "começar", "continuar"}
_FALA = {"dizer", "afirmar", "contar", "murmurar", "perguntar", "responder", "falar"}
_AUXILIARES = {"ser", "estar", "ter", "haver", "ir", "poder", "dever", "querer"}


def _abster(token: TokenLinguistico, motivo: str, candidatos: list[str] | None = None) -> ResultadoSujeito:
    return ResultadoSujeito(None, "abstencao", [motivo], [(token.inicio, token.fim)], candidatos or [])


def _intervalo(item: TokenLinguistico | Mention) -> tuple[int, int]:
    if hasattr(item, "intervalo"):
        return item.intervalo.inicio, item.intervalo.fim
    return item.inicio, item.fim


def _escopos(base: BaseLinguistica) -> dict[str, tuple[int, ...]]:
    """Identifica a instância da citação, não apenas estar dentro/fora de aspas."""
    pilha: list[tuple[str, int]] = []
    aberturas = {"“": "”", "«": "»", "‘": "’"}
    resultado = {}
    indice = 0
    for token in sorted(base.tokens, key=lambda item: item.inicio):
        while indice < token.inicio:
            caractere = base.texto[indice]
            if caractere == '"':
                if pilha and pilha[-1][0] == '"':
                    pilha.pop()
                else:
                    pilha.append(('"', indice))
            elif caractere in aberturas:
                pilha.append((aberturas[caractere], indice))
            elif pilha and caractere == pilha[-1][0]:
                pilha.pop()
            indice += 1
        resultado[token.id] = tuple(inicio for _, inicio in pilha)
    return resultado


def _mencao_do_token(token: TokenLinguistico, mencoes: list[Mention]) -> Mention | None:
    candidatas = [
        mencao for mencao in mencoes
        if mencao.origem == "paragrafo"
        and mencao.tipo not in {"pronome_possessivo", "descricao_complexa"}
        and mencao.intervalo.inicio <= token.inicio < token.fim <= mencao.intervalo.fim
    ]
    return min(candidatas, key=lambda item: item.intervalo.fim - item.intervalo.inicio, default=None)


def _mesmo_escopo(token: TokenLinguistico, outro: TokenLinguistico, escopos: dict) -> bool:
    return token.periodo_id == outro.periodo_id and escopos[token.id] == escopos[outro.id]


def _nominal(token: TokenLinguistico, mencao: Mention | None, base: BaseLinguistica) -> bool:
    if token.pos in _NOMINAIS:
        return token.pos != "PRON" or token.normalizado in _PRONOMES_SUJEITO
    # Um adjetivo substantivado ou etiqueta ADJ conflitante não elimina um
    # sintagma nominal com determinante e dependência de sujeito direta.
    return bool(token.pos == "ADJ" and mencao and mencao.tipo == "descricao_nominal" and any(
        outro.pos == "DET" and mencao.intervalo.inicio <= outro.inicio < token.inicio
        for outro in base.tokens
    ))


def _tokens_da_mencao(base: BaseLinguistica, mencao: Mention) -> list[TokenLinguistico]:
    return [token for token in base.tokens if mencao.intervalo.inicio <= token.inicio < token.fim <= mencao.intervalo.fim]


def _candidatas_locais(
    base: BaseLinguistica, token: TokenLinguistico, mencoes: list[Mention], escopos: dict,
) -> tuple[list[Mention], int]:
    anteriores = [
        outro for outro in base.tokens
        if outro.fim <= token.inicio and _mesmo_escopo(token, outro, escopos)
    ]
    periodo = next(item for item in base.periodos if item.id == token.periodo_id)
    limite = periodo.inicio
    for outro in anteriores:
        if outro.texto in {",", ";", ":"} or outro.normalizado in _COORDENADORES | _SUBORDINADORES:
            limite = outro.fim
        elif outro.normalizado == "se" and any(
            mencao.origem == "paragrafo" and outro.fim <= mencao.intervalo.inicio < mencao.intervalo.fim <= token.inicio
            and mencao.tipo in {"nome_proprio", "pronome_pessoal", "descricao_nominal"}
            for mencao in mencoes
        ):
            # "se Ana vier" abre uma oração; o reflexivo de "o tempo estava
            # se esgotando" não apaga o sujeito que precede o auxiliar.
            limite = outro.fim
    candidatas = []
    for mencao in mencoes:
        if mencao.origem != "paragrafo" or mencao.tipo in {"pronome_possessivo", "descricao_complexa"}:
            continue
        if not (limite <= mencao.intervalo.inicio < mencao.intervalo.fim <= token.inicio):
            continue
        contidos = _tokens_da_mencao(base, mencao)
        if not contidos or not all(_mesmo_escopo(token, outro, escopos) for outro in contidos):
            continue
        # A construção "de João", por exemplo, não é sujeito explícito.
        antes = [outro for outro in anteriores if limite <= outro.inicio < mencao.intervalo.inicio]
        if antes and antes[-1].normalizado in _PREPOSICOES:
            continue
        # Objetos de outro verbo não se tornam sujeitos pela proximidade.
        if any(outro.pos in {"VERB", "AUX"} and outro.lema not in _AUXILIARES for outro in antes):
            continue
        entre = [outro for outro in anteriores if mencao.intervalo.fim <= outro.inicio]
        if any(outro.pos in {"VERB", "AUX"} and outro.lema not in _AUXILIARES for outro in entre):
            continue
        # Uma anotação nominal de objeto/oblíquo explícita prevalece sobre a
        # hipótese linear. Não rejeitamos o determinante ou o possessivo interno.
        nucleos = [outro for outro in contidos if outro.pos in {"NOUN", "PROPN", "PRON"}]
        if any(outro.dependencia and outro.dependencia.split(":")[0] in {"obj", "iobj", "obl", "nmod"} for outro in nucleos):
            continue
        candidatas.append(mencao)
    # Uma descrição externa e o nome/pronome contido são a mesma hipótese.
    candidatas = [
        item for item in candidatas
        if not any(outro.id != item.id and item.intervalo.inicio <= outro.intervalo.inicio
                   and outro.intervalo.fim <= item.intervalo.fim
                   and outro.intervalo != item.intervalo for outro in candidatas)
    ]
    return candidatas, limite


def _explicito_local(
    base: BaseLinguistica, token: TokenLinguistico, mencoes: list[Mention], escopos: dict,
) -> ResultadoSujeito | None:
    candidatas, _ = _candidatas_locais(base, token, mencoes, escopos)
    if len(candidatas) == 1:
        mencao = candidatas[0]
        return ResultadoSujeito(mencao, "sujeito_explicito_local", [
            "Menção explícita antes do predicado na mesma oração, sem verbo lexical interveniente."
        ], [_intervalo(mencao), _intervalo(token)], [mencao.id])
    if candidatas:
        return _abster(token, "Mais de uma menção pode ocupar o sujeito da oração local.", [item.id for item in candidatas])
    return None


def _posposto_relato(
    base: BaseLinguistica, token: TokenLinguistico, mencoes: list[Mention], escopos: dict,
) -> ResultadoSujeito | None:
    if token.lema not in _FALA:
        return None
    posteriores = [outro for outro in base.tokens if outro.inicio >= token.fim and _mesmo_escopo(token, outro, escopos)]
    for mencao in sorted(mencoes, key=lambda item: item.intervalo.inicio):
        if mencao.origem != "paragrafo" or mencao.tipo in {"pronome_possessivo", "descricao_complexa"}:
            continue
        if mencao.caracteristicas.classe_semantica != "pessoa":
            continue
        if mencao.intervalo.inicio < token.fim:
            continue
        contidos = _tokens_da_mencao(base, mencao)
        if not contidos or not all(_mesmo_escopo(token, outro, escopos) for outro in contidos):
            continue
        antes = [outro for outro in posteriores if outro.fim <= mencao.intervalo.inicio]
        # Limitar ao sintagma imediatamente posposto impede "disse que João
        # saiu" de atribuir João ao verbo relator.
        if antes or base.texto[token.fim:mencao.intervalo.inicio].strip():
            return None
        conflitos = [outro for outro in contidos if outro.dependencia
                     and outro.dependencia.split(":")[0] in {"obj", "iobj", "obl"}]
        citacao_antes = re.search(r'["”»’][,\s—-]*$', base.texto[:token.inicio])
        if conflitos and not citacao_antes:
            return None
        razoes = ["Menção humana imediatamente posposta ao verbo de relato, fora do conteúdo citado."]
        if conflitos:
            razoes.append("A etiqueta de objeto recebida conflita com a construção relatora após a citação; adotada a leitura de sujeito posposto.")
        return ResultadoSujeito(mencao, "sujeito_posposto_relato", razoes,
                                [_intervalo(token), _intervalo(mencao)], [mencao.id])
    return None


def _controle_sustentado(base: BaseLinguistica, token: TokenLinguistico, cabeca: TokenLinguistico) -> bool:
    intervalo = base.texto[cabeca.fim:token.inicio].casefold()
    if token.inicio <= cabeca.inicio:
        return False
    # "ler ... sem demonstrar" tem sujeito compartilhado, mesmo com objeto
    # de ler. Pedir/mandar alguém para fazer não têm esta mesma garantia.
    if re.search(r"\bsem\s+(?:(?:não|nunca)\s+)?$", intervalo):
        return True
    permitido = cabeca.lema in _CONTROLE_SUJEITO or (
        cabeca.lema in {"voltar", "retornar", "ir"} and re.search(r"\bpara\s*$", intervalo)
    )
    if not permitido:
        return False
    # Objeto entre o controlador e o infinitivo torna o controle incerto.
    return not any(
        outro.cabeca_id == cabeca.id and outro.dependencia
        and outro.dependencia.split(":")[0] in {"obj", "iobj"}
        and cabeca.fim <= outro.inicio < token.inicio
        for outro in base.tokens
    )


def _por_dependencia(
    base: BaseLinguistica, token: TokenLinguistico, mencoes: list[Mention], escopos: dict,
    por_id: dict[str, TokenLinguistico], visitados: frozenset[str] = frozenset(),
) -> ResultadoSujeito:
    if token.id in visitados:
        return _abster(token, "Ciclo na cadeia sintática; sujeito não propagado.")
    visitados = visitados | {token.id}
    sujeitos = [outro for outro in base.tokens if outro.cabeca_id == token.id and outro.dependencia in _SUJEITOS_NOMINAIS]
    validos = []
    for sujeito in sujeitos:
        mencao = _mencao_do_token(sujeito, mencoes)
        if _nominal(sujeito, mencao, base) and _mesmo_escopo(token, sujeito, escopos):
            if mencao is not None:
                validos.append((sujeito, mencao))
        elif sujeito.normalizado == "que" and token.dependencia == "acl:relcl" and _mesmo_escopo(token, sujeito, escopos):
            antecedente = por_id.get(token.cabeca_id or "")
            if antecedente and _mesmo_escopo(token, antecedente, escopos):
                mencao = _mencao_do_token(antecedente, mencoes)
                if mencao and _nominal(antecedente, mencao, base):
                    validos.append((sujeito, mencao))
    if len(validos) == 1 and len(sujeitos) == 1:
        sujeito, mencao = validos[0]
        razoes = [f"Dependência {sujeito.dependencia} nominal liga a menção diretamente ao predicado, no mesmo período e escopo de citação."]
        if sujeito.normalizado == "que":
            razoes.append("O relativo 'que' ocupa nsubj; a menção selecionada é seu antecedente na dependência acl:relcl, não um objeto da oração relativa.")
        elif sujeito.pos == "ADJ":
            razoes.append("Etiqueta ADJ recebida revista nesta função: determinante, menção nominal e dependência direta sustentam o sujeito nominal.")
        return ResultadoSujeito(mencao, "dependencia_sujeito_direto", razoes,
                                [_intervalo(mencao), _intervalo(sujeito), _intervalo(token)], [mencao.id])
    if sujeitos:
        return _abster(token, "Anotação de sujeito ausente de menção nominal válida, ambígua ou fora do escopo da oração.", [item.id for _, item in validos])
    if any(outro.cabeca_id == token.id and outro.dependencia and outro.dependencia.startswith("csubj") for outro in base.tokens):
        return _abster(token, "O sujeito recebido é uma oração; nenhuma menção nominal foi substituída pela oração inteira.")
    explicito = _explicito_local(base, token, mencoes, escopos)
    if explicito:
        return explicito
    posposto = _posposto_relato(base, token, mencoes, escopos)
    if posposto:
        return posposto
    relativa = _relativa_alguem(base, token, mencoes, escopos)
    if relativa:
        return relativa
    cabeca = por_id.get(token.cabeca_id or "")
    relacao = (token.dependencia or "").split(":")[0]
    if relacao not in {"conj", "xcomp"} or cabeca is None or cabeca.id == token.id:
        return _abster(token, "Nenhum sujeito nominal direto ou cadeia de controle sustentada foi encontrado.")
    if not _mesmo_escopo(token, cabeca, escopos) or cabeca.pos not in {"VERB", "AUX"}:
        return _abster(token, "A cabeça não é um predicado no mesmo período e escopo de citação; herança bloqueada.")
    if relacao == "xcomp" and not _controle_sustentado(base, token, cabeca):
        return _abster(token, "Complemento sem controle pelo sujeito suficientemente sustentado; o objeto não foi promovido a sujeito.")
    herdado = _por_dependencia(base, cabeca, mencoes, escopos, por_id, visitados)
    if herdado.mencao is None:
        return _abster(token, "A cabeça da cadeia também não possui sujeito sustentado.", herdado.candidato_ids)
    return ResultadoSujeito(
        herdado.mencao, "dependencia_coordenacao" if relacao == "conj" else "dependencia_controle_sujeito",
        [f"Sujeito compartilhado pela dependência {token.dependencia} com {cabeca.texto!r}.", *herdado.razoes],
        [*herdado.evidencias, _intervalo(token)], herdado.candidato_ids,
    )


def _relativa_alguem(
    base: BaseLinguistica, token: TokenLinguistico, mencoes: list[Mention], escopos: dict,
) -> ResultadoSujeito | None:
    for complexa in mencoes:
        if complexa.origem != "paragrafo" or complexa.tipo != "descricao_complexa":
            continue
        dentro = complexa.intervalo.inicio < token.inicio < complexa.intervalo.fim
        depois = complexa.intervalo.fim <= token.inicio and not base.texto[complexa.intervalo.fim:token.inicio].strip()
        if not (dentro or depois):
            continue
        nucleo = next((item for item in mencoes if item.mencao_pai_id == complexa.id and item.texto.casefold() == "alguém"), None)
        if nucleo is None:
            continue
        contidos = _tokens_da_mencao(base, nucleo)
        if not contidos or not all(_mesmo_escopo(token, outro, escopos) for outro in contidos):
            continue
        # Só a relativa sem outro sujeito expresso permite recuperar o núcleo.
        inicio_relativa = base.texto.find("que", nucleo.intervalo.fim, token.inicio)
        if inicio_relativa < 0:
            continue
        concorrentes = [item for item in mencoes if item.origem == "paragrafo" and item.id not in {nucleo.id, complexa.id}
                        and inicio_relativa < item.intervalo.inicio < item.intervalo.fim <= token.inicio
                        and item.tipo in {"pronome_pessoal", "nome_proprio"}]
        if concorrentes:
            return None
        return ResultadoSujeito(nucleo, "nucleo_relativa_local", [
            "A relativa de 'alguém' não apresenta outro sujeito expresso; preservado o núcleo da descrição."
        ], [_intervalo(nucleo), _intervalo(token)], [nucleo.id])
    return None


def _por_texto(
    base: BaseLinguistica, token: TokenLinguistico, mencoes: list[Mention], escopos: dict,
    visitados: frozenset[str] = frozenset(),
) -> ResultadoSujeito:
    if token.id in visitados:
        return _abster(token, "Ciclo na recuperação local do sujeito.")
    visitados = visitados | {token.id}
    explicito = _explicito_local(base, token, mencoes, escopos)
    if explicito:
        return explicito
    posposto = _posposto_relato(base, token, mencoes, escopos)
    if posposto:
        return posposto
    relativa = _relativa_alguem(base, token, mencoes, escopos)
    if relativa:
        return relativa
    anteriores = [outro for outro in base.tokens if outro.fim <= token.inicio and _mesmo_escopo(token, outro, escopos)
                  and outro.pos in {"VERB", "AUX"} and outro.lema not in _AUXILIARES]
    if not anteriores:
        return _abster(token, "Sujeito elíptico ou não detectado; nenhuma menção foi escolhida por proximidade.")
    anterior = anteriores[-1]
    entre = base.texto[anterior.fim:token.inicio]
    marcadores = list(re.finditer(r"\b(?:que|quando|enquanto|embora|porque|pois|se|para|e|nem|mas|porém|ou)\b|[,;:]", entre, re.IGNORECASE))
    if not marcadores or marcadores[-1].group().casefold() not in _COORDENADORES | {","}:
        return _abster(token, "Sem sujeito explícito ou coordenação local sustentada; objetos próximos não foram usados.")
    # Uma relativa imediatamente anterior pode terminar antes da coordenada.
    # Sem árvore, não se decide sua ligação por proximidade.
    periodo = next(item for item in base.periodos if item.id == token.periodo_id)
    antes_do_anterior = base.texto[periodo.inicio:anterior.inicio]
    if re.search(r"\bque\b", antes_do_anterior, re.IGNORECASE):
        # Complemento com sujeito explícito ("percebeu que João leu e saiu")
        # permite continuar com João, sem regressar ao sujeito de percebeu.
        anterior_sujeito = _explicito_local(base, anterior, mencoes, escopos)
        if anterior_sujeito is None or anterior_sujeito.mencao is None:
            return _abster(token, "Uma oração relativa ou completiva interveniente torna a coordenação local ambígua.")
        antes_mencao = base.texto[periodo.inicio:anterior_sujeito.mencao.intervalo.inicio]
        # A relativa com antecedente nominal e sujeito expresso não fornece
        # sujeito para a oração externa ("folha que Ana leu caiu").
        if not re.search(r"\b(?:percebeu|disse|afirmou|pensou|acredita|imaginou|viu|ouviu)\s+que\s*$", antes_mencao, re.IGNORECASE):
            return _abster(token, "Relativa interveniente sem ligação de coordenação comprovada.")
    herdado = _por_texto(base, anterior, mencoes, escopos, visitados)
    if herdado.mencao is None:
        return _abster(token, "O predicado anterior também não possui sujeito local sustentado.", herdado.candidato_ids)
    return ResultadoSujeito(herdado.mencao, "coordenacao_local", [
        "Coordenação local preserva o sujeito do predicado anterior; seus objetos não são candidatos.", *herdado.razoes
    ], [*herdado.evidencias, _intervalo(token)], herdado.candidato_ids)


def selecionar_sujeito(base: BaseLinguistica, token: TokenLinguistico, mencoes: list[Mention]) -> ResultadoSujeito:
    """Retorna uma menção existente ou uma abstenção justificada e auditável."""
    if base.token_em(token.inicio, token.fim) != token:
        raise ValueError("O predicado deve ser um token da base linguística informada.")
    escopos = _escopos(base)
    if token.dependencia is not None:
        return _por_dependencia(base, token, mencoes, escopos, {item.id: item for item in base.tokens})
    return _por_texto(base, token, mencoes, escopos)
