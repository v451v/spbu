"""Таблицы коэффициентов для западной методики (SNAME/ISO 19905-1).

Источники:
- SNAME 5-5A (Technical & Research Bulletin 5-5A)
- ISO 19905-1 / ГОСТ Р 59997
- InSafeJIP
"""

from functools import lru_cache

import numpy as np

# --- Константы ---

NC_CLAY = 5.14  # Коэффициент несущей способности для глин (φ=0)


# --- Коэффициенты несущей способности для песков (C.2.9) ---


@lru_cache(maxsize=256)
def bearing_factors_sand(phi_deg: float) -> tuple[float, float]:
    """Коэффициенты несущей способности Nγ, Nq для песков (SNAME/ISO).

    Nq = e^(π·tanφ) · tan²(45° + φ/2)
    Nγ = 2·(Nq + 1)·tanφ

    Кэшируется для ускорения повторных вызовов.

    Args:
        phi_deg: Угол внутреннего трения, градусы.

    Returns:
        (Nγ, Nq)
    """
    if phi_deg <= 0:
        return 0.0, 1.0

    phi_rad = np.radians(phi_deg)
    tan_phi = np.tan(phi_rad)

    # Nq = e^(π·tanφ) · tan²(45° + φ/2)
    n_q = np.exp(np.pi * tan_phi) * (np.tan(np.radians(45.0) + phi_rad / 2.0)) ** 2

    # Nγ = 2·(Nq + 1)·tanφ
    n_gamma = 2.0 * (n_q + 1.0) * tan_phi

    return float(n_gamma), float(n_q)


# --- Коэффициенты формы (shape factors) ---


@lru_cache(maxsize=64)
def shape_factor_clay(B: float, L: float) -> float:
    """Коэффициент формы sc для глин (SNAME).

    sc = 1 + 0.2·(B/L) для прямоугольного фундамента.
    sc = 1.2 для круглого/квадратного (B=L).

    Args:
        B: Ширина (или диаметр) фундамента, м.
        L: Длина фундамента, м.

    Returns:
        sc
    """
    if L <= 0:
        return 1.2
    return 1.0 + 0.2 * (B / L)


def shape_factors_sand(B: float, L: float, phi_deg: float) -> tuple[float, float]:
    """Коэффициенты формы sγ, sq для песков (SNAME/ISO).

    sγ = 1 - 0.4·(B/L)  (≥ 0.6)
    sq = 1 + (B/L)·sinφ

    Args:
        B: Ширина фундамента, м.
        L: Длина фундамента, м.
        phi_deg: Угол внутреннего трения, градусы.

    Returns:
        (sγ, sq)
    """
    if L <= 0:
        ratio = 1.0
    else:
        ratio = B / L

    s_gamma = max(0.6, 1.0 - 0.4 * ratio)
    s_q = 1.0 + ratio * np.sin(np.radians(phi_deg))

    return float(s_gamma), float(s_q)


# --- Коэффициенты глубины (depth factors) ---


@lru_cache(maxsize=512)
def depth_factor_clay(D: float, B: float) -> float:
    """Коэффициент глубины dc для глин (SNAME).

    dc = 1 + 0.4·(D/B)   при D/B ≤ 1
    dc = 1 + 0.4·arctan(D/B)  при D/B > 1

    Args:
        D: Глубина заглубления, м.
        B: Ширина (диаметр) фундамента, м.

    Returns:
        dc
    """
    if B <= 0:
        return 1.0

    ratio = D / B
    if ratio <= 1.0:
        return 1.0 + 0.4 * ratio
    else:
        return 1.0 + 0.4 * np.arctan(ratio)


def depth_factors_sand(D: float, B: float, phi_deg: float) -> tuple[float, float]:
    """Коэффициенты глубины dγ, dq для песков (SNAME/ISO).

    dγ = 1.0 (обычно принимается 1)
    dq = 1 + 2·tanφ·(1 - sinφ)²·(D/B)   при D/B ≤ 1
    dq = 1 + 2·tanφ·(1 - sinφ)²·arctan(D/B)  при D/B > 1

    Args:
        D: Глубина заглубления, м.
        B: Ширина фундамента, м.
        phi_deg: Угол внутреннего трения, градусы.

    Returns:
        (dγ, dq)
    """
    d_gamma = 1.0

    if B <= 0 or phi_deg <= 0:
        return d_gamma, 1.0

    phi_rad = np.radians(phi_deg)
    tan_phi = np.tan(phi_rad)
    sin_phi = np.sin(phi_rad)
    factor = 2.0 * tan_phi * (1.0 - sin_phi) ** 2

    ratio = D / B
    if ratio <= 1.0:
        d_q = 1.0 + factor * ratio
    else:
        d_q = 1.0 + factor * np.arctan(ratio)

    return float(d_gamma), float(d_q)


# --- Коэффициент сдвига при протыкании Ks (C.2.19) ---


def punch_through_coefficient_Ks(
    cu: float, gamma_prime: float, B: float, phi_deg: float
) -> float:
    """Коэффициент сдвига при протыкании песка в глину (C.2.19).

    Ks·tanφ ≈ 3·cu / (B·γ')
    => Ks ≈ 3·cu / (B·γ'·tanφ)

    Args:
        cu: Недренированная прочность глины, кПа.
        gamma_prime: Эффективный удельный вес, кН/м³.
        B: Ширина фундамента, м.
        phi_deg: Угол внутреннего трения песка, градусы.

    Returns:
        Ks
    """
    if B <= 0 or gamma_prime <= 0 or phi_deg <= 0:
        return 0.0

    tan_phi = np.tan(np.radians(phi_deg))
    if tan_phi <= 0:
        return 0.0

    return 3.0 * cu / (B * gamma_prime * tan_phi)
