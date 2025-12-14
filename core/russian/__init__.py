"""Российская методика расчёта основания СПБУ (СП 22/23/58).

Модуль реализует расчёт по двум группам предельных состояний:
- I группа ПС: несущая способность Nu (C.1.1)
- II группа ПС: расчётное сопротивление R (C.1.3), осадка (C.1.4)

Использование:
    from core.russian import (
        bearing_capacity_Nu,
        design_resistance_R,
        settlement,
        penetration_curve,
        find_equilibrium_depth,
    )
"""

from .bearing import bearing_capacity_Nu, design_resistance_R
from .penetration import (
    calculate_point,
    find_equilibrium_depth,
    penetration_curve,
)
from .settlement import (
    compressible_depth,
    min_compressible_depth,
    settlement,
)

__all__ = [
    # Несущая способность
    "bearing_capacity_Nu",
    "design_resistance_R",
    # Осадка
    "min_compressible_depth",
    "compressible_depth",
    "settlement",
    # Пенетрация
    "calculate_point",
    "penetration_curve",
    "find_equilibrium_depth",
]
