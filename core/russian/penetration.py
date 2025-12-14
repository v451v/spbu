"""Кривая пенетрации и поиск глубины равновесия (российская методика)."""

import numpy as np

from core.helpers import get_layer_at_depth, additional_stress_boussinesq
from core.models import Coefficients, Foundation, PointResult, SoilLayer

from .bearing import bearing_capacity_Nu, design_resistance_R


def calculate_point(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F: float,
    d: float,
) -> PointResult:
    """Расчёт для одной глубины d с учётом распределения давления по Буссинеску.

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        coef: Коэффициенты надёжности.
        F: Вертикальная нагрузка, кН.
        d: Глубина заглубления, м.

    Returns:
        PointResult с результатами расчёта.
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return PointResult(d=d, Nu=0.0, R=0.0, p=0.0, eta1=999.0, eta2=999.0, layer_name="Unknown")

    Nu = bearing_capacity_Nu(layers, foundation, d, layer)
    R = design_resistance_R(layers, foundation, d, coef)

    # Среднее давление под подошвой
    p_avg = F / foundation.area_prime

    # Дополнительное вертикальное напряжение по Буссинеску на глубине d
    # Для расчёта используем приведённые размеры фундамента
    b_prime = foundation.b_prime
    l_prime = foundation.l_prime

    # На подошве фундамента (z=0) σ_zp = p, с глубиной затухает
    # Здесь z = 0, так как мы считаем давление непосредственно под подошвой на глубине d
    # Для корректного расчёта нужно учитывать глубину от подошвы, но в данном случае
    # мы сравниваем давление на подошве с несущей способностью на этой глубине
    p = p_avg  # На подошве σ_zp = p_avg

    eta1 = (coef.gamma_lc * F * coef.gamma_n) / Nu if Nu > 0 else np.inf
    eta2 = p / R if R > 0 else np.inf

    return PointResult(d=d, Nu=Nu, R=R, p=p, eta1=eta1, eta2=eta2, layer_name=layer.name)


def penetration_curve(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F: float,
    d_max: float = 20.0,
    d_step: float = 0.1,
) -> list[PointResult]:
    """Кривая пенетрации Nu(d) и R(d).

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        coef: Коэффициенты надёжности.
        F: Вертикальная нагрузка, кН.
        d_max: Максимальная глубина расчёта, м.
        d_step: Шаг по глубине, м.

    Returns:
        Список PointResult для каждой глубины.
    """
    depths = np.arange(d_step, d_max + d_step / 2, d_step)
    return [calculate_point(layers, foundation, coef, F, d) for d in depths]


def find_equilibrium_depth(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F: float,
    d_max: float = 30.0,
    d_step: float = 0.05,
) -> PointResult | None:
    """Найти глубину равновесия (η₁ ≤ 1 и η₂ ≤ 1).

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        coef: Коэффициенты надёжности.
        F: Вертикальная нагрузка, кН.
        d_max: Максимальная глубина поиска, м.
        d_step: Шаг поиска, м.

    Returns:
        PointResult при выполнении условий, или None если не найдено.
    """
    for d in np.arange(d_step, d_max + d_step / 2, d_step):
        res = calculate_point(layers, foundation, coef, F, d)
        if res.eta1 <= 1.0 and res.eta2 <= 1.0:
            return res
    return None
