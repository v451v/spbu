"""Кривая пенетрации и поиск глубины равновесия (западная методика)."""

import numpy as np

from core.helpers import get_layer_at_depth
from core.models import Coefficients, Foundation, PointResult, SoilLayer

from .bearing import bearing_capacity_Vl


def calculate_point(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F: float,
    d: float,
) -> PointResult:
    """Расчёт для одной глубины d (западная методика).

    Args:
        layers: Список слоёв.
        foundation: Параметры фундамента.
        coef: Коэффициенты.
        F: Вертикальная нагрузка, кН.
        d: Глубина заглубления, м.

    Returns:
        PointResult с Vl вместо Nu.
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return PointResult(d=d, Nu=0.0, R=0.0, p=0.0, eta1=999.0, eta2=999.0, layer_name="Unknown")

    # Передаём F для расчёта H_cav по полной формуле C.2.5
    Vl = bearing_capacity_Vl(layers, foundation, d, F, coef.use_backfill)
    p = F / foundation.area_prime

    R = Vl / foundation.area_prime if foundation.area_prime > 0 else 0.0
    eta1 = F / Vl if Vl > 0 else np.inf
    eta2 = p / R if R > 0 else np.inf

    return PointResult(d=d, Nu=Vl, R=R, p=p, eta1=eta1, eta2=eta2, layer_name=layer.name)


def penetration_curve(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F: float,
    d_max: float = 20.0,
    d_step: float = 0.1,
) -> list[PointResult]:
    """Построение кривой пенетрации Vl(d).

    Args:
        layers: Список слоёв.
        foundation: Параметры фундамента.
        coef: Коэффициенты.
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
    d_step: float = 0.1,
) -> PointResult | None:
    """Найти безопасную глубину равновесия где F ≤ Vl(d).

    ВАЖНО: При punch-through кривая Vl(d) немонотонна.
    Ищем глубину, после которой нет провалов (зон с η₁ > 1).

    Args:
        layers: Список слоёв.
        foundation: Параметры фундамента.
        coef: Коэффициенты.
        F: Вертикальная нагрузка, кН.
        d_max: Максимальная глубина поиска, м.
        d_step: Шаг поиска, м.

    Returns:
        PointResult при η₁ ≤ 1 в безопасной зоне, или None если не найдено.
    """
    curve = penetration_curve(layers, foundation, coef, F, d_max, d_step)

    if not curve:
        return None

    safe_indices = [i for i, res in enumerate(curve) if res.eta1 <= 1.0]

    if not safe_indices:
        return None

    # Ищем безопасную глубину (без провалов ниже)
    for i in range(len(safe_indices) - 1, -1, -1):
        idx = safe_indices[i]
        has_instability_below = any(
            curve[j].eta1 > 1.0 for j in range(idx + 1, len(curve))
        )
        if not has_instability_below:
            return curve[idx]

    return curve[safe_indices[-1]]


def find_all_equilibrium_depths(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F: float,
    d_max: float = 30.0,
    d_step: float = 0.1,
) -> list[PointResult]:
    """Найти ВСЕ глубины равновесия и зоны неустойчивости.

    Возвращает список точек, где происходит переход:
    - от η₁ > 1 к η₁ ≤ 1 (вход в стабильную зону)
    - от η₁ ≤ 1 к η₁ > 1 (выход из стабильной зоны — ОПАСНО!)
    """
    curve = penetration_curve(layers, foundation, coef, F, d_max, d_step)

    if len(curve) < 2:
        return []

    transitions = []
    for i in range(1, len(curve)):
        prev_safe = curve[i - 1].eta1 <= 1.0
        curr_safe = curve[i].eta1 <= 1.0
        if prev_safe != curr_safe:
            transitions.append(curve[i])

    return transitions


def has_punch_through_risk(
    layers: list[SoilLayer],
    foundation: Foundation,
    coef: Coefficients,
    F: float,
    d_max: float = 30.0,
    d_step: float = 0.1,
) -> bool:
    """Проверить наличие риска punch-through.

    Риск существует, если кривая Vl(d) имеет локальный максимум
    с последующим падением ниже нагрузки F.
    """
    transitions = find_all_equilibrium_depths(layers, foundation, coef, F, d_max, d_step)
    return len(transitions) >= 2
