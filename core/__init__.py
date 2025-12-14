"""Ядро расчёта основания СПБУ.

Модули:
- models: Типы данных (SoilLayer, Foundation, Coefficients, ...)
- calculator: Организатор алгоритма расчёта
- russian: Российская методика (СП 22/23/58)
- western: Западная методика (SNAME/ISO 19905-1)
- helpers: Общие вспомогательные функции

Использование:
    from core import russian, western
    from core.models import SoilLayer, Foundation, Coefficients
    from core.calculator import Calculator
"""

from . import helpers, russian, western
from .models import Coefficients, Foundation, PointResult, SoilLayer

__all__ = ["russian", "western", "helpers", "SoilLayer", "Foundation", "Coefficients", "PointResult"]
