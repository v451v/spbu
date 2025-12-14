"""Общие вспомогательные функции для расчётов основания СПБУ.

Используются обеими методиками (российской и западной).
"""

import numpy as np

from core.models import Foundation, SoilLayer


# =============================================================================
# Типы грунтов для автоопределения drainage (западная методика)
# =============================================================================

UNDRAINED_SOIL_TYPES = frozenset({
    "clay", "clay_soft", "clay_plastic", "clay_stiff",
    "silty_clay", "organic", "peat",
})

DRAINED_SOIL_TYPES = frozenset({
    "sand", "sand_fine", "sand_medium", "sand_coarse",
    "gravel", "rock",
})

DUAL_DRAINAGE_SOIL_TYPES = frozenset({
    "silt", "sandy_silt", "silty_sand",
})


def shape_factors(eta: float) -> tuple[float, float, float]:
    """Коэффициенты формы ξγ, ξq, ξc (СП 22.13330 п.5.7.7)."""
    eta = max(eta, 1.0)
    return (1.0 - 0.25 / eta, 1.0 + 1.5 / eta, 1.0 + 0.3 / eta)


def reduced_dimensions(foundation: Foundation) -> tuple[float, float, float]:
    """Приведённые размеры b', l' и η по СП 22 п.5.29."""
    b_p = foundation.b_prime
    l_p = foundation.l_prime
    eta = max(1.0, l_p / b_p) if b_p > 0 else 1.0
    return b_p, l_p, eta


def get_layer_at_depth(layers: list[SoilLayer], depth: float) -> SoilLayer | None:
    """Найти слой на заданной глубине."""
    z = 0.0
    for layer in layers:
        if z <= depth <= z + layer.thickness:
            return layer
        z += layer.thickness
    return layers[-1] if layers and depth > z else None


def overburden_stress(layers: list[SoilLayer], depth: float) -> float:
    """Бытовое давление σzg = Σ(γ'ᵢ · hᵢ), кПа.
    
    При depth > суммарной толщины слоёв — экстраполяция последним слоем.
    """
    if not layers or depth <= 0:
        return 0.0
    
    sigma = 0.0
    remaining = depth
    
    for layer in layers:
        if remaining <= 0:
            break
        h = min(layer.thickness, remaining)
        sigma += layer.gamma_prime * h
        remaining -= h
    
    # Экстраполяция за пределами скважины последним слоем
    if remaining > 0:
        sigma += layers[-1].gamma_prime * remaining
    
    return sigma


def average_props_below(
    layers: list[SoilLayer], d: float, z_thickness: float
) -> tuple[float, float, float]:
    """Средневзвешенные свойства грунта ниже подошвы (II группа ПС).
    
    При выходе за пределы скважины — экстраполяция последним слоем.
    """
    if not layers or z_thickness <= 0:
        layer = layers[-1] if layers else None
        if layer:
            return (
                layer.gamma_prime_II or layer.gamma_prime,
                layer.phi_II or layer.phi,
                layer.c_II or layer.c,
            )
        return 10.0, 20.0, 0.0
    
    z_start, z_end = d, d + z_thickness
    total_h = sum_gamma = sum_phi = sum_c = 0.0
    total_depth = sum(L.thickness for L in layers)

    z = 0.0
    for layer in layers:
        z_top, z_bot = z, z + layer.thickness
        z = z_bot

        h = min(z_bot, z_end) - max(z_top, z_start)
        if h <= 0:
            continue

        total_h += h
        sum_gamma += (layer.gamma_prime_II or layer.gamma_prime) * h
        sum_phi += (layer.phi_II or layer.phi) * h
        sum_c += (layer.c_II or layer.c) * h

    # Экстраполяция за пределами скважины последним слоем
    if z_end > total_depth:
        last = layers[-1]
        extra = z_end - max(total_depth, z_start)
        if extra > 0:
            total_h += extra
            sum_gamma += (last.gamma_prime_II or last.gamma_prime) * extra
            sum_phi += (last.phi_II or last.phi) * extra
            sum_c += (last.c_II or last.c) * extra

    if total_h <= 0:
        layer = layers[-1]
        return (
            layer.gamma_prime_II or layer.gamma_prime,
            layer.phi_II or layer.phi,
            layer.c_II or layer.c,
        )

    return sum_gamma / total_h, sum_phi / total_h, sum_c / total_h


def average_gamma_below(
    layers: list[SoilLayer], d: float, z_thickness: float
) -> float:
    """Средневзвешенное γ′ (I группа ПС) ниже подошвы на толщину z_thickness.
    
    При выходе за пределы скважины — экстраполяция последним слоем.
    """
    if not layers or z_thickness <= 0:
        return layers[-1].gamma_prime if layers else 0.0
    
    z_start, z_end = d, d + z_thickness
    total_h = gamma_sum = 0.0
    total_depth = sum(L.thickness for L in layers)

    z = 0.0
    for layer in layers:
        z_top, z_bot = z, z + layer.thickness
        z = z_bot

        h = min(z_bot, z_end) - max(z_top, z_start)
        if h <= 0:
            continue

        total_h += h
        gamma_sum += layer.gamma_prime * h

    # Экстраполяция за пределами скважины последним слоем
    if z_end > total_depth and layers:
        extra = z_end - max(total_depth, z_start)
        if extra > 0:
            total_h += extra
            gamma_sum += layers[-1].gamma_prime * extra

    if total_h <= 0:
        return layers[-1].gamma_prime if layers else 0.0

    return gamma_sum / total_h


def average_gamma_above(layers: list[SoilLayer], d: float) -> float:
    """Средневзвешенное γ′II по толщине от поверхности до глубины d."""
    if d <= 0:
        layer = layers[0] if layers else None
        return layer.gamma_prime_II or layer.gamma_prime if layer else 0.0

    remaining = d
    covered = 0.0
    gamma_sum = 0.0

    for layer in layers:
        if remaining <= 0:
            break
        h = min(layer.thickness, remaining)
        gamma_sum += (layer.gamma_prime_II or layer.gamma_prime) * h
        covered += h
        remaining -= h

    if remaining > 0 and layers:
        last = layers[-1]
        gamma_sum += (last.gamma_prime_II or last.gamma_prime) * remaining
        covered += remaining

    return gamma_sum / covered if covered > 0 else 0.0


# =============================================================================
# Функции для западной методики (SNAME/ISO)
# =============================================================================


def average_cu_below(
    layers: list[SoilLayer], d: float, z_thickness: float
) -> float:
    """Средневзвешенная недренированная прочность cu ниже подошвы (C.2.7).
    
    Args:
        layers: Список слоёв.
        d: Глубина подошвы, м.
        z_thickness: Толщина зоны усреднения, м (обычно ~1.0·B).
    """
    if not layers or z_thickness <= 0:
        layer = layers[-1] if layers else None
        return layer.cu or layer.c if layer else 0.0
    
    z_start, z_end = d, d + z_thickness
    total_h = cu_sum = 0.0
    total_depth = sum(L.thickness for L in layers)

    z = 0.0
    for layer in layers:
        z_top, z_bot = z, z + layer.thickness
        z = z_bot

        h = min(z_bot, z_end) - max(z_top, z_start)
        if h <= 0:
            continue

        total_h += h
        cu = layer.cu if layer.cu is not None else layer.c
        cu_sum += cu * h

    # Экстраполяция за пределами скважины последним слоем
    if z_end > total_depth and layers:
        last = layers[-1]
        extra = z_end - max(total_depth, z_start)
        if extra > 0:
            total_h += extra
            cu = last.cu if last.cu is not None else last.c
            cu_sum += cu * extra

    return cu_sum / total_h if total_h > 0 else 0.0


def average_sand_props_below(
    layers: list[SoilLayer], d: float, z_thickness: float
) -> tuple[float, float]:
    """Средневзвешенные свойства песка (φ, γ') ниже подошвы (C.2.9).
    
    Args:
        layers: Список слоёв.
        d: Глубина подошвы, м.
        z_thickness: Толщина зоны усреднения, м (обычно ~1.0·B).
        
    Returns:
        (phi_avg, gamma_prime_avg)
    """
    if not layers or z_thickness <= 0:
        layer = layers[-1] if layers else None
        if layer:
            return layer.phi, layer.gamma_prime
        return 30.0, 10.0
    
    z_start, z_end = d, d + z_thickness
    total_h = phi_sum = gamma_sum = 0.0
    total_depth = sum(L.thickness for L in layers)

    z = 0.0
    for layer in layers:
        z_top, z_bot = z, z + layer.thickness
        z = z_bot

        h = min(z_bot, z_end) - max(z_top, z_start)
        if h <= 0:
            continue

        total_h += h
        phi_sum += layer.phi * h
        gamma_sum += layer.gamma_prime * h

    # Экстраполяция за пределами скважины последним слоем
    if z_end > total_depth and layers:
        last = layers[-1]
        extra = z_end - max(total_depth, z_start)
        if extra > 0:
            total_h += extra
            phi_sum += last.phi * extra
            gamma_sum += last.gamma_prime * extra

    if total_h <= 0:
        layer = layers[-1]
        return layer.phi, layer.gamma_prime

    return phi_sum / total_h, gamma_sum / total_h


def get_drainage(layer: SoilLayer) -> str:
    """Определить условия дренирования (drained/undrained)."""
    if layer.drainage:
        return layer.drainage

    soil_type = (layer.soil_type or "").lower()
    if soil_type in UNDRAINED_SOIL_TYPES:
        return "undrained"
    if soil_type in DRAINED_SOIL_TYPES:
        return "drained"
    if soil_type in DUAL_DRAINAGE_SOIL_TYPES:
        return "undrained"

    return "undrained" if layer.cu and layer.cu > 0 else "drained"


def is_dual_drainage(layer: SoilLayer) -> bool:
    """Проверить, требует ли грунт двойного расчёта (silt)."""
    return (layer.soil_type or "").lower() in DUAL_DRAINAGE_SOIL_TYPES


def spud_cone_volume(D_eff: float, beta_deg: float) -> float:
    """Эквивалентный объём конуса шипа (C.2.3): Vs = π/24·Deff³·tan(β/2)."""
    if D_eff <= 0 or beta_deg <= 0:
        return 0.0
    return (np.pi / 24.0) * D_eff**3 * np.tan(np.radians(beta_deg / 2.0))


def cavity_depth_ratio(
    su_m: float, gamma_prime: float, B: float, p: float = 0.0
) -> float:
    """Относительная глубина полости Hcav/B (C.2.5).
    
    S = (s_um / (γ'·B)) · (1 - p/γ')
    Hcav/B = S^0.55 - 0.25·S
    
    Args:
        su_m: Недренированная прочность у дна моря, кПа.
        gamma_prime: Эффективный удельный вес грунта, кН/м³.
        B: Эффективный диаметр башмака, м.
        p: Эффективная вертикальная нагрузка, кПа (опционально).
    """
    if gamma_prime <= 0 or B <= 0:
        return 0.0
    
    # Коэффициент влияния давления (C.2.5)
    pressure_factor = max(0.0, 1.0 - p / gamma_prime) if gamma_prime > 0 else 1.0
    
    S = (su_m / (gamma_prime * B)) * pressure_factor
    return S**0.55 - 0.25 * S if S > 0 else 0.0


def cavity_depth(
    su_m: float, gamma_prime: float, B: float, p: float = 0.0
) -> float:
    """Глубина полости над башмаком Hcav (C.2.5).
    
    Args:
        su_m: Недренированная прочность у дна моря, кПа.
        gamma_prime: Эффективный удельный вес грунта, кН/м³.
        B: Эффективный диаметр башмака, м.
        p: Эффективная вертикальная нагрузка, кПа (опционально).
    """
    return max(0.0, cavity_depth_ratio(su_m, gamma_prime, B, p) * B)


def min_backfill_weight(
    gamma_prime: float, A: float, D: float, H_cav: float, V_spud: float, V_D: float
) -> float:
    """Минимальный вес обратной засыпки (C.2.4): Wbf = γ'·[A·(D-Hcav) - (Vspud-VD)]."""
    if gamma_prime <= 0:
        return 0.0
    volume = A * max(0.0, D - H_cav) - (V_spud - V_D)
    return max(0.0, gamma_prime * volume)


def buoyancy_force(gamma_prime: float, V_displaced: float) -> float:
    """Сила выдавливания Bs = γ'·Vd (C.2.1)."""
    return gamma_prime * max(0.0, V_displaced)


def additional_stress_boussinesq(p: float, b: float, l: float, z: float) -> float:
    """Дополнительное вертикальное напряжение по Буссинеску (формула 6.14).

    Распределение давления под прямоугольной нагрузкой с учётом
    пространственного затухания напряжений в массиве грунта.

    Args:
        p: Среднее давление под подошвой фундамента, кПа
        b: Ширина фундамента (меньшая сторона), м
        l: Длина фундамента (большая сторона), м
        z: Глубина расчётной точки от подошвы, м

    Returns:
        σ_zp: Дополнительное вертикальное напряжение, кПа

    Formula (6.14):
        σ_zp = (2p/π) × [
            2ηξ(η²+8ξ²+1) / [(η²+4ξ²)(1+4ξ²)√(η²+4ξ²+1)]
            + arctan(η / [2ξ√(η²+4ξ²+1)])
        ]
    где:
        ξ = z/b - относительная глубина
        η = l/b - отношение сторон фундамента
    """
    if z <= 0 or b <= 0 or l <= 0:
        return p  # На подошве σ_zp = p

    # Относительные параметры
    xi = z / b       # ξ = z/b
    eta = l / b      # η = l/b

    # Первое слагаемое
    numerator_1 = 2 * eta * xi * (eta**2 + 8*xi**2 + 1)
    denominator_1 = (eta**2 + 4*xi**2) * (1 + 4*xi**2) * np.sqrt(eta**2 + 4*xi**2 + 1)
    term_1 = numerator_1 / denominator_1 if denominator_1 > 0 else 0.0

    # Второе слагаемое (арктангенс)
    numerator_2 = eta
    denominator_2 = 2 * xi * np.sqrt(eta**2 + 4*xi**2 + 1)
    term_2 = np.arctan(numerator_2 / denominator_2) if denominator_2 > 0 else 0.0

    # Итоговое напряжение
    sigma_zp = (2 * p / np.pi) * (term_1 + term_2)

    return max(0.0, sigma_zp)
