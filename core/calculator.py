"""Калькулятор основания СПБУ."""

from typing import Literal

from core import russian, western
from core.models import CalculationResult, Coefficients, Foundation, SoilLayer


def calculate(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F_operation: float,
    F_preload: float,
    d_max: float = 20.0,
    d_step: float = 0.2,
    method: str = "russian",
    stress_distribution: Literal["alpha", "boussinesq"] = "alpha",
) -> CalculationResult:
    """Основной пайплайн расчёта.

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        coef: Коэффициенты надёжности.
        F_operation: Эксплуатационная нагрузка, кН.
        F_preload: Преднагрузка, кН.
        d_max: Максимальная глубина расчёта, м.
        d_step: Шаг по глубине, м.
        method: Методика расчёта ("russian" или "western").
        stress_distribution: Распределение напряжений для осадки/Нс (только russian).

    Returns:
        CalculationResult с кривыми и глубинами равновесия.
    """
    punch_through_risk = False
    
    if method == "russian":
        # Российская методика (СП 22/23/58)
        curve = russian.penetration_curve(layers, foundation, coef, F_operation, d_max, d_step)
        eq_operation = russian.find_equilibrium_depth(layers, foundation, coef, F_operation, d_max)
        eq_preload = russian.find_equilibrium_depth(layers, foundation, coef, F_preload, d_max)

        # Осадки s(d) — только для российской методики
        p = F_operation / foundation.area_prime
        depths = [r.d for r in curve]
        settlements = [
            russian.settlement(
                layers,
                foundation,
                d,
                p,
                stress_distribution=stress_distribution,
            )
            * 1000
            for d in depths
        ]
    else:
        # Западная методика (SNAME/ISO)
        curve = western.penetration_curve(layers, foundation, coef, F_operation, d_max, d_step)
        eq_operation = western.find_equilibrium_depth(layers, foundation, coef, F_operation, d_max)
        eq_preload = western.find_equilibrium_depth(layers, foundation, coef, F_preload, d_max)

        # Осадки не рассчитываются в западной методике
        depths = [r.d for r in curve]
        settlements = [0.0] * len(depths)
        
        # Проверка риска punch-through
        punch_through_risk = western.has_punch_through_risk(
            layers, foundation, coef, F_operation, d_max, d_step
        )

    return CalculationResult(
        curve=curve,
        d_operation=eq_operation.d if eq_operation else None,
        d_preload=eq_preload.d if eq_preload else None,
        eq_operation=eq_operation,
        eq_preload=eq_preload,
        depths=depths,
        settlements=settlements,
        punch_through_risk=punch_through_risk,
    )
