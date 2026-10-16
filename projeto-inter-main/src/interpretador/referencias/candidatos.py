from __future__ import annotations

from .models import Mention
from .restricoes import verificar_compatibilidade


def gerar_candidatos(mencao: Mention, anteriores: list[Mention]) -> list[tuple[Mention, int]]:
    """Retorna antecedentes textualmente anteriores e sua distância discursiva."""
    candidatos: list[tuple[Mention, int]] = []
    for distancia, candidato in enumerate(reversed(anteriores), start=1):
        compativel, _ = verificar_compatibilidade(mencao, candidato)
        if compativel:
            candidatos.append((candidato, distancia))
    return candidatos
