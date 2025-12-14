"""Несущая способность по СП 22/23/58 (I и II группы ПС)."""

from core.helpers import (
    average_gamma_above,
    average_props_below,
    get_layer_at_depth,
    overburden_stress,
    reduced_dimensions,
    shape_factors,
)
from core.models import Coefficients, Foundation, SoilLayer
from core.russian.tables import bearing_capacity_factors, resistance_factors


def bearing_capacity_Nu(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    layer: SoilLayer | None = None,
) -> float:
    """Несущая способность Nu (C.1.1).

    Для дисперсных грунтов:
        Nu = A · (Nc·ξc·c + Nq·ξq·σzg + Nγ·ξγ·b·γ')

    Для скальных грунтов (СП 22.13330):
        Nu = Rc · b' · l'

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        d: Глубина заглубления, м.
        layer: Слой грунта (опционально, иначе определяется по глубине).

    Returns:
        Nu, кН — несущая способность.
    """
    if layer is None:
        layer = get_layer_at_depth(layers, d)
    if layer is None:
        return 0.0

    # === Скальные грунты (СП 22.13330) ===
    if layer.Rc is not None and layer.Rc > 0:
        # Rc в МПа, переводим в кПа (× 1000)
        return layer.Rc * 1000.0 * foundation.area_prime

    # === Дисперсные грунты ===
    # Все параметры (φ, c, γ') берутся из слоя под подошвой (СП 22.13330 п. 5.7)
    b_p, _, eta = reduced_dimensions(foundation)
    area = foundation.area_prime
    xi_gamma, xi_q, xi_c = shape_factors(eta)
    sigma_zg = overburden_stress(layers, d)
    N_gamma, N_q, N_c = bearing_capacity_factors(layer.phi)

    return area * (
        N_c * xi_c * layer.c
        + N_q * xi_q * sigma_zg
        + N_gamma * xi_gamma * b_p * layer.gamma_prime
    )


def design_resistance_R(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    coef: Coefficients,
) -> float:
    """Расчётное сопротивление R (C.1.3).

    R = (γc1·γc2/k)·[Mγ·kz·b·γII + Mq·d·γ′II + Mc·cII]

    Args:
        layers: Список слоёв грунта.
        foundation: Параметры фундамента.
        d: Глубина заглубления, м.
        coef: Коэффициенты надёжности.

    Returns:
        R, кПа — расчётное сопротивление.
    """
    b_p, _, _ = reduced_dimensions(foundation)
    kz = 1.0 if b_p < 10.0 else 8.0 / b_p + 0.2
    z_avg = b_p / 2.0 if b_p <= 10.0 else 4.0 + 0.1 * b_p

    gamma_II, phi_II, c_II = average_props_below(layers, d, z_avg)
    gamma_II_above = average_gamma_above(layers, d)
    M_gamma, M_q, M_c = resistance_factors(phi_II)

    return (coef.gamma_c1 * coef.gamma_c2 / coef.k) * (
        M_gamma * kz * b_p * gamma_II + M_q * d * gamma_II_above + M_c * c_II
    )
