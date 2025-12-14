"""Несущая способность по западной методике (SNAME/ISO).

Включает:
- Однородные толщи (глина, песок)
- Слоистые толщи (squeezing, punch-through)
- Итоговые Qv и Vl
"""

import numpy as np

from core.helpers import (
    average_cu_below,
    average_sand_props_below,
    buoyancy_force,
    cavity_depth,
    get_drainage,
    get_layer_at_depth,
    is_dual_drainage,
    min_backfill_weight,
    overburden_stress,
    spud_cone_volume,
)
from core.western.tables import (
    NC_CLAY,
    bearing_factors_sand,
    depth_factor_clay,
    depth_factors_sand,
    punch_through_coefficient_Ks,
    shape_factor_clay,
    shape_factors_sand,
)
from core.models import Foundation, SoilLayer


# =============================================================================
# Несущая способность однородной толщи
# =============================================================================


def bearing_capacity_clay(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
) -> float:
    """Несущая способность для глин (недренированные условия) (C.2.7).

    Fv = (cu·Nc·sc·dc + p0')·A
    
    Согласно C.2.7: cu — усреднённая в пределах характерной глубины (~1.0·B).
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return 0.0

    B = foundation.b_prime
    L = foundation.l_prime
    A = foundation.area_prime

    # Усреднённая прочность в зоне деформации ~1.0·B (C.2.7)
    influence_depth = B
    cu = average_cu_below(layers, d, influence_depth)
    if cu <= 0:
        # Fallback на точечное значение
        cu = layer.cu if layer.cu is not None else layer.c
    if cu <= 0:
        return 0.0

    Nc = NC_CLAY
    sc = shape_factor_clay(B, L)
    dc = depth_factor_clay(d, B)
    p0_prime = overburden_stress(layers, d)

    return (cu * Nc * sc * dc + p0_prime) * A


def bearing_capacity_sand(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
) -> float:
    """Несущая способность для песков (дренированные условия) (C.2.9).

    Fv = (0.5·γ'·B·Nγ·sγ·dγ + p0'·Nq·sq·dq)·A
    
    Свойства усредняются в зоне деформации (~1.0·B).
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return 0.0

    B = foundation.b_prime
    L = foundation.l_prime
    A = foundation.area_prime

    # Усреднённые свойства в зоне деформации ~1.0·B
    influence_depth = B
    phi, gamma_prime = average_sand_props_below(layers, d, influence_depth)
    
    if phi <= 0:
        # Fallback на точечное значение
        phi = layer.phi
    if phi <= 0:
        return 0.0

    N_gamma, N_q = bearing_factors_sand(phi)
    s_gamma, s_q = shape_factors_sand(B, L, phi)
    d_gamma, d_q = depth_factors_sand(d, B, phi)
    p0_prime = overburden_stress(layers, d)

    return (
        0.5 * gamma_prime * B * N_gamma * s_gamma * d_gamma
        + p0_prime * N_q * s_q * d_q
    ) * A


# =============================================================================
# Несущая способность слоистых толщ
# =============================================================================


def bearing_capacity_squeezing(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H_weak: float,
    cu_weak: float,
    cu_strong: float,
) -> float:
    """Несущая способность при сжатии слабого слоя глин (C.2.12-C.2.13)."""
    B = foundation.b_prime
    A = foundation.area_prime

    if H_weak <= 0 or cu_weak <= 0:
        return 0.0

    a, b = 5.0, 0.33  # Meyerhof & Chaplin

    Nc = NC_CLAY
    sc = shape_factor_clay(B, foundation.l_prime)
    dc = depth_factor_clay(d, B)

    Nc_mod = Nc * (1.0 + a * (cu_strong / cu_weak - 1.0) * (B / H_weak) ** b)
    Nc_upper = Nc * sc * dc * cu_strong / cu_weak
    Nc_mod = min(Nc_mod, Nc_upper)

    p0_prime = overburden_stress(layers, d)
    return (cu_weak * Nc_mod * sc * dc + p0_prime) * A


def bearing_capacity_punch_through_clay(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H: float,
    cu_top: float,
    cu_bottom: float,
) -> float:
    """Несущая способность при протыкании: два слоя глин (C.2.14)."""
    B = foundation.b_prime
    L = foundation.l_prime
    A = foundation.area_prime

    if cu_top <= 0:
        return 0.0

    Nc = NC_CLAY
    sc = shape_factor_clay(B, L)

    Fv_punch = A * (3.0 * H / B * cu_top + Nc * sc * cu_bottom)
    Fv_upper = A * Nc * sc * cu_top

    return min(Fv_punch, Fv_upper)


def _punch_through_load_spread(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H_sand: float,
    gamma_sand: float,
    cu_clay: float,
    n: float = 5.0,
) -> float:
    """Метод расширения нагрузки (Load Spread, C.2.20)."""
    B = foundation.b_prime
    L = foundation.l_prime
    A = foundation.area_prime

    if H_sand <= 0 or cu_clay <= 0:
        return 0.0

    B_star = B + 2.0 * H_sand / n
    A_star = (1.0 + 2.0 * H_sand / (n * B)) ** 2 * A

    Nc = NC_CLAY
    sc = shape_factor_clay(B_star, L + 2.0 * H_sand / n)

    p0_prime = overburden_stress(layers, d + H_sand)
    Fv_b = (cu_clay * Nc * sc + p0_prime) * A_star
    W = A_star * H_sand * gamma_sand

    return max(0.0, Fv_b - W)


def _punch_through_ks_shear(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H_sand: float,
    phi_sand: float,
    gamma_sand: float,
    cu_clay: float,
) -> float:
    """Метод сдвига Ks (Punching Shear, C.2.19)."""
    B = foundation.b_prime
    L = foundation.l_prime
    A = foundation.area_prime

    if H_sand <= 0 or cu_clay <= 0 or phi_sand <= 0:
        return 0.0

    Nc = NC_CLAY
    sc = shape_factor_clay(B, L)
    dc = depth_factor_clay(d + H_sand, B)
    p0_prime = overburden_stress(layers, d + H_sand)

    Qv_clay = (cu_clay * Nc * sc * dc + p0_prime) * A

    Ks = punch_through_coefficient_Ks(cu_clay, gamma_sand, B, phi_sand)
    tan_phi = np.tan(np.radians(phi_sand))
    sigma_v_avg = gamma_sand * H_sand / 2.0
    perimeter = np.pi * B
    As = perimeter * H_sand
    T_side = Ks * tan_phi * sigma_v_avg * As

    return max(0.0, Qv_clay + T_side)


def bearing_capacity_punch_through_sand_clay(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H_sand: float,
    phi_sand: float,
    gamma_sand: float,
    cu_clay: float,
) -> float:
    """Несущая способность при протыкании: песок над глиной (C.2.19-C.2.20).

    Использует ТРИ метода и возвращает МИНИМУМ:
    - Load Spread с n=3
    - Load Spread с n=5
    - Ks Shear (punching shear)
    
    По документу: расчёт для n=3 и n=5 с выбором минимума.
    """
    if H_sand <= 0 or cu_clay <= 0:
        return 0.0

    # Load Spread для n=3 и n=5, берём минимум (по документу C.2.20)
    Fv_load_spread_n3 = _punch_through_load_spread(
        layers, foundation, d, H_sand, gamma_sand, cu_clay, n=3.0
    )
    Fv_load_spread_n5 = _punch_through_load_spread(
        layers, foundation, d, H_sand, gamma_sand, cu_clay, n=5.0
    )
    Fv_load_spread = min(Fv_load_spread_n3, Fv_load_spread_n5)
    
    # Ks Shear метод
    Fv_ks_shear = _punch_through_ks_shear(
        layers, foundation, d, H_sand, phi_sand, gamma_sand, cu_clay
    )

    if Fv_ks_shear > 0:
        return min(Fv_load_spread, Fv_ks_shear)
    return Fv_load_spread


def detect_failure_mechanism(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
) -> str:
    """Определить преобладающий механизм разрушения.

    - "general_shear" — однородная толща
    - "squeezing" — слабый слой над прочным
    - "punch_through" — прочный слой над слабым
    """
    B = foundation.b_prime
    influence_depth = 1.5 * B
    z = 0.0
    relevant_layers = []

    for layer in layers:
        z_top = z
        z_bot = z + layer.thickness
        z = z_bot
        if z_bot > d and z_top < d + influence_depth:
            relevant_layers.append((layer, max(0, z_top - d), min(z_bot - d, influence_depth)))

    if len(relevant_layers) <= 1:
        return "general_shear"

    layer1, _, _ = relevant_layers[0]
    layer2, _, _ = relevant_layers[1]

    drainage1 = get_drainage(layer1)
    drainage2 = get_drainage(layer2)

    # Sand over Clay → punch_through
    if drainage1 == "drained" and drainage2 == "undrained":
        return "punch_through"

    # Clay over Sand → general_shear
    if drainage1 == "undrained" and drainage2 == "drained":
        return "general_shear"

    # Clay over Clay → сравниваем cu
    if drainage1 == "undrained" and drainage2 == "undrained":
        cu1 = layer1.cu if layer1.cu else layer1.c
        cu2 = layer2.cu if layer2.cu else layer2.c
        if cu1 <= 0 or cu2 <= 0:
            return "general_shear"
        if cu1 > cu2 * 1.2:
            return "punch_through"
        if cu2 > cu1 * 1.2:
            return "squeezing"
        return "general_shear"

    # Sand over Sand → сравниваем φ
    if drainage1 == "drained" and drainage2 == "drained":
        phi1, phi2 = layer1.phi, layer2.phi
        if phi1 <= 0 or phi2 <= 0:
            return "general_shear"
        if phi1 > phi2 * 1.2:
            return "punch_through"
        if phi2 > phi1 * 1.2:
            return "squeezing"
        return "general_shear"

    return "general_shear"


# =============================================================================
# Трёхслойный анализ (C.2.3.4.4)
# =============================================================================


def _collect_layer_params(
    layers: list[SoilLayer], d: float, influence_depth: float, max_layers: int = 3
) -> list[dict]:
    """Собрать параметры слоёв в зоне влияния."""
    z = 0.0
    layer_params = []
    
    for lyr in layers:
        z_top = z
        z_bot = z + lyr.thickness
        z = z_bot
        
        if z_bot <= d:
            continue
        if z_top >= d + influence_depth:
            break
            
        layer_params.append({
            "layer": lyr,
            "z_top": max(z_top, d),
            "z_bot": min(z_bot, d + influence_depth),
            "H": min(z_bot, d + influence_depth) - max(z_top, d),
            "drainage": get_drainage(lyr),
            "is_dual": is_dual_drainage(lyr),  # для двойного расчёта (silt)
            "cu": lyr.cu if lyr.cu else lyr.c,
            "phi": lyr.phi,
            "gamma": lyr.gamma_prime,
        })
        
        if len(layer_params) >= max_layers:
            break
    
    return layer_params


def bearing_capacity_three_layer(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    layer_params: list[dict],
) -> float:
    """Несущая способность для 3-слойной системы (C.2.3.4.4).
    
    Расчёт выполняется по схеме:
    1. Анализ верхнего и среднего слоев как двухслойной системы
    2. Анализ среднего и нижнего слоев (эквивалентное основание)
    3. Итоговая оценка = минимум по всем сценариям
    """
    if len(layer_params) < 3:
        return 0.0
    
    lp1, lp2, lp3 = layer_params[0], layer_params[1], layer_params[2]
    results = []
    
    # === Сценарий 1: Двухслойная система (слои 1-2) ===
    H1 = lp1["H"]
    
    # Sand над Clay → punch-through
    if lp1["drainage"] == "drained" and lp2["drainage"] == "undrained":
        Qv_12 = bearing_capacity_punch_through_sand_clay(
            layers, foundation, d, H1, lp1["phi"], lp1["gamma"], lp2["cu"]
        )
        results.append(Qv_12)
    # Clay над Clay → punch-through или squeezing
    elif lp1["drainage"] == "undrained" and lp2["drainage"] == "undrained":
        cu1, cu2 = lp1["cu"], lp2["cu"]
        if cu1 > cu2 * 1.2:  # punch-through
            Qv_12 = bearing_capacity_punch_through_clay(
                layers, foundation, d, H1, cu1, cu2
            )
            results.append(Qv_12)
        elif cu2 > cu1 * 1.2:  # squeezing
            Qv_12 = bearing_capacity_squeezing(
                layers, foundation, d, H1, cu1, cu2
            )
            results.append(Qv_12)
    
    # === Сценарий 2: Двухслойная система (слои 2-3) ===
    # Глубина эквивалентного основания на кровле слоя 2
    d_equiv = lp2["z_top"]
    H2 = lp2["H"]
    
    # Sand над Clay → punch-through (слой 2 над слоем 3)
    if lp2["drainage"] == "drained" and lp3["drainage"] == "undrained":
        Qv_23 = bearing_capacity_punch_through_sand_clay(
            layers, foundation, d_equiv, H2, lp2["phi"], lp2["gamma"], lp3["cu"]
        )
        results.append(Qv_23)
    # Clay над Clay → punch-through или squeezing
    elif lp2["drainage"] == "undrained" and lp3["drainage"] == "undrained":
        cu2, cu3 = lp2["cu"], lp3["cu"]
        if cu2 > cu3 * 1.2:  # punch-through в слой 3
            Qv_23 = bearing_capacity_punch_through_clay(
                layers, foundation, d_equiv, H2, cu2, cu3
            )
            results.append(Qv_23)
        elif cu3 > cu2 * 1.2:  # squeezing слоя 2
            Qv_23 = bearing_capacity_squeezing(
                layers, foundation, d_equiv, H2, cu2, cu3
            )
            results.append(Qv_23)
    
    # === Сценарий 3: Общий сдвиг в однородной толще ===
    layer = lp1["layer"]
    if lp1["drainage"] == "undrained":
        Qv_gs = bearing_capacity_clay(layers, foundation, d)
    else:
        Qv_gs = bearing_capacity_sand(layers, foundation, d)
    results.append(Qv_gs)
    
    # Возвращаем минимум (наиболее консервативная оценка)
    return min(r for r in results if r > 0) if results else 0.0


# =============================================================================
# Итоговая несущая способность Qv и Vl
# =============================================================================


def bearing_capacity_Qv(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
) -> float:
    """Предельная вертикальная несущая способность Qv.

    Для пылеватых грунтов выполняется ДВОЙНОЙ расчёт и берётся МИНИМУМ.
    Для слоистых толщ (2-3 слоя) анализируются все возможные механизмы разрушения.
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return 0.0

    B = foundation.b_prime
    drainage = get_drainage(layer)
    
    # Собираем параметры слоёв в зоне влияния (1.5·B)
    influence_depth = 1.5 * B
    layer_params = _collect_layer_params(layers, d, influence_depth, max_layers=3)
    
    # === Однородная толща ===
    if len(layer_params) <= 1:
        if is_dual_drainage(layer):
            Qv_clay = bearing_capacity_clay(layers, foundation, d)
            Qv_sand = bearing_capacity_sand(layers, foundation, d)
            if Qv_clay > 0 and Qv_sand > 0:
                return min(Qv_clay, Qv_sand)
            return Qv_clay if Qv_clay > 0 else Qv_sand

        if drainage == "undrained":
            return bearing_capacity_clay(layers, foundation, d)
        return bearing_capacity_sand(layers, foundation, d)

    # === Трёхслойная система (C.2.3.4.4) ===
    if len(layer_params) >= 3:
        return bearing_capacity_three_layer(layers, foundation, d, layer_params)

    # === Двухслойная система ===
    lp1, lp2 = layer_params[0], layer_params[1]
    H_top = lp1["H"]
    
    mechanism = detect_failure_mechanism(layers, foundation, d)
    
    results = []
    
    # Для dual drainage (silt) слоёв: рассматриваем оба варианта дренирования
    # Определяем эффективные типы дренирования с учётом dual drainage
    drainages_top = ["drained", "undrained"] if lp1["is_dual"] else [lp1["drainage"]]
    drainages_bot = ["drained", "undrained"] if lp2["is_dual"] else [lp2["drainage"]]
    
    for d_top in drainages_top:
        for d_bot in drainages_bot:
            if mechanism == "punch_through":
                if d_top == "undrained" and d_bot == "undrained":
                    Qv = bearing_capacity_punch_through_clay(
                        layers, foundation, d, H_top, lp1["cu"], lp2["cu"]
                    )
                    results.append(Qv)
                elif d_top == "drained" and d_bot == "undrained":
                    Qv = bearing_capacity_punch_through_sand_clay(
                        layers, foundation, d, H_top, lp1["phi"], lp1["gamma"], lp2["cu"]
                    )
                    results.append(Qv)

            elif mechanism == "squeezing":
                if d_top == "undrained" and d_bot == "undrained":
                    Qv = bearing_capacity_squeezing(
                        layers, foundation, d, H_top, lp1["cu"], lp2["cu"]
                    )
                    results.append(Qv)

            # Добавляем общий сдвиг как альтернативу
            if d_top == "undrained":
                results.append(bearing_capacity_clay(layers, foundation, d))
            else:
                results.append(bearing_capacity_sand(layers, foundation, d))

    # Возвращаем минимум (консервативная оценка)
    valid_results = [r for r in results if r > 0]
    return min(valid_results) if valid_results else 0.0


def bearing_capacity_Vl(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    F: float = 0.0,
    use_backfill: bool = False,
) -> float:
    """Несущая способность с учётом выдавливания и обратной засыпки (C.2.1-C.2.2).

    Без засыпки: Vl = Qv + Bs
    С засыпкой:  Vl = Qv - Wbf + Bs

    Args:
        layers: Список слоёв.
        foundation: Параметры фундамента.
        d: Глубина заглубления, м.
        F: Вертикальная нагрузка, кН (для расчёта H_cav по C.2.5).
        use_backfill: Учитывать обратную засыпку.
    """
    Qv = bearing_capacity_Qv(layers, foundation, d)

    layer = get_layer_at_depth(layers, d)
    gamma = layer.gamma_prime if layer else 10.0

    # Объём вытесненного грунта (C.2.3)
    # Если задан V_D — используем его, иначе рассчитываем
    if foundation.V_D is not None:
        V_displaced = foundation.V_D
    else:
        # Базовый объём = A·d
        V_displaced = foundation.area_prime * d
        # Добавляем объём конуса шипа, если задан (C.2.3)
        if foundation.D_eff and foundation.beta:
            V_s = spud_cone_volume(foundation.D_eff, foundation.beta)
            V_displaced += V_s

    Bs = buoyancy_force(gamma, V_displaced)

    if not use_backfill:
        return Qv + Bs

    # С учётом засыпки
    # По C.2.5: su,m — прочность на сдвиг у поверхности морского дна (d=0)
    seabed_layer = get_layer_at_depth(layers, 0.0)
    su_m = seabed_layer.cu if seabed_layer and seabed_layer.cu else (
        seabed_layer.c if seabed_layer else 0.0
    )
    
    # Расчёт H_cav по полной формуле (C.2.5)
    p = F / foundation.area_prime if foundation.area_prime > 0 and F > 0 else 0.0
    H_cav = cavity_depth(su_m, gamma, foundation.b_prime, p) if su_m > 0 else 0.0

    Wbf = min_backfill_weight(
        gamma, foundation.area_prime, d, H_cav,
        foundation.V_spud or 0.0, foundation.V_D or 0.0
    )

    return Qv - Wbf + Bs
