"""Расчёт осадки по СП 22/23 (II группа ПС)."""

from core.helpers import (
    get_layer_at_depth,
    additional_stress_boussinesq,
    overburden_stress,
    reduced_dimensions,
)
from core.models import Foundation, SoilLayer
from core.russian.tables import stress_coefficient_alpha

DEFAULT_E = 10.0  # МПа

StressDistribution = str  # "alpha" | "boussinesq"


def vertical_stress(
    p_surface: float,
    foundation: Foundation,
    z: float,
    stress_distribution: StressDistribution = "alpha",
) -> float:
    """Вертикальное напряжение на глубине z от подошвы.

    Args:
        p_surface: Напряжение на уровне подошвы, кПа.
        foundation: Параметры фундамента.
        z: Глубина от подошвы, м.
        stress_distribution: "alpha" (СП 22 табл. 5.8, η=1) или "boussinesq".
    """
    b_p, l_p, _ = reduced_dimensions(foundation)
    if z <= 0:
        return max(0.0, p_surface)

    if stress_distribution == "boussinesq":
        return additional_stress_boussinesq(p_surface, b_p, l_p, z)

    # По умолчанию: нормативная таблица α (СП 22 табл. 5.8) для η=1.
    alpha = stress_coefficient_alpha(z, b_p)
    return max(0.0, alpha * p_surface)


def min_compressible_depth(b: float) -> float:
    """Минимальная глубина сжимаемой толщи Hmin (СП 22.13330 п.5.6.41).

    Args:
        b: Ширина фундамента, м.

    Returns:
        Hmin, м.
    """
    if b <= 10.0:
        return b / 2.0
    elif b <= 60.0:
        return 4.0 + 0.1 * b
    return 10.0


def compressible_depth(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    p: float,
    max_depth: float = 50.0,
    stress_distribution: StressDistribution = "alpha",
) -> float:
    """Глубина сжимаемой толщи Hc.

    Критерий: σzp = 0.5·σzg (или 0.2·σzg для E ≤ 7 МПа).

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        d: Глубина заглубления, м.
        p: Среднее давление под подошвой, кПа.
        max_depth: Максимальная глубина поиска, м.
        stress_distribution: "alpha" или "boussinesq".

    Returns:
        Hc, м — глубина сжимаемой толщи.
    """
    b_p, _, _ = reduced_dimensions(foundation)
    H_min = min_compressible_depth(b_p)
    sigma_zg_0 = overburden_stress(layers, d)

    z = 0.1
    while z <= max_depth:
        sigma_zp = vertical_stress(p, foundation, z, stress_distribution=stress_distribution)
        sigma_zg = vertical_stress(sigma_zg_0, foundation, z, stress_distribution=stress_distribution)

        layer = get_layer_at_depth(layers, d + z)
        E = layer.E if layer and layer.E is not None else DEFAULT_E
        ratio = 0.2 if E <= 7.0 else 0.5

        if sigma_zp <= ratio * sigma_zg and z >= H_min:
            return z
        z += 0.1

    return max(H_min, max_depth)


def settlement(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    p: float,
    beta: float = 0.8,
    stress_distribution: StressDistribution = "alpha",
) -> float:
    """Осадка методом послойного суммирования (C.1.4).

    s = β · Σ[(σzp,i - σzγ,i) · hi / Ei]

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        d: Глубина заглубления, м.
        p: Среднее давление под подошвой, кПа.
        beta: Безразмерный коэффициент (по умолчанию 0.8).
        stress_distribution: "alpha" или "boussinesq".

    Returns:
        s, м — осадка.
    """
    b_p, _, _ = reduced_dimensions(foundation)
    Hc = compressible_depth(
        layers,
        foundation,
        d,
        p,
        stress_distribution=stress_distribution,
    )
    sigma_zg_0 = overburden_stress(layers, d)

    h_max = 0.2 * b_p
    s = 0.0
    z_cursor = 0.0

    while z_cursor < Hc - 1e-6:
        # Определяем текущий слой и доступную толщину до его низа
        depth_abs = d + z_cursor
        z_top = 0.0
        current_layer = None
        for layer in layers:
            z_bot = z_top + layer.thickness
            if z_top <= depth_abs < z_bot:
                current_layer = layer
                break
            z_top = z_bot

        if current_layer is None:
            break

        available = (z_top + current_layer.thickness) - depth_abs
        h_seg = min(h_max, Hc - z_cursor, available)
        z_mid = z_cursor + h_seg / 2.0

        sigma_zp = vertical_stress(p, foundation, z_mid, stress_distribution=stress_distribution)
        sigma_zg = vertical_stress(sigma_zg_0, foundation, z_mid, stress_distribution=stress_distribution)
        delta_sigma = max(0.0, sigma_zp - sigma_zg)

        E = (current_layer.E if current_layer.E else DEFAULT_E) * 1000  # МПа → кПа
        s += delta_sigma * h_seg / E

        z_cursor += h_seg

    return beta * s
