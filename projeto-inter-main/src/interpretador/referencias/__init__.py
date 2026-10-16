"""Detecção e resolução progressiva de referências textuais."""

from .detector import detectar_mencoes
from .resolvedor import resolver_referencias

__all__ = ["detectar_mencoes", "resolver_referencias"]

