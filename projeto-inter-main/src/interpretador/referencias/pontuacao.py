from __future__ import annotations

import re
import unicodedata

from .models import Mention


PALAVRAS_FUNCIONAIS = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da",
    "dos", "das", "que", "seu", "sua", "seus", "suas", "dele", "dela",
}


def _normalizar(texto: str) -> str:
    sem_acentos = "".join(
        caractere for caractere in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(re.findall(r"[^\W\d_]+", sem_acentos, re.UNICODE))


def _conteudo(texto: str) -> set[str]:
    return {palavra for palavra in _normalizar(texto).split() if palavra not in PALAVRAS_FUNCIONAIS}


def pontuar_candidato(atual: Mention, candidato: Mention, distancia: int) -> tuple[float, list[str]]:
    pontos = 0.0
    razoes: list[str] = []
    classe_atual = atual.caracteristicas.classe_semantica
    classe_candidato = candidato.caracteristicas.classe_semantica

    if classe_atual == classe_candidato and classe_atual != "desconhecida":
        pontos += 0.24
        razoes.append(f"mesma classe semântica: {classe_atual}")
    elif atual.tipo == "pronome_possessivo" and classe_candidato == "pessoa":
        pontos += 0.24
        razoes.append("candidato humano para o papel de possuidor")

    if (
        atual.caracteristicas.genero != "indeterminado"
        and atual.caracteristicas.genero == candidato.caracteristicas.genero
    ):
        pontos += 0.18
        razoes.append("gênero compatível")
    if (
        atual.caracteristicas.numero != "indeterminado"
        and atual.caracteristicas.numero == candidato.caracteristicas.numero
    ):
        pontos += 0.12
        razoes.append("número compatível")

    bonus_distancia = 0.22 if distancia == 1 else 0.16 if distancia <= 3 else 0.10 if distancia <= 6 else 0.05
    pontos += bonus_distancia
    razoes.append("antecedente recente" if distancia <= 3 else "antecedente disponível no contexto")

    bonus_tipo = {
        "nome_proprio": 0.12,
        "descricao_nominal": 0.06,
        "descricao_complexa": 0.06,
        "pronome_pessoal": 0.02,
        "pronome_possessivo": 0.01,
    }[candidato.tipo]
    pontos += bonus_tipo
    if candidato.tipo == "nome_proprio":
        razoes.append("nome próprio saliente")

    pontos += 0.05 if atual.origem == candidato.origem else 0.02
    razoes.append("mesma unidade textual" if atual.origem == candidato.origem else "continuidade com o contexto anterior")

    normal_atual = _normalizar(atual.texto)
    normal_candidato = _normalizar(candidato.texto)
    conteudo_comum = _conteudo(atual.texto) & _conteudo(candidato.texto)
    if normal_atual == normal_candidato:
        pontos += 0.30
        razoes.append("mesma realização lexical")
    elif conteudo_comum:
        pontos += 0.18
        razoes.append("núcleo lexical compartilhado")

    if classe_atual == "pessoa" and classe_candidato == "pessoa":
        if atual.tipo in {"descricao_nominal", "descricao_complexa"}:
            pontos += 0.10
            razoes.append("descrição humana compatível")
        if atual.tipo == "descricao_complexa":
            pontos += 0.10
            razoes.append("continuidade discursiva de descrição complexa")
            if candidato.tipo == "pronome_pessoal":
                pontos += 0.18
                razoes.append("retomada do participante humano em foco")

    return round(min(pontos, 0.98), 2), razoes
