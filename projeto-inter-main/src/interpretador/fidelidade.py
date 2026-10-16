"""Checagem explicável de cobertura e rastreabilidade das saídas geradas."""

from __future__ import annotations

from .geracao import validar_parafrase
from .grafo.models import PropositionRelation, ScopeOperator
from .models import (
    Evidence,
    FidelityCheck,
    FidelityFinding,
    Paraphrase,
    Proposition,
    Synthesis,
)


LIMITACAO = (
    "A checagem verifica rastreabilidade estrutural e transformações conhecidas; "
    "não certifica equivalência semântica geral."
)


def _ids_unicos(valores: list[str]) -> list[str]:
    return list(dict.fromkeys(valores))


def _abrange(evidencias: list[Evidence], inicio: int, fim: int) -> bool:
    return any(
        item.intervalo.inicio <= inicio and fim <= item.intervalo.fim
        for item in evidencias
    )


def _adicionar(
    achados: list[FidelityFinding],
    codigo: str,
    alvo_id: str,
    mensagem: str,
    ids_afetados: list[str] | None = None,
    evidencias: list[Evidence] | None = None,
) -> None:
    ids = ids_afetados or []
    chave = (codigo, alvo_id, tuple(ids))
    if any(
        (item.codigo, item.alvo_id, tuple(item.ids_afetados)) == chave
        for item in achados
    ):
        return
    achados.append(FidelityFinding(
        codigo=codigo,
        alvo_id=alvo_id,
        mensagem=mensagem,
        ids_afetados=ids,
        evidencias=evidencias or [],
    ))


def _comparar_ids(
    achados: list[FidelityFinding],
    alvo_id: str,
    esperados: list[str],
    declarados: list[str],
    codigo_ausencia: str,
    rotulo: str,
) -> None:
    faltantes = [item for item in esperados if item not in declarados]
    excedentes = [item for item in declarados if item not in esperados]
    if faltantes:
        _adicionar(
            achados,
            codigo_ausencia,
            alvo_id,
            f"A saída não declara {rotulo}: {', '.join(faltantes)}.",
            faltantes,
        )
    if excedentes:
        _adicionar(
            achados,
            "afirmacao_sem_apoio",
            alvo_id,
            f"A saída declara {rotulo} sem apoio: {', '.join(excedentes)}.",
            excedentes,
        )


def _classificar_erro_parafrase(mensagem: str) -> tuple[str, str]:
    texto = mensagem.casefold()
    if "além das transformações" in texto:
        return "afirmacao_sem_apoio", "A paráfrase contém texto sem transformação declarada."
    if "não autorizada" in texto or "transformação" in texto or "substituir" in texto:
        return "transformacao_nao_autorizada", mensagem
    if "evidência" in texto or "evidências" in texto:
        return "evidencia_invalida", mensagem
    return "saida_nao_reconstruivel", mensagem


def checar_fidelidade(
    texto: str,
    proposicoes: list[Proposition],
    conteudo_essencial_ids: list[str],
    operadores: list[ScopeOperator],
    relacoes: list[PropositionRelation],
    sintese: Synthesis,
    parafrases: list[Paraphrase],
) -> FidelityCheck:
    """Compara cada saída com o registro interpretativo e o texto original."""

    alvos = ["sintese", *[item.id for item in parafrases]]
    achados: list[FidelityFinding] = []
    if sintese.estado == "indeterminada":
        if conteudo_essencial_ids:
            _adicionar(
                achados,
                "conteudo_essencial_ausente",
                "sintese",
                "Há conteúdo essencial, mas nenhuma síntese foi gerada.",
                conteudo_essencial_ids,
            )
        estado = "revisao_necessaria" if achados else "indeterminada"
        return FidelityCheck(
            estado=estado,
            alvos_verificados=alvos,
            achados=achados,
            limitacoes=[LIMITACAO],
        )

    proposicoes_por_id = {item.id: item for item in proposicoes}
    essenciais = [
        proposicoes_por_id[item]
        for item in conteudo_essencial_ids
        if item in proposicoes_por_id
    ]
    ids_essenciais = set(conteudo_essencial_ids)
    operadores_esperados = [
        item for item in operadores if ids_essenciais.intersection(item.escopo)
    ]
    relacoes_esperadas = [
        item
        for item in relacoes
        if item.origem_id in ids_essenciais or item.destino_id in ids_essenciais
    ]
    mencoes_esperadas = _ids_unicos([
        participante.mencao_id
        for proposicao in essenciais
        for participante in proposicao.participantes
    ])
    cobertura_esperada = {
        "proposicao_ids": conteudo_essencial_ids,
        "operador_ids": [item.id for item in operadores_esperados],
        "relacao_ids": [item.id for item in relacoes_esperadas],
        "mencao_ids": mencoes_esperadas,
    }

    for evidencia in sintese.evidencias:
        intervalo = evidencia.intervalo
        if texto[intervalo.inicio:intervalo.fim] != evidencia.texto:
            _adicionar(
                achados,
                "evidencia_invalida",
                "sintese",
                "Uma evidência da síntese diverge do texto original.",
                evidencias=[evidencia],
            )
    texto_rastreavel = " ".join(item.texto for item in sintese.evidencias)
    if sintese.texto != texto_rastreavel:
        if sintese.texto and sintese.texto in texto_rastreavel:
            _adicionar(
                achados,
                "conteudo_essencial_ausente",
                "sintese",
                "A síntese omite parte do texto sustentado pelas evidências.",
                conteudo_essencial_ids,
            )
        else:
            _adicionar(
                achados,
                "afirmacao_sem_apoio",
                "sintese",
                "A síntese contém texto que não pode ser reconstruído pelas evidências.",
            )

    _comparar_ids(
        achados,
        "sintese",
        cobertura_esperada["proposicao_ids"],
        sintese.cobertura.proposicao_ids,
        "conteudo_essencial_ausente",
        "proposições essenciais",
    )
    _comparar_ids(
        achados,
        "sintese",
        cobertura_esperada["operador_ids"],
        sintese.cobertura.operador_ids,
        "operador_essencial_ausente",
        "operadores essenciais",
    )
    _comparar_ids(
        achados,
        "sintese",
        cobertura_esperada["relacao_ids"],
        sintese.cobertura.relacao_ids,
        "relacao_essencial_ausente",
        "relações essenciais",
    )
    _comparar_ids(
        achados,
        "sintese",
        cobertura_esperada["mencao_ids"],
        sintese.cobertura.mencao_ids,
        "participante_essencial_ausente",
        "participantes essenciais",
    )

    for proposicao in essenciais:
        intervalo = proposicao.evidencia.intervalo
        if not _abrange(sintese.evidencias, intervalo.inicio, intervalo.fim):
            _adicionar(
                achados,
                "conteudo_essencial_ausente",
                "sintese",
                f"As evidências não cobrem a proposição essencial {proposicao.id}.",
                [proposicao.id],
                [proposicao.evidencia],
            )
        for participante in proposicao.participantes:
            intervalo_participante = participante.intervalo
            if not _abrange(
                sintese.evidencias,
                intervalo_participante.inicio,
                intervalo_participante.fim,
            ):
                _adicionar(
                    achados,
                    "participante_essencial_ausente",
                    "sintese",
                    f"As evidências não cobrem o participante {participante.mencao_id}.",
                    [participante.mencao_id],
                )
    for item, codigo, rotulo in [
        *[(item, "operador_essencial_ausente", "operador") for item in operadores_esperados],
        *[(item, "relacao_essencial_ausente", "relação") for item in relacoes_esperadas],
    ]:
        intervalo = item.evidencia.intervalo
        if not _abrange(sintese.evidencias, intervalo.inicio, intervalo.fim):
            _adicionar(
                achados,
                codigo,
                "sintese",
                f"As evidências não cobrem o {rotulo} essencial {item.id}.",
                [item.id],
            )

    sintese_tem_achados = any(item.alvo_id == "sintese" for item in achados)
    for parafrase in parafrases:
        inicio_achados = len(achados)
        _comparar_ids(
            achados,
            parafrase.id,
            cobertura_esperada["proposicao_ids"],
            parafrase.cobertura.proposicao_ids,
            "conteudo_essencial_ausente",
            "proposições essenciais",
        )
        _comparar_ids(
            achados,
            parafrase.id,
            cobertura_esperada["operador_ids"],
            parafrase.cobertura.operador_ids,
            "operador_essencial_ausente",
            "operadores essenciais",
        )
        _comparar_ids(
            achados,
            parafrase.id,
            cobertura_esperada["relacao_ids"],
            parafrase.cobertura.relacao_ids,
            "relacao_essencial_ausente",
            "relações essenciais",
        )
        _comparar_ids(
            achados,
            parafrase.id,
            cobertura_esperada["mencao_ids"],
            parafrase.cobertura.mencao_ids,
            "participante_essencial_ausente",
            "participantes essenciais",
        )
        if parafrase.proposicao_ids != conteudo_essencial_ids:
            _adicionar(
                achados,
                "conteudo_essencial_ausente",
                parafrase.id,
                "A paráfrase não declara todas as proposições essenciais.",
                [item for item in conteudo_essencial_ids if item not in parafrase.proposicao_ids],
            )
        for evidencia in parafrase.evidencias:
            intervalo = evidencia.intervalo
            if texto[intervalo.inicio:intervalo.fim] != evidencia.texto:
                _adicionar(
                    achados,
                    "evidencia_invalida",
                    parafrase.id,
                    "Uma evidência da paráfrase diverge do texto original.",
                    evidencias=[evidencia],
                )
        if len(achados) == inicio_achados and not sintese_tem_achados:
            try:
                validar_parafrase(
                    texto,
                    proposicoes,
                    operadores,
                    relacoes,
                    sintese,
                    parafrase,
                )
            except (ValueError, KeyError, IndexError) as erro:
                codigo, mensagem = _classificar_erro_parafrase(str(erro))
                _adicionar(achados, codigo, parafrase.id, mensagem)

    return FidelityCheck(
        estado="revisao_necessaria" if achados else "sem_alertas_detectados",
        alvos_verificados=alvos,
        achados=achados,
        limitacoes=[LIMITACAO],
    )
