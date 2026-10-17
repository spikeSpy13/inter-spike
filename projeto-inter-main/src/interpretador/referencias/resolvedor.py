from __future__ import annotations

import re
from dataclasses import dataclass

from .candidatos import gerar_candidatos
from .models import (
    Mention,
    Referent,
    ReferenceCandidate,
    ReferenceEvidence,
    ReferenceResolution,
)
from .pontuacao import pontuar_candidato
from .restricoes import PAPEIS_HUMANOS, verificar_compatibilidade
from .validator import validar_referencias


PALAVRAS_FUNCIONAIS = {"o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das", "que"}
PRIMEIRA_PESSOA = {"eu", "nós", "meu", "minha", "meus", "minhas"}
SEGUNDA_PESSOA = {"tu", "você", "vocês"}
_CITACOES = re.compile(r'"[^"]*"|“[^”]*”', re.DOTALL)


def _palavras_de_conteudo(texto: str) -> set[str]:
    return set(texto.casefold().split()) - PALAVRAS_FUNCIONAIS


@dataclass(frozen=True)
class ResolutionResult:
    referentes: list[Referent]
    resolucoes: list[ReferenceResolution]
    referente_por_mencao: dict[str, str]


def _evidencia(mencao: Mention) -> ReferenceEvidence:
    return ReferenceEvidence(
        mencao_id=mencao.id,
        texto=mencao.texto,
        origem=mencao.origem,
        intervalo=mencao.intervalo,
    )


def _deve_buscar_antecedente(mencao: Mention, anteriores: list[Mention]) -> bool:
    if not anteriores:
        return False
    if mencao.tipo in {"pronome_pessoal", "pronome_possessivo"}:
        return True
    if mencao.tipo == "nome_proprio":
        return any(item.texto.casefold() == mencao.texto.casefold() for item in anteriores)
    if mencao.caracteristicas.classe_semantica == "pessoa":
        return True
    palavras = _palavras_de_conteudo(mencao.texto)
    return any(palavras & _palavras_de_conteudo(item.texto) for item in anteriores)


def _rotulo_preferido(atual: str, candidata: Mention, referente: Referent, por_id: dict[str, Mention]) -> str:
    nomes = [por_id[item].texto for item in referente.mencoes if por_id[item].tipo == "nome_proprio"]
    if nomes and candidata.tipo != "nome_proprio":
        return nomes[0]
    if candidata.tipo == "nome_proprio":
        return candidata.texto
    if len(candidata.texto) > len(atual) and candidata.tipo != "pronome_possessivo":
        return candidata.texto
    return atual


def _esta_em_citacao(mencao: Mention, textos: dict[str, str]) -> bool:
    texto = textos.get(mencao.origem)
    if not texto:
        return False
    return any(
        citacao.start() < mencao.intervalo.inicio < citacao.end()
        for citacao in _CITACOES.finditer(texto)
    )


def resolver_referencias(
    mencoes: list[Mention],
    texto: str | None = None,
    contexto_anterior: str | None = None,
) -> ResolutionResult:
    referentes: list[Referent] = []
    resolucoes: list[ReferenceResolution] = []
    referente_por_mencao: dict[str, str] = {}
    confiancas: dict[str, list[float]] = {}
    textos = {"paragrafo": texto or "", "contexto_anterior": contexto_anterior or ""}
    participante_discursivo: dict[str, str] = {}

    def novo_referente(mencao: Mention) -> str:
        referente_id = f"R{len(referentes) + 1}"
        referentes.append(Referent(
            id=referente_id,
            rotulo=mencao.texto,
            classe_semantica=mencao.caracteristicas.classe_semantica,
            mencoes=[mencao.id],
            confianca=mencao.confianca_deteccao,
        ))
        referente_por_mencao[mencao.id] = referente_id
        confiancas[referente_id] = [mencao.confianca_deteccao]
        return referente_id

    def ligar_ao_participante_discursivo(mencao: Mention, papel: str = "narrador") -> str:
        referente_id = participante_discursivo.get(papel)
        if referente_id is None:
            referente_id = f"R{len(referentes) + 1}"
            referentes.append(Referent(
                id=referente_id,
                rotulo=papel,
                classe_semantica="pessoa",
                tipo="participante_discursivo",
                mencoes=[],
                confianca=0.96,
            ))
            participante_discursivo[papel] = referente_id
            confiancas[referente_id] = []
        referente = next(item for item in referentes if item.id == referente_id)
        referente.mencoes.append(mencao.id)
        referente_por_mencao[mencao.id] = referente_id
        confiancas[referente_id].append(0.96)
        referente.confianca = round(sum(confiancas[referente_id]) / len(confiancas[referente_id]), 2)
        return referente_id

    anteriores: list[Mention] = []
    por_id = {mencao.id: mencao for mencao in mencoes}
    for mencao in mencoes:
        forma = mencao.texto.casefold()
        em_citacao = _esta_em_citacao(mencao, textos)
        if forma in PRIMEIRA_PESSOA and not em_citacao:
            referente_id = ligar_ao_participante_discursivo(mencao)
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                referente_id=referente_id,
                estado="resolvida",
                tipo_relacao="possuidor" if mencao.tipo == "pronome_possessivo" else "identidade",
                confianca=0.96,
                razoes=[
                    "primeira pessoa vinculada ao papel discursivo de narrador",
                    "a identidade externa do narrador não foi inferida",
                ],
                evidencias=[_evidencia(mencao)],
            ))
            anteriores.append(mencao)
            continue

        if forma in PRIMEIRA_PESSOA and em_citacao:
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                estado="nao_resolvida",
                tipo_relacao="possuidor" if mencao.tipo == "pronome_possessivo" else "identidade",
                confianca=0.0,
                motivo_pendencia="fonte_fala_desconhecida",
                razoes=["primeira pessoa em fala citada depende da identificação textual do falante"],
                evidencias=[_evidencia(mencao)],
            ))
            anteriores.append(mencao)
            continue

        if forma in SEGUNDA_PESSOA:
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                estado="nao_resolvida",
                tipo_relacao="identidade",
                confianca=0.0,
                motivo_pendencia="exoforia",
                razoes=["pronome de segunda pessoa depende da situação de fala e não possui antecedente textual seguro"],
                evidencias=[_evidencia(mencao)],
            ))
            anteriores.append(mencao)
            continue

        buscar = _deve_buscar_antecedente(mencao, anteriores)
        hipoteses_por_referente: dict[str, ReferenceCandidate] = {}
        candidatos_compativeis = gerar_candidatos(mencao, anteriores) if buscar else []
        if buscar:
            for candidato, distancia in candidatos_compativeis:
                referente_id = referente_por_mencao.get(candidato.id)
                if not referente_id:
                    continue
                referente_atual = next(item for item in referentes if item.id == referente_id)
                if (
                    mencao.tipo in {"pronome_pessoal", "pronome_possessivo"}
                    and referente_atual.tipo == "participante_discursivo"
                ):
                    continue
                if set(mencao.texto.casefold().split()) & PAPEIS_HUMANOS:
                    membros_com_papel = [
                        por_id[item] for item in referente_atual.mencoes
                        if set(por_id[item].texto.casefold().split()) & PAPEIS_HUMANOS
                    ]
                    if any(not verificar_compatibilidade(mencao, membro)[0] for membro in membros_com_papel):
                        continue
                pontuacao, razoes = pontuar_candidato(mencao, candidato, distancia)
                hipotese = ReferenceCandidate(
                    antecedente_mencao_id=candidato.id,
                    referente_id=referente_id,
                    pontuacao=pontuacao,
                    razoes=razoes,
                )
                existente = hipoteses_por_referente.get(referente_id)
                if existente is None or hipotese.pontuacao > existente.pontuacao:
                    hipoteses_por_referente[referente_id] = hipotese

        hipoteses = sorted(
            hipoteses_por_referente.values(),
            key=lambda item: item.pontuacao,
            reverse=True,
        )
        if len(hipoteses) == 1 and mencao.tipo == "pronome_pessoal":
            unica = hipoteses[0]
            antecedente = por_id[unica.antecedente_mencao_id]
            if (
                antecedente.tipo in {"nome_proprio", "descricao_nominal", "descricao_complexa"}
                and antecedente.caracteristicas.classe_semantica == "pessoa"
            ):
                hipoteses[0] = unica.model_copy(update={
                    "pontuacao": round(min(unica.pontuacao + 0.08, 0.98), 2),
                    "razoes": [*unica.razoes, "único referente humano compatível"],
                })
        limiar = 0.50 if mencao.tipo == "pronome_possessivo" else 0.68 if mencao.tipo == "pronome_pessoal" else 0.72
        melhor = hipoteses[0] if hipoteses else None
        margem = melhor.pontuacao - hipoteses[1].pontuacao if melhor and len(hipoteses) > 1 else 1.0

        margem_minima = 0.05 if mencao.tipo == "pronome_possessivo" else 0.07
        if melhor and melhor.pontuacao >= limiar and margem >= margem_minima:
            referente_id = melhor.referente_id
            referente = next(item for item in referentes if item.id == referente_id)
            referente.mencoes.append(mencao.id)
            referente.rotulo = _rotulo_preferido(referente.rotulo, mencao, referente, por_id)
            referente_por_mencao[mencao.id] = referente_id
            confiancas[referente_id].append(melhor.pontuacao)
            referente.confianca = round(sum(confiancas[referente_id]) / len(confiancas[referente_id]), 2)
            antecedente = por_id[melhor.antecedente_mencao_id]
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                referente_id=referente_id,
                estado="resolvida",
                tipo_relacao="possuidor" if mencao.tipo == "pronome_possessivo" else "identidade",
                confianca=melhor.pontuacao,
                antecedente_mencao_id=melhor.antecedente_mencao_id,
                razoes=melhor.razoes,
                alternativas=hipoteses[1:4],
                evidencias=[_evidencia(antecedente), _evidencia(mencao)],
            ))
        elif melhor and melhor.pontuacao >= limiar:
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                estado="ambigua",
                tipo_relacao="possuidor" if mencao.tipo == "pronome_possessivo" else "identidade",
                confianca=melhor.pontuacao,
                motivo_pendencia="ambiguidade",
                razoes=["há mais de um referente com pontuação semelhante"],
                alternativas=hipoteses[:3],
                evidencias=[_evidencia(mencao)],
            ))
        elif mencao.tipo in {"pronome_pessoal", "pronome_possessivo"}:
            if melhor:
                motivo = "evidencia_insuficiente"
                razoes = [
                    f"melhor candidato obteve {melhor.pontuacao:.2f}, abaixo do limiar {limiar:.2f}",
                    "a ligação foi mantida pendente para evitar uma associação fraca",
                ]
            elif anteriores and not candidatos_compativeis:
                motivo = "candidatos_incompativeis"
                restricoes = {
                    razao
                    for anterior in anteriores
                    for razao in verificar_compatibilidade(mencao, anterior)[1]
                }
                razoes = [
                    "as menções anteriores não satisfazem as restrições referenciais",
                    *sorted(restricoes)[:3],
                ]
            else:
                motivo = "ausencia_antecedente"
                razoes = ["não há antecedente textual anterior com um referente utilizável"]
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                estado="nao_resolvida",
                tipo_relacao="possuidor" if mencao.tipo == "pronome_possessivo" else "identidade",
                confianca=melhor.pontuacao if melhor else 0.0,
                motivo_pendencia=motivo,
                razoes=razoes,
                alternativas=hipoteses[:3],
                evidencias=[_evidencia(mencao)],
            ))
        else:
            referente_id = novo_referente(mencao)
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                referente_id=referente_id,
                estado="novo_referente",
                tipo_relacao="introducao",
                confianca=mencao.confianca_deteccao,
                razoes=["menção nominal introduz um referente distinto"],
                alternativas=hipoteses[:3],
                evidencias=[_evidencia(mencao)],
            ))
        anteriores.append(mencao)

    validar_referencias(mencoes, referentes, resolucoes)
    return ResolutionResult(referentes, resolucoes, referente_por_mencao)
