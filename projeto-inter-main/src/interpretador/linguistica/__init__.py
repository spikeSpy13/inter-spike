"""Base linguística local e adaptador das hipóteses recebidas no JSON."""

from .base import (
    BaseLinguistica,
    DiagnosticoLinguistico,
    ErroAnotacao,
    PeriodoLinguistico,
    TokenLinguistico,
    adaptar_anotacoes,
    analisar_texto,
)
from .lexico import VERBOS, lematizar_palavra, pos_local

__all__ = [
    "BaseLinguistica", "DiagnosticoLinguistico", "ErroAnotacao",
    "PeriodoLinguistico", "TokenLinguistico", "adaptar_anotacoes", "analisar_texto",
    "VERBOS", "lematizar_palavra", "pos_local",
]
