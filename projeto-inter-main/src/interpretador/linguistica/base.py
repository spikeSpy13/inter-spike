from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator

from .lexico import AUXILIARES_LEXICAIS, lematizar_palavra, pos_local


class _Intervalo(BaseModel):
    inicio: int = Field(ge=0, strict=True)
    fim: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def validar_intervalo(self) -> Self:
        if self.fim <= self.inicio:
            raise ValueError("O intervalo deve ter início menor que fim.")
        return self


class PeriodoLinguistico(_Intervalo):
    id: str
    texto: str


class TokenLinguistico(_Intervalo):
    id: str
    texto: str
    lema: str | None = None
    pos: str | None = None
    dependencia: str | None = None
    cabeca_id: str | None = None
    periodo_id: str | None = None
    origem: str = "heuristica_local"
    recebida: dict[str, Any] = Field(default_factory=dict)
    decisoes: list[str] = Field(default_factory=list)

    @property
    def normalizado(self) -> str:
        return self.texto.casefold()


class DiagnosticoLinguistico(BaseModel):
    codigo: str
    caminho: str
    mensagem: str
    token_id: str | None = None
    inicio: int | None = Field(default=None, ge=0, strict=True)
    fim: int | None = Field(default=None, gt=0, strict=True)

    @model_validator(mode="after")
    def validar_intervalo(self) -> Self:
        if (self.inicio is None) != (self.fim is None):
            raise ValueError("O diagnóstico deve informar ambos os limites ou nenhum.")
        if self.inicio is not None and self.fim <= self.inicio:
            raise ValueError("O diagnóstico deve ter início menor que fim.")
        return self


class BaseLinguistica(BaseModel):
    texto: str
    inicio_original: int = Field(default=0, ge=0, strict=True)
    tokens: list[TokenLinguistico]
    periodos: list[PeriodoLinguistico]
    diagnosticos: list[DiagnosticoLinguistico] = Field(default_factory=list)
    origem: str = "heuristica_local"

    @model_validator(mode="after")
    def validar_recortes(self) -> Self:
        ids = set()
        for item in [*self.periodos, *self.tokens]:
            if item.id in ids:
                raise ValueError("Identificador duplicado na base linguística.")
            ids.add(item.id)
            if self.texto[item.inicio:item.fim] != item.texto or item.fim > len(self.texto):
                raise ValueError("O intervalo local não corresponde ao texto informado.")
        periodos = {item.id: item for item in self.periodos}
        for token in self.tokens:
            periodo = periodos.get(token.periodo_id)
            if not periodo or not (periodo.inicio <= token.inicio < token.fim <= periodo.fim):
                raise ValueError("O token deve pertencer a um período que contenha seu intervalo.")
        return self

    def token_em(self, inicio: int, fim: int) -> TokenLinguistico | None:
        """Busca um token pelo intervalo local exato, em pontos de código."""
        return next((item for item in self.tokens if (item.inicio, item.fim) == (inicio, fim)), None)


@dataclass(frozen=True)
class ProblemaAnotacao:
    codigo: str
    caminho: str
    mensagem: str


class ErroAnotacao(ValueError):
    def __init__(self, problemas: list[ProblemaAnotacao]):
        self.problemas = tuple(problemas)
        super().__init__(problemas[0].mensagem if problemas else "Anotação inválida.")


_TOKEN_RE = re.compile(r"[^\W_]+(?:[-'][^\W\d_]+)*|[^\w\s]", re.UNICODE)
_FECHAMENTOS = '"”»’\')]}'
_ABREVIACOES = {"dr", "dra", "sr", "sra", "prof", "profa"}
_SEG = "$.contexto.regras.analise.anotacao.segmentacao"
_MORF = "$.contexto.regras.analise.anotacao.anotacoes_tokens"
_SINT = "$.contexto.regras.analise.sintaxe"


def _periodos_locais(texto: str) -> list[PeriodoLinguistico]:
    limites = []
    inicio = 0
    indice = 0
    while indice < len(texto):
        caractere = texto[indice]
        if caractere in ".!?":
            fim = indice + 1
            while fim < len(texto) and texto[fim] in ".!?":
                fim += 1
            # Reticências e abreviações protegidas não encerram um período.
            palavra = re.search(r"([^\W\d_]+)$", texto[inicio:indice], re.UNICODE)
            abreviacao = caractere == "." and palavra and palavra.group(1).casefold() in _ABREVIACOES
            reticencias = texto[indice:fim] == "..."
            while fim < len(texto) and texto[fim] in _FECHAMENTOS:
                fim += 1
            if not abreviacao and not reticencias and (fim == len(texto) or texto[fim].isspace()):
                limites.append((inicio, fim))
                inicio = fim
                indice = fim
                continue
        indice += 1
    if inicio < len(texto):
        limites.append((inicio, len(texto)))
    periodos = []
    for inicio, fim in limites:
        while inicio < fim and texto[inicio].isspace():
            inicio += 1
        while fim > inicio and texto[fim - 1].isspace():
            fim -= 1
        if inicio < fim:
            periodos.append(PeriodoLinguistico(id=f"local:periodo:{len(periodos)}", texto=texto[inicio:fim], inicio=inicio, fim=fim))
    return periodos


def analisar_texto(texto: str) -> BaseLinguistica:
    """Analisa sem rede; limites e lemas locais são hipóteses explícitas."""
    if not isinstance(texto, str):
        raise TypeError("O texto deve ser uma string.")
    periodos = _periodos_locais(texto)
    tokens = []
    for match in _TOKEN_RE.finditer(texto):
        periodo = next(item for item in periodos if item.inicio <= match.start() < match.end() <= item.fim)
        lema, pos = lematizar_palavra(match.group()), pos_local(match.group())
        tokens.append(TokenLinguistico(
            id=f"local:token:{len(tokens)}", texto=match.group(), inicio=match.start(), fim=match.end(),
            lema=lema, pos=pos, periodo_id=periodo.id,
            decisoes=["lema_do_lexico_local"] if lema else [],
        ))
    return BaseLinguistica(
        texto=texto, tokens=tokens, periodos=periodos,
        diagnosticos=[DiagnosticoLinguistico(
            codigo="analise_local_limitada", caminho="$",
            mensagem="Análise local com léxico fechado; palavras desconhecidas e relações sintáticas não são inferidas.",
        )],
    )


class _Validador:
    def __init__(self, original: str):
        self.original = original
        self.problemas: list[ProblemaAnotacao] = []

    def erro(self, codigo: str, caminho: str, mensagem: str) -> None:
        self.problemas.append(ProblemaAnotacao(codigo, caminho, mensagem))

    def concluir(self) -> None:
        if self.problemas:
            raise ErroAnotacao(self.problemas)

    def lista(self, valor: Any, caminho: str) -> list:
        if not isinstance(valor, list):
            self.erro("tipo_invalido", caminho, "O campo deve ser uma lista.")
            return []
        return valor

    def indice(self, valores: Any, caminho: str, chave: str = "id") -> dict[str, tuple[dict, str]]:
        indice = {}
        for i, valor in enumerate(self.lista(valores, caminho)):
            local = f"{caminho}[{i}]"
            if not isinstance(valor, dict):
                self.erro("tipo_invalido", local, "Cada anotação deve ser um objeto JSON.")
                continue
            ident = valor.get(chave)
            if not isinstance(ident, str) or not ident:
                self.erro("identificador_invalido", f"{local}.{chave}", "Identificador ausente ou inválido.")
                continue
            if ident in indice:
                self.erro("identificador_duplicado", f"{local}.{chave}", "Identificador repetido na mesma coleção.")
                continue
            indice[ident] = (valor, local)
        return indice

    def intervalo(self, item: dict, caminho: str) -> tuple[int, int] | None:
        valor = item.get("original")
        if not isinstance(valor, dict):
            self.erro("intervalo_invalido", f"{caminho}.original", "O intervalo original deve ser um objeto.")
            return None
        inicio, fim = valor.get("inicio"), valor.get("fim")
        if type(inicio) is not int or type(fim) is not int or not (0 <= inicio < fim <= len(self.original)):
            self.erro("intervalo_invalido", f"{caminho}.original", "Intervalo fora do texto original ou limites inválidos.")
            return None
        if not isinstance(item.get("texto"), str) or self.original[inicio:fim] != item["texto"]:
            self.erro("texto_divergente", f"{caminho}.texto", "O texto não corresponde ao recorte original.")
        if "trabalho" in item:
            trabalho = item["trabalho"]
            if not isinstance(trabalho, dict) or type(trabalho.get("inicio")) is not int or type(trabalho.get("fim")) is not int:
                self.erro("intervalo_invalido", f"{caminho}.trabalho", "Os limites de trabalho devem ser inteiros, sem conversão de booleans.")
            elif trabalho != valor:
                self.erro("coordenadas_trabalho_divergentes", f"{caminho}.trabalho", "A adaptação literal requer coordenadas de trabalho iguais às originais.")
        return inicio, fim

    def referencia(self, item: dict, chave: str, indice: dict, caminho: str) -> bool:
        valor = item.get(chave)
        if not isinstance(valor, str) or valor not in indice:
            self.erro("referencia_quebrada", f"{caminho}.{chave}", "O identificador não existe na segmentação.")
            return False
        return True


def _validar_segmentacao(v: _Validador, segmentacao: dict) -> tuple[dict, dict, dict]:
    if not isinstance(segmentacao, dict):
        v.erro("tipo_invalido", _SEG, "A segmentação deve ser um objeto JSON.")
        v.concluir()
    paragrafos = v.indice(segmentacao.get("paragrafos"), f"{_SEG}.paragrafos")
    periodos = v.indice(segmentacao.get("periodos"), f"{_SEG}.periodos")
    tokens = v.indice(segmentacao.get("tokens"), f"{_SEG}.tokens")
    if v.original.strip() and (not paragrafos or not periodos or not tokens):
        v.erro("segmentacao_incompleta", _SEG, "Texto não vazio requer parágrafos, períodos e tokens.")
    vistos = set()
    for grupo in (paragrafos, periodos, tokens):
        for ident, (_, caminho) in grupo.items():
            if ident in vistos:
                v.erro("identificador_duplicado", f"{caminho}.id", "O identificador já pertence a outro elemento da segmentação.")
            vistos.add(ident)
    intervalos = {}
    for grupo in (paragrafos, periodos, tokens):
        anterior = -1
        for ident, (item, caminho) in grupo.items():
            intervalo = v.intervalo(item, caminho)
            if intervalo:
                intervalos[ident] = intervalo
                if intervalo[0] < anterior:
                    v.erro("intervalos_sobrepostos", f"{caminho}.original", "Os intervalos devem estar ordenados e não podem se sobrepor.")
                anterior = intervalo[1]
    for ident, (item, caminho) in periodos.items():
        if v.referencia(item, "paragrafo_id", paragrafos, caminho):
            pai, filho = intervalos.get(item["paragrafo_id"]), intervalos.get(ident)
            if pai and filho and not (pai[0] <= filho[0] < filho[1] <= pai[1]):
                v.erro("intervalo_fora_do_pai", f"{caminho}.original", "O período deve estar contido no seu parágrafo.")
    for ident, (item, caminho) in tokens.items():
        valido = v.referencia(item, "paragrafo_id", paragrafos, caminho)
        valido = v.referencia(item, "periodo_id", periodos, caminho) and valido
        if valido:
            periodo = periodos[item["periodo_id"]][0]
            if periodo.get("paragrafo_id") != item["paragrafo_id"]:
                v.erro("referencia_divergente", f"{caminho}.paragrafo_id", "Token e período devem pertencer ao mesmo parágrafo.")
            pai, filho = intervalos.get(item["periodo_id"]), intervalos.get(ident)
            if pai and filho and not (pai[0] <= filho[0] < filho[1] <= pai[1]):
                v.erro("intervalo_fora_do_pai", f"{caminho}.original", "O token deve estar contido no seu período.")
    for pais, campo, filhos, referencia in (
        (paragrafos, "periodos", periodos, "paragrafo_id"),
        (periodos, "tokens", tokens, "periodo_id"),
    ):
        for ident, (item, caminho) in pais.items():
            if campo not in item:
                continue
            ids = v.lista(item[campo], f"{caminho}.{campo}")
            esperados = [filho_id for filho_id, (filho, _) in filhos.items() if filho.get(referencia) == ident]
            if not all(isinstance(valor, str) for valor in ids) or ids != esperados:
                v.erro("referencia_divergente", f"{caminho}.{campo}", "A lista de filhos deve corresponder à segmentação, sem repetições e em ordem.")
    v.concluir()
    return paragrafos, periodos, tokens


def _validar_anotacoes(v: _Validador, valores: list | None, caminho: str, tokens: dict, sintaxe: bool = False) -> dict:
    if valores is None:
        return {}
    indice = v.indice(valores, caminho, "token_id")
    for ident, (item, local) in indice.items():
        if ident not in tokens:
            v.erro("referencia_quebrada", f"{local}.token_id", "A anotação aponta para token inexistente.")
            continue
        token = tokens[ident][0]
        v.intervalo(item, local)
        for campo in ("texto", "original", "periodo_id", "paragrafo_id"):
            if item.get(campo) != token.get(campo):
                v.erro("anotacao_divergente", f"{local}.{campo}", "A anotação não corresponde ao token da segmentação.")
        if sintaxe:
            dependencia, cabeca = item.get("dependencia"), item.get("cabeca_token_id")
            if not isinstance(dependencia, str) or not dependencia.strip():
                v.erro("tipo_invalido", f"{local}.dependencia", "A dependência deve ser uma string não vazia.")
            if not isinstance(cabeca, str) or cabeca not in tokens:
                v.erro("referencia_quebrada", f"{local}.cabeca_token_id", "A cabeça deve apontar para um token existente.")
            elif tokens[cabeca][0]["periodo_id"] != token["periodo_id"]:
                v.erro("cabeca_fora_do_periodo", f"{local}.cabeca_token_id", "A cabeça deve pertencer ao mesmo período.")
            elif cabeca == ident and dependencia != "ROOT":
                v.erro("ciclo_sintatico", f"{local}.cabeca_token_id", "Somente uma raiz ROOT pode apontar para si mesma.")
            elif dependencia == "ROOT" and cabeca != ident:
                v.erro("raiz_invalida", f"{local}.cabeca_token_id", "Uma raiz ROOT deve apontar para si mesma.")
        else:
            for campo in ("lema", "pos"):
                if campo not in item or (item[campo] is not None and (not isinstance(item[campo], str) or not item[campo].strip())):
                    v.erro("tipo_invalido", f"{local}.{campo}", "O campo deve ser uma string não vazia ou null explícito.")
            if "morfologia" in item and not isinstance(item["morfologia"], dict):
                v.erro("tipo_invalido", f"{local}.morfologia", "Os traços morfológicos devem ser um objeto JSON.")
            if isinstance(item.get("pos"), str) and item["pos"] not in {"ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", "NOUN", "NUM", "PART", "PRON", "PROPN", "PUNCT", "SCONJ", "SYM", "VERB", "X", "SPACE"}:
                v.erro("classe_gramatical_invalida", f"{local}.pos", "A classe deve usar uma etiqueta gramatical universal conhecida.")
    if sintaxe:
        visitados = set()
        for ident in indice:
            cadeia = set()
            atual = ident
            while atual in indice and atual not in visitados:
                if atual in cadeia:
                    v.erro("ciclo_sintatico", f"{indice[atual][1]}.cabeca_token_id", "A cadeia sintática contém um ciclo.")
                    break
                cadeia.add(atual)
                item = indice[atual][0]
                proximo = item.get("cabeca_token_id")
                if proximo == atual or not isinstance(proximo, str):
                    break
                atual = proximo
            visitados.update(cadeia)
    v.concluir()
    return indice


def adaptar_anotacoes(
    texto_original: str,
    segmentacao: dict,
    anotacoes_tokens: list | None,
    sintaxe: list | None,
) -> dict[str, BaseLinguistica]:
    """Valida a fonte inteira antes de adaptar intervalos globais para locais.

    As árvores recebidas permanecem hipóteses: integridade dos IDs não equivale
    a correção semântica. Não atribui sujeitos nem cria relações proposicionais.
    """
    if not isinstance(texto_original, str):
        raise ErroAnotacao([ProblemaAnotacao("tipo_invalido", "$.texto_original", "O texto original deve ser uma string.")])
    v = _Validador(texto_original)
    paragrafos, periodos, tokens = _validar_segmentacao(v, segmentacao)
    morfologia = _validar_anotacoes(v, anotacoes_tokens, _MORF, tokens)
    arvores = _validar_anotacoes(v, sintaxe, _SINT, tokens, sintaxe=True)
    resultado = {}
    for paragrafo_id, (paragrafo, _) in paragrafos.items():
        inicio_original = paragrafo["original"]["inicio"]
        diagnosticos = [DiagnosticoLinguistico(
            codigo="anotacoes_sao_hipoteses", caminho="$.contexto.regras.analise",
            mensagem="Predições recebidas preservadas; integridade estrutural não certifica correção linguística.",
        )]
        if not morfologia and not arvores:
            diagnosticos.append(DiagnosticoLinguistico(
                codigo="anotacoes_ausentes", caminho="$.contexto.regras.analise",
                mensagem="Não foram fornecidas anotações morfológicas nem sintáticas; aplicada a análise lexical local.",
            ))
        periodos_locais = [PeriodoLinguistico(
            id=ident, texto=item["texto"],
            inicio=item["original"]["inicio"] - inicio_original,
            fim=item["original"]["fim"] - inicio_original,
        ) for ident, (item, _) in periodos.items() if item["paragrafo_id"] == paragrafo_id]
        tokens_locais = []
        for ident, (item, _) in tokens.items():
            if item["paragrafo_id"] != paragrafo_id:
                continue
            inicio = item["original"]["inicio"] - inicio_original
            fim = item["original"]["fim"] - inicio_original
            morf, caminho_morf = morfologia.get(ident, ({}, _MORF))
            arvore, caminho_sint = arvores.get(ident, ({}, _SINT))
            lema_local, classe_local = lematizar_palavra(item["texto"]), pos_local(item["texto"])
            lema, classe = morf.get("lema"), morf.get("pos")
            decisoes = []

            def diagnosticar(codigo: str, caminho: str, mensagem: str) -> None:
                diagnosticos.append(DiagnosticoLinguistico(codigo=codigo, caminho=caminho, mensagem=mensagem,
                                                          token_id=ident, inicio=inicio, fim=fim))

            if not morf:
                lema, classe = lema_local, classe_local
                decisoes.append("analise_lexical_local")
                if morfologia or arvores:
                    diagnosticar("morfologia_ausente", _MORF, "Token sem anotação morfológica; aplicada a análise lexical local.")
            elif lema_local:
                if lema != lema_local:
                    diagnosticar("conflito_lema", f"{caminho_morf}.lema", f"Lema recebido {lema!r}; o léxico local sustenta {lema_local!r}.")
                    decisoes.append("lema_corrigido_por_lexico_local")
                lema = lema_local
                # Auxiliares recebidos são preservados somente nas famílias
                # auxiliares. Um parser não torna 'decidi' um auxiliar lexical.
                auxiliar_compativel = item["texto"].casefold() in AUXILIARES_LEXICAIS or lema in {"ser", "estar", "ter", "haver", "ir", "poder", "dever", "querer"}
                classe_esperada = "AUX" if classe == "AUX" and auxiliar_compativel else classe_local
                if classe not in {"VERB", "AUX"} or (classe == "AUX" and not auxiliar_compativel):
                    diagnosticar("conflito_pos", f"{caminho_morf}.pos", f"Classe recebida {classe!r}; forma verbal conhecida, adotada {classe_esperada!r}.")
                    decisoes.append("pos_corrigida_por_lexico_local")
                classe = classe_esperada
            elif classe_local:
                # 'a', 'se' e outros itens funcionais são ambíguos. Não trocar
                # uma classe funcional recebida por outra só pelo léxico.
                rever_classe = classe in {None, "PROPN", "NOUN", "VERB", "AUX"} or classe_local == "PUNCT"
                if rever_classe and classe != classe_local:
                    diagnosticar("conflito_pos", f"{caminho_morf}.pos", f"Classe recebida {classe!r}; função local {classe_local!r} evita um participante ou predicado falso.")
                    decisoes.append("pos_corrigida_por_regra_lexical")
                if rever_classe:
                    classe = classe_local
                if classe_local == "PUNCT":
                    lema = None
            elif classe in {"VERB", "AUX"}:
                if not isinstance(lema, str) or not re.fullmatch(r"[^\W\d_]+(?:ar|er|ir|or)", lema.casefold(), re.UNICODE):
                    diagnosticar("lema_verbal_nao_sustentado", f"{caminho_morf}.lema", "Lema verbal recebido não reconhecido como infinitivo; mantida abstenção lexical.")
                    lema = None
                    decisoes.append("lema_nao_inferido")
                else:
                    decisoes.append("lema_recebido_como_hipotese")
            if not arvore and (morfologia or arvores):
                diagnosticar("sintaxe_ausente", _SINT, "Token sem anotação sintática; nenhuma dependência foi inventada.")
            if arvore.get("dependencia", "").split(":")[0] == "aux" and classe == "VERB" and lema not in {"ser", "estar", "ter", "haver", "ir", "poder", "dever", "querer"}:
                diagnosticar("conflito_auxiliar_lexical", f"{caminho_sint}.dependencia", "O parser marcou aux para um verbo lexical; a dependência recebida exige revisão.")
            if item["texto"].casefold() in {"decidi", "achei", "respondi", "peguei", "saí", "atrasei", "terminei", "enviei", "fiquei", "deixei", "corri", "arrumei", "imprimi", "voltei", "retornei", "estudei", "escrevi"}:
                tracos = morf.get("morfologia", {})
                esperados = {"Person": "1", "Mood": "Ind", "Tense": "Past"}
                conflitos = {chave: valor for chave, valor in esperados.items() if chave in tracos and tracos[chave] != valor}
                if conflitos:
                    diagnosticar("conflito_tracos_morfologicos", f"{caminho_morf}.morfologia", f"Forma conhecida de primeira pessoa do passado; traços recebidos em conflito: {', '.join(sorted(conflitos))}.")
                    decisoes.append("tracos_recebidos_exigem_revisao")
            tokens_locais.append(TokenLinguistico(
                id=ident, texto=item["texto"], inicio=inicio, fim=fim, lema=lema, pos=classe,
                dependencia=arvore.get("dependencia"), cabeca_id=arvore.get("cabeca_token_id"),
                periodo_id=item["periodo_id"], origem="anotacao_com_revisao_local" if morf or arvore else "heuristica_local",
                recebida={"morfologia": deepcopy(morf) if morf else None, "sintaxe": deepcopy(arvore) if arvore else None},
                decisoes=decisoes,
            ))
        resultado[paragrafo_id] = BaseLinguistica(
            texto=paragrafo["texto"], inicio_original=inicio_original, tokens=tokens_locais,
            periodos=periodos_locais, diagnosticos=diagnosticos,
            origem="anotacoes_com_revisao_local" if morfologia or arvores else "heuristica_local",
        )
    return resultado
