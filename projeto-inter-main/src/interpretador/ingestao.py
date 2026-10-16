"""Ingestão e validação da saída estruturada da etapa 09_vetorizacao."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any


SCHEMA_SUPORTADO = "1.0.0"
ETAPA_SUPORTADA = "09_vetorizacao"


@dataclass(frozen=True)
class ProblemaIngestao:
    codigo: str
    caminho: str
    mensagem: str

    def serializar(self) -> dict[str, str]:
        return {
            "codigo": self.codigo,
            "caminho": self.caminho,
            "mensagem": self.mensagem,
        }


class ErroIngestao(ValueError):
    def __init__(self, problemas: list[ProblemaIngestao]):
        self.problemas = problemas
        super().__init__(problemas[0].mensagem if problemas else "JSON incompatível.")


@dataclass(frozen=True)
class ParagrafoIngerido:
    id: str
    rotulo: str
    ordem: int
    texto: str
    inicio_original: int
    fim_original: int
    representacao_id: str
    artefato_id: str


@dataclass(frozen=True)
class DocumentoIngerido:
    documento_id: int | str
    schema_version: str
    etapa: str
    texto_original: str
    paragrafos: tuple[ParagrafoIngerido, ...]
    periodos_total: int
    tokens_total: int
    representacoes_total: int
    artefatos_total: int
    dimensao_vetores: int

    def selecionar(self, paragrafo_id: str) -> ParagrafoIngerido:
        for paragrafo in self.paragrafos:
            if paragrafo.id == paragrafo_id or paragrafo.rotulo == paragrafo_id:
                return paragrafo
        raise ErroIngestao(
            [
                ProblemaIngestao(
                    "paragrafo_inexistente",
                    "$.paragrafo_id",
                    f"O parágrafo {paragrafo_id!r} não existe no documento validado.",
                )
            ]
        )

    def contexto_anterior(self, paragrafo: ParagrafoIngerido) -> str | None:
        anteriores = [item for item in self.paragrafos if item.ordem < paragrafo.ordem]
        if not anteriores:
            return None
        anterior = max(anteriores, key=lambda item: item.ordem)
        return anterior.texto


class _Coletor:
    def __init__(self) -> None:
        self.problemas: list[ProblemaIngestao] = []

    def adicionar(self, codigo: str, caminho: str, mensagem: str) -> None:
        self.problemas.append(ProblemaIngestao(codigo, caminho, mensagem))

    def concluir(self) -> None:
        if self.problemas:
            raise ErroIngestao(self.problemas)


def _buscar(raiz: Any, caminho: tuple[str, ...], coletor: _Coletor) -> Any:
    atual = raiz
    percorrido = "$"
    for chave in caminho:
        percorrido += f".{chave}"
        if not isinstance(atual, dict) or chave not in atual:
            coletor.adicionar(
                "campo_obrigatorio_ausente",
                percorrido,
                "Campo obrigatório ausente.",
            )
            return None
        atual = atual[chave]
    return atual


def _lista(valor: Any, caminho: str, coletor: _Coletor) -> list[Any]:
    if not isinstance(valor, list):
        coletor.adicionar("tipo_invalido", caminho, "O campo deve ser uma lista.")
        return []
    return valor


def _objeto(valor: Any, caminho: str, coletor: _Coletor) -> dict[str, Any]:
    if not isinstance(valor, dict):
        coletor.adicionar("tipo_invalido", caminho, "O campo deve ser um objeto JSON.")
        return {}
    return valor


def _identificador(valor: Any, caminho: str, coletor: _Coletor) -> str | None:
    if not isinstance(valor, str) or not valor:
        coletor.adicionar("identificador_invalido", caminho, "Identificador ausente ou inválido.")
        return None
    return valor


def _intervalo(
    valor: Any,
    caminho: str,
    limite: int,
    coletor: _Coletor,
) -> tuple[int, int] | None:
    intervalo = _objeto(valor, caminho, coletor)
    inicio = intervalo.get("inicio")
    fim = intervalo.get("fim")
    if (
        not isinstance(inicio, int)
        or isinstance(inicio, bool)
        or not isinstance(fim, int)
        or isinstance(fim, bool)
        or inicio < 0
        or fim <= inicio
        or fim > limite
    ):
        coletor.adicionar(
            "intervalo_invalido",
            caminho,
            f"O intervalo deve obedecer a 0 <= início < fim <= {limite}.",
        )
        return None
    return inicio, fim


def _registrar_ids(
    itens: list[Any],
    caminho: str,
    coletor: _Coletor,
) -> dict[str, dict[str, Any]]:
    indice: dict[str, dict[str, Any]] = {}
    for posicao, valor in enumerate(itens):
        item = _objeto(valor, f"{caminho}[{posicao}]", coletor)
        identificador = _identificador(item.get("id"), f"{caminho}[{posicao}].id", coletor)
        if identificador is None:
            continue
        if identificador in indice:
            coletor.adicionar(
                "identificador_duplicado",
                f"{caminho}[{posicao}].id",
                f"O identificador {identificador!r} aparece mais de uma vez.",
            )
        else:
            indice[identificador] = item
    return indice


def _validar_texto_intervalo(
    item: dict[str, Any],
    caminho: str,
    original: str,
    coletor: _Coletor,
) -> tuple[int, int] | None:
    intervalo = _intervalo(item.get("original"), f"{caminho}.original", len(original), coletor)
    texto = item.get("texto")
    if not isinstance(texto, str):
        coletor.adicionar("tipo_invalido", f"{caminho}.texto", "O texto deve ser uma string.")
        return intervalo
    if intervalo and original[intervalo[0] : intervalo[1]] != texto:
        coletor.adicionar(
            "texto_divergente",
            f"{caminho}.texto",
            "O texto não corresponde ao recorte indicado no original.",
        )
    return intervalo


def validar_documento(documento: Any) -> DocumentoIngerido:
    """Valida referências, coordenadas e vetores e cria uma visão interna enxuta."""

    coletor = _Coletor()
    raiz = _objeto(documento, "$", coletor)
    if not raiz:
        coletor.concluir()

    schema_version = _buscar(raiz, ("schema_version",), coletor)
    etapa = _buscar(raiz, ("etapa",), coletor)
    documento_id = _buscar(raiz, ("documento_id",), coletor)
    if schema_version != SCHEMA_SUPORTADO:
        coletor.adicionar(
            "schema_incompativel",
            "$.schema_version",
            f"Versão incompatível: esperada {SCHEMA_SUPORTADO!r}.",
        )
    if etapa != ETAPA_SUPORTADA:
        coletor.adicionar(
            "etapa_incompativel",
            "$.etapa",
            f"Etapa incompatível: esperada {ETAPA_SUPORTADA!r}.",
        )
    if isinstance(documento_id, bool) or not isinstance(documento_id, (int, str)):
        coletor.adicionar("documento_invalido", "$.documento_id", "Identificador de documento inválido.")

    validacao = _objeto(_buscar(raiz, ("validacao",), coletor), "$.validacao", coletor)
    if validacao.get("estado") != "concluida" or validacao.get("pronto") is not True:
        coletor.adicionar(
            "validacao_incompleta",
            "$.validacao",
            "A vetorização deve estar com estado 'concluida' e pronto igual a true.",
        )

    contexto = _objeto(_buscar(raiz, ("contexto",), coletor), "$.contexto", coletor)
    if contexto.get("documento_id") != documento_id:
        coletor.adicionar(
            "referencia_quebrada",
            "$.contexto.documento_id",
            "O contexto aponta para outro documento.",
        )
    coordenadas = _objeto(contexto.get("coordenadas"), "$.contexto.coordenadas", coletor)
    if (
        coordenadas.get("unidade") != "pontos_de_codigo_unicode"
        or coordenadas.get("base") != 0
        or coordenadas.get("fim_exclusivo") is not True
    ):
        coletor.adicionar(
            "coordenadas_incompativeis",
            "$.contexto.coordenadas",
            "As coordenadas devem usar pontos de código Unicode, base zero e fim exclusivo.",
        )

    caminho_segmentacao = "$.contexto.regras.analise.anotacao.segmentacao"
    segmentacao = _objeto(
        _buscar(contexto, ("regras", "analise", "anotacao", "segmentacao"), coletor),
        caminho_segmentacao,
        coletor,
    )
    original = _buscar(segmentacao, ("preparacao", "original", "texto"), coletor)
    if not isinstance(original, str) or not original:
        coletor.adicionar(
            "texto_original_invalido",
            "$.contexto.regras.analise.anotacao.segmentacao.preparacao.original.texto",
            "O texto original deve ser uma string não vazia.",
        )
        original = ""

    paragrafos = _lista(segmentacao.get("paragrafos"), f"{caminho_segmentacao}.paragrafos", coletor)
    periodos = _lista(segmentacao.get("periodos"), f"{caminho_segmentacao}.periodos", coletor)
    tokens = _lista(segmentacao.get("tokens"), f"{caminho_segmentacao}.tokens", coletor)
    unidades = _lista(contexto.get("unidades"), "$.contexto.unidades", coletor)
    representacoes = _lista(raiz.get("representacoes"), "$.representacoes", coletor)
    artefatos = _lista(raiz.get("artefatos"), "$.artefatos", coletor)

    paragrafos_por_id = _registrar_ids(paragrafos, f"{caminho_segmentacao}.paragrafos", coletor)
    periodos_por_id = _registrar_ids(periodos, f"{caminho_segmentacao}.periodos", coletor)
    tokens_por_id = _registrar_ids(tokens, f"{caminho_segmentacao}.tokens", coletor)
    unidades_por_id = _registrar_ids(unidades, "$.contexto.unidades", coletor)
    representacoes_por_id = _registrar_ids(representacoes, "$.representacoes", coletor)
    artefatos_por_id = _registrar_ids(artefatos, "$.artefatos", coletor)

    intervalos_paragrafos: dict[str, tuple[int, int]] = {}
    for posicao, item in enumerate(paragrafos):
        if not isinstance(item, dict):
            continue
        caminho = f"{caminho_segmentacao}.paragrafos[{posicao}]"
        identificador = item.get("id")
        intervalo = _validar_texto_intervalo(item, caminho, original, coletor)
        if isinstance(identificador, str) and intervalo:
            intervalos_paragrafos[identificador] = intervalo
        referencias = _lista(item.get("periodos"), f"{caminho}.periodos", coletor)
        for indice, periodo_id in enumerate(referencias):
            if periodo_id not in periodos_por_id:
                coletor.adicionar(
                    "referencia_quebrada",
                    f"{caminho}.periodos[{indice}]",
                    f"Período inexistente: {periodo_id!r}.",
                )
            elif periodos_por_id[periodo_id].get("paragrafo_id") != identificador:
                coletor.adicionar(
                    "referencia_inconsistente",
                    f"{caminho}.periodos[{indice}]",
                    "O período pertence a outro parágrafo.",
                )

    for posicao, item in enumerate(periodos):
        if not isinstance(item, dict):
            continue
        caminho = f"{caminho_segmentacao}.periodos[{posicao}]"
        intervalo = _validar_texto_intervalo(item, caminho, original, coletor)
        paragrafo_id = item.get("paragrafo_id")
        if paragrafo_id not in paragrafos_por_id:
            coletor.adicionar(
                "referencia_quebrada",
                f"{caminho}.paragrafo_id",
                f"Parágrafo inexistente: {paragrafo_id!r}.",
            )
        elif intervalo and paragrafo_id in intervalos_paragrafos:
            inicio_p, fim_p = intervalos_paragrafos[paragrafo_id]
            if intervalo[0] < inicio_p or intervalo[1] > fim_p:
                coletor.adicionar(
                    "intervalo_fora_do_paragrafo",
                    f"{caminho}.original",
                    "O período ultrapassa o intervalo do parágrafo indicado.",
                )
        referencias = _lista(item.get("tokens"), f"{caminho}.tokens", coletor)
        for indice, token_id in enumerate(referencias):
            if token_id not in tokens_por_id:
                coletor.adicionar(
                    "referencia_quebrada",
                    f"{caminho}.tokens[{indice}]",
                    f"Token inexistente: {token_id!r}.",
                )
            elif tokens_por_id[token_id].get("periodo_id") != item.get("id"):
                coletor.adicionar(
                    "referencia_inconsistente",
                    f"{caminho}.tokens[{indice}]",
                    "O token pertence a outro período.",
                )

    for posicao, item in enumerate(tokens):
        if not isinstance(item, dict):
            continue
        caminho = f"{caminho_segmentacao}.tokens[{posicao}]"
        intervalo = _validar_texto_intervalo(item, caminho, original, coletor)
        paragrafo_id = item.get("paragrafo_id")
        periodo_id = item.get("periodo_id")
        if paragrafo_id not in paragrafos_por_id:
            coletor.adicionar(
                "referencia_quebrada",
                f"{caminho}.paragrafo_id",
                "Parágrafo do token inexistente.",
            )
        if periodo_id not in periodos_por_id:
            coletor.adicionar("referencia_quebrada", f"{caminho}.periodo_id", "Período do token inexistente.")
        elif intervalos_paragrafos.get(paragrafo_id) and intervalo:
            intervalo_periodo = periodos_por_id[periodo_id].get("original")
            if isinstance(intervalo_periodo, dict):
                inicio_periodo = intervalo_periodo.get("inicio")
                fim_periodo = intervalo_periodo.get("fim")
                if isinstance(inicio_periodo, int) and isinstance(fim_periodo, int) and (
                    intervalo[0] < inicio_periodo or intervalo[1] > fim_periodo
                ):
                    coletor.adicionar(
                        "intervalo_fora_do_periodo",
                        f"{caminho}.original",
                        "O token ultrapassa o intervalo do período indicado.",
                    )

    for posicao, item in enumerate(unidades):
        if not isinstance(item, dict):
            continue
        caminho = f"$.contexto.unidades[{posicao}]"
        if item.get("paragrafo_foco_id") not in paragrafos_por_id:
            coletor.adicionar(
                "referencia_quebrada",
                f"{caminho}.paragrafo_foco_id",
                "Parágrafo de foco inexistente.",
            )
        if item.get("periodo_foco_id") not in periodos_por_id:
            coletor.adicionar("referencia_quebrada", f"{caminho}.periodo_foco_id", "Período de foco inexistente.")
        for campo in ("anteriores", "seguintes"):
            referencias = _lista(item.get(campo), f"{caminho}.{campo}", coletor)
            for indice, periodo_id in enumerate(referencias):
                if periodo_id not in periodos_por_id:
                    coletor.adicionar(
                        "referencia_quebrada",
                        f"{caminho}.{campo}[{indice}]",
                        f"Período de contexto inexistente: {periodo_id!r}.",
                    )
        foco = _objeto(item.get("foco"), f"{caminho}.foco", coletor)
        intervalo = _intervalo(foco.get("original"), f"{caminho}.foco.original", len(original), coletor)
        texto_foco = foco.get("texto_original")
        if intervalo and texto_foco != original[intervalo[0] : intervalo[1]]:
            coletor.adicionar(
                "texto_divergente",
                f"{caminho}.foco.texto_original",
                "O foco não corresponde ao recorte do texto original.",
            )

    processamento = _objeto(raiz.get("processamento"), "$.processamento", coletor)
    dimensao_processamento = processamento.get("dimensao")
    if (
        not isinstance(dimensao_processamento, int)
        or isinstance(dimensao_processamento, bool)
        or dimensao_processamento <= 0
    ):
        coletor.adicionar("dimensao_invalida", "$.processamento.dimensao", "A dimensão deve ser um inteiro positivo.")
        dimensao_processamento = 0

    for posicao, item in enumerate(artefatos):
        if not isinstance(item, dict):
            continue
        caminho = f"$.artefatos[{posicao}]"
        dimensao = item.get("dimensao")
        valores = item.get("valores")
        if not isinstance(dimensao, int) or isinstance(dimensao, bool) or dimensao <= 0:
            coletor.adicionar("dimensao_invalida", f"{caminho}.dimensao", "A dimensão deve ser um inteiro positivo.")
            continue
        if dimensao_processamento and dimensao != dimensao_processamento:
            coletor.adicionar(
                "dimensao_incompativel",
                f"{caminho}.dimensao",
                f"Esperada dimensão {dimensao_processamento}, recebida {dimensao}.",
            )
        if not isinstance(valores, list) or len(valores) != dimensao:
            tamanho = len(valores) if isinstance(valores, list) else "inválido"
            coletor.adicionar(
                "vetor_dimensao_incorreta",
                f"{caminho}.valores",
                f"O vetor deve conter {dimensao} valores; recebeu {tamanho}.",
            )
            continue
        if any(isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) for valor in valores):
            coletor.adicionar("vetor_nao_finito", f"{caminho}.valores", "O vetor contém valor não numérico ou não finito.")
            continue
        if item.get("normalizacao") != "l2":
            coletor.adicionar(
                "normalizacao_incompativel",
                f"{caminho}.normalizacao",
                "O artefato deve declarar normalização L2.",
            )
        else:
            norma = math.sqrt(sum(float(valor) ** 2 for valor in valores))
            if not math.isclose(norma, 1.0, rel_tol=1e-4, abs_tol=1e-4):
                coletor.adicionar(
                    "vetor_nao_normalizado",
                    f"{caminho}.valores",
                    f"A norma L2 declarada deveria ser 1; valor observado: {norma:.6f}.",
                )

    representacoes_paragrafo: dict[tuple[int, int], dict[str, Any]] = {}
    for posicao, item in enumerate(representacoes):
        if not isinstance(item, dict):
            continue
        caminho = f"$.representacoes[{posicao}]"
        artefato_id = item.get("artefato_id")
        if artefato_id not in artefatos_por_id:
            coletor.adicionar(
                "referencia_quebrada",
                f"{caminho}.artefato_id",
                f"Artefato inexistente: {artefato_id!r}.",
            )
        fragmentos = _lista(item.get("fragmentos"), f"{caminho}.fragmentos", coletor)
        for indice, fragmento in enumerate(fragmentos):
            trecho = _objeto(fragmento, f"{caminho}.fragmentos[{indice}]", coletor)
            if trecho.get("artefato_id") not in artefatos_por_id:
                coletor.adicionar(
                    "referencia_quebrada",
                    f"{caminho}.fragmentos[{indice}].artefato_id",
                    "O fragmento aponta para um artefato inexistente.",
                )
            _intervalo(trecho.get("original"), f"{caminho}.fragmentos[{indice}].original", len(original), coletor)
        origem = _objeto(item.get("origem"), f"{caminho}.origem", coletor)
        intervalo = _intervalo(origem.get("original"), f"{caminho}.origem.original", len(original), coletor)
        if "unidade_id" in origem and origem.get("unidade_id") not in unidades_por_id:
            coletor.adicionar(
                "referencia_quebrada",
                f"{caminho}.origem.unidade_id",
                "A representação aponta para uma unidade inexistente.",
            )
        if "periodo_foco_id" in origem and origem.get("periodo_foco_id") not in periodos_por_id:
            coletor.adicionar(
                "referencia_quebrada",
                f"{caminho}.origem.periodo_foco_id",
                "A representação aponta para um período inexistente.",
            )
        if item.get("tipo") == "paragrafo" and intervalo:
            if intervalo in representacoes_paragrafo:
                coletor.adicionar(
                    "representacao_duplicada",
                    caminho,
                    "Existe mais de uma representação de parágrafo para o mesmo intervalo.",
                )
            else:
                representacoes_paragrafo[intervalo] = item
            hash_esperado = hashlib.sha256(original[intervalo[0] : intervalo[1]].encode()).hexdigest()
            if item.get("texto_sha256") != hash_esperado:
                coletor.adicionar(
                    "hash_texto_divergente",
                    f"{caminho}.texto_sha256",
                    "O hash da representação não corresponde ao recorte original.",
                )

    paragrafos_ingeridos: list[ParagrafoIngerido] = []
    for posicao, item in enumerate(paragrafos):
        if not isinstance(item, dict):
            continue
        identificador = item.get("id")
        intervalo = intervalos_paragrafos.get(identificador)
        if not isinstance(identificador, str) or intervalo is None:
            continue
        representacao = representacoes_paragrafo.get(intervalo)
        if representacao is None:
            coletor.adicionar(
                "representacao_ausente",
                f"{caminho_segmentacao}.paragrafos[{posicao}]",
                "O parágrafo não possui representação vetorial vinculada ao seu intervalo.",
            )
            continue
        ordem = item.get("ordem")
        if not isinstance(ordem, int) or isinstance(ordem, bool) or ordem < 0:
            coletor.adicionar(
                "ordem_invalida",
                f"{caminho_segmentacao}.paragrafos[{posicao}].ordem",
                "Ordem inválida.",
            )
            continue
        rotulo = f"P{ordem + 1}"
        origem_representacao = representacao.get("origem", {})
        if origem_representacao.get("paragrafo_id") != rotulo:
            coletor.adicionar(
                "referencia_inconsistente",
                f"$.representacoes[{representacoes.index(representacao)}].origem.paragrafo_id",
                f"A representação deveria apontar para {rotulo!r}.",
            )
        paragrafos_ingeridos.append(
            ParagrafoIngerido(
                id=identificador,
                rotulo=rotulo,
                ordem=ordem,
                texto=item.get("texto", ""),
                inicio_original=intervalo[0],
                fim_original=intervalo[1],
                representacao_id=representacao.get("id", ""),
                artefato_id=representacao.get("artefato_id", ""),
            )
        )

    if not paragrafos_ingeridos:
        coletor.adicionar("sem_paragrafos", f"{caminho_segmentacao}.paragrafos", "Nenhum parágrafo utilizável foi encontrado.")

    # Impede estruturas declaradas mas vazias de serem aceitas silenciosamente.
    if not periodos_por_id:
        coletor.adicionar("sem_periodos", f"{caminho_segmentacao}.periodos", "Nenhum período foi encontrado.")
    if not tokens_por_id:
        coletor.adicionar("sem_tokens", f"{caminho_segmentacao}.tokens", "Nenhum token foi encontrado.")
    if not unidades_por_id:
        coletor.adicionar("sem_unidades", "$.contexto.unidades", "Nenhuma unidade de contexto foi encontrada.")
    if not representacoes_por_id:
        coletor.adicionar("sem_representacoes", "$.representacoes", "Nenhuma representação foi encontrada.")
    if not artefatos_por_id:
        coletor.adicionar("sem_artefatos", "$.artefatos", "Nenhum artefato vetorial foi encontrado.")

    coletor.concluir()
    paragrafos_ingeridos.sort(key=lambda item: item.ordem)
    return DocumentoIngerido(
        documento_id=documento_id,
        schema_version=schema_version,
        etapa=etapa,
        texto_original=original,
        paragrafos=tuple(paragrafos_ingeridos),
        periodos_total=len(periodos_por_id),
        tokens_total=len(tokens_por_id),
        representacoes_total=len(representacoes_por_id),
        artefatos_total=len(artefatos_por_id),
        dimensao_vetores=dimensao_processamento,
    )
