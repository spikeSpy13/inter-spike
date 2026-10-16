from __future__ import annotations

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


def resolver_referencias(mencoes: list[Mention]) -> ResolutionResult:
    referentes: list[Referent] = []
    resolucoes: list[ReferenceResolution] = []
    referente_por_mencao: dict[str, str] = {}
    confiancas: dict[str, list[float]] = {}

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

    anteriores: list[Mention] = []
    por_id = {mencao.id: mencao for mencao in mencoes}
    for mencao in mencoes:
        buscar = _deve_buscar_antecedente(mencao, anteriores)
        hipoteses_por_referente: dict[str, ReferenceCandidate] = {}
        if buscar:
            for candidato, distancia in gerar_candidatos(mencao, anteriores):
                referente_id = referente_por_mencao.get(candidato.id)
                if not referente_id:
                    continue
                if set(mencao.texto.casefold().split()) & PAPEIS_HUMANOS:
                    referente_atual = next(item for item in referentes if item.id == referente_id)
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
                razoes=["há mais de um referente com pontuação semelhante"],
                alternativas=hipoteses[:3],
                evidencias=[_evidencia(mencao)],
            ))
        elif mencao.tipo in {"pronome_pessoal", "pronome_possessivo"}:
            resolucoes.append(ReferenceResolution(
                mencao_id=mencao.id,
                estado="nao_resolvida",
                tipo_relacao="possuidor" if mencao.tipo == "pronome_possessivo" else "identidade",
                confianca=melhor.pontuacao if melhor else 0.0,
                razoes=["nenhum antecedente atingiu o limiar de decisão"],
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
