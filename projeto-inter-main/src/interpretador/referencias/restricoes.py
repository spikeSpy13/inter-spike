from __future__ import annotations

from .models import Mention


PRONOMES_EXOFORICOS = {"eu", "tu", "você", "nós", "vocês"}
POSSESSIVOS_EXOFORICOS = {"meu", "minha", "meus", "minhas"}
PAPEIS_HUMANOS = {"gerente", "engenheira", "profissional", "diretor", "auditor", "auditores", "mensageiro"}
PAPEIS_EQUIVALENTES = {frozenset({"engenheira", "profissional"})}


def _papeis(mencao: Mention) -> set[str]:
    return set(mencao.texto.casefold().split()) & PAPEIS_HUMANOS


def verificar_compatibilidade(atual: Mention, candidato: Mention) -> tuple[bool, list[str]]:
    """Aplica apenas restrições fortes; sinais graduais ficam na pontuação."""
    if atual.id == candidato.id:
        return False, ["uma menção não pode apontar para si própria"]

    if atual.tipo == "pronome_pessoal" and atual.texto.casefold() in PRONOMES_EXOFORICOS:
        return False, ["pronome ligado à situação de fala, sem antecedente textual automático"]
    if atual.tipo == "pronome_possessivo" and atual.texto.casefold() in POSSESSIVOS_EXOFORICOS:
        return False, ["possessivo de primeira pessoa depende da fonte da fala"]

    if atual.origem == candidato.origem:
        contem_atual = (
            candidato.intervalo.inicio <= atual.intervalo.inicio
            and candidato.intervalo.fim >= atual.intervalo.fim
        )
        if contem_atual:
            eh_nucleo_de_descricao_complexa = (
                atual.texto.casefold() == "alguém"
                and candidato.tipo == "descricao_complexa"
            )
            if not eh_nucleo_de_descricao_complexa:
                return False, ["o candidato contém a própria menção"]

    classe_atual = atual.caracteristicas.classe_semantica
    classe_candidato = candidato.caracteristicas.classe_semantica
    if atual.tipo == "pronome_possessivo" and classe_candidato != "pessoa":
        return False, ["um possessivo deve apontar para o possuidor"]
    if (
        classe_atual != "desconhecida"
        and classe_candidato != "desconhecida"
        and classe_atual != classe_candidato
    ):
        return False, ["classes semânticas incompatíveis"]
    if classe_atual == "pessoa" and classe_candidato == "desconhecida":
        return False, ["candidato sem evidência de que represente uma pessoa"]

    if classe_atual == "pessoa" or atual.tipo in {"pronome_pessoal", "pronome_possessivo"}:
        genero_atual = atual.caracteristicas.genero
        genero_candidato = candidato.caracteristicas.genero
        if (
            genero_atual != "indeterminado"
            and genero_candidato != "indeterminado"
            and genero_atual != genero_candidato
        ):
            return False, ["gêneros incompatíveis"]

        numero_atual = atual.caracteristicas.numero
        numero_candidato = candidato.caracteristicas.numero
        if (
            numero_atual != "indeterminado"
            and numero_candidato != "indeterminado"
            and numero_atual != numero_candidato
        ):
            return False, ["números incompatíveis"]

    papeis_atual = _papeis(atual)
    papeis_candidato = _papeis(candidato)
    if papeis_atual and papeis_candidato and papeis_atual != papeis_candidato:
        par = frozenset({next(iter(papeis_atual)), next(iter(papeis_candidato))})
        if par not in PAPEIS_EQUIVALENTES:
            return False, ["papéis humanos lexicalmente distintos"]

    return True, []
