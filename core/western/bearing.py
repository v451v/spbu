"""Несущая способность по западной методике (SNAME/ISO).

Включает:
- Однородные толщи (глина, песок)
- Слоистые толщи (squeezing, punch-through)
- Итоговые Qv и Vl
"""

from dataclasses import dataclass

import numpy as np

from core.helpers import (
    average_cu_below,
    average_sand_props_below,
    buoyancy_force,
    cavity_depth,
    cu_variability_ratio,
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
    clay_factor_iso_table_23_1,
    depth_factors_sand,
    punch_through_coefficient_Ks,
    shape_factor_clay,
    shape_factors_sand,
)
from core.models import Foundation, SoilLayer, SoilProfileCache


def _min_positive(values: list[float]) -> float:
    valid = [v for v in values if v > 0]
    return min(valid) if valid else 0.0


@dataclass(frozen=True)
class LayerWindow:
    layer: SoilLayer
    z_top: float
    z_bot: float
    H: float
    drainage: str
    is_dual: bool
    cu: float
    phi: float
    gamma: float


# =============================================================================
# Несущая способность однородной толщи
# =============================================================================


def bearing_capacity_clay(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    cache: SoilProfileCache | None = None,
) -> float:
    """Несущая способность для глин (недренированные условия) (C.2.7).

    Fv = (cu·Nc·sc·dc + p0')·A
    
    Согласно C.2.7: cu — усреднённая в пределах характерной глубины (~1.0·B).
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return 0.0

    B = foundation.B_eff
    A = foundation.area_prime

    # C.2.3.1: при сильной изменчивости cu (>50% на глубину B) используем послойное суммирование.
    influence_depth = 0.5 * B
    variability = cu_variability_ratio(layers, d, B, cache=cache)
    if variability > 0.5:
        influence_depth = B

    cu = average_cu_below(layers, d, influence_depth, cache=cache)
    if cu <= 0:
        # Fallback на точечное значение
        cu = layer.cu if layer.cu is not None else layer.c
    if cu <= 0:
        return 0.0

    p0_prime = overburden_stress(layers, d, cache=cache)

    # Табл. 2.3-1 (ISO/ГОСТ): используем табличный множитель Nc·s·dc
    # (в текущей реализации принят как основной способ для глин).
    ncsdc = clay_factor_iso_table_23_1(d / B if B > 0 else 0.0)
    return (cu * ncsdc + p0_prime) * A


def bearing_capacity_sand(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    cache: SoilProfileCache | None = None,
) -> float:
    """Несущая способность для песков (дренированные условия) (C.2.9).

    Fv = (0.5·γ'·B·Nγ·sγ·dγ + p0'·Nq·sq·dq)·A
    
    Свойства усредняются в зоне деформации (~1.0·B).
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return 0.0

    B = foundation.B_eff
    L = B  # круглый башмак в западной методике
    A = foundation.area_prime

    # Усреднённые свойства в зоне деформации ~1.0·B
    influence_depth = B
    phi, gamma_prime = average_sand_props_below(layers, d, influence_depth, cache=cache)
    
    if phi <= 0:
        # Fallback на точечное значение
        phi = layer.phi
    if phi <= 0:
        return 0.0

    N_gamma, N_q = bearing_factors_sand(phi)
    s_gamma, s_q = shape_factors_sand(B, L, phi)
    d_gamma, d_q = depth_factors_sand(d, B, phi)
    p0_prime = overburden_stress(layers, d, cache=cache)

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
    T: float,
    cu_weak: float,
    use_backflow: bool = False,
    cache: SoilProfileCache | None = None,
) -> float:
    """Несущая способность при сжатии (squeezing) слоя глин (C.2.12–C.2.13)."""
    B = foundation.B_eff
    A = foundation.area_prime

    if T <= 0 or cu_weak <= 0 or B <= 0 or A <= 0:
        return 0.0

    # Условия применимости squeezing (C.2.3.4.1):
    # SNAME: B ≥ 3.45·T·(1 + 1.1·D/B)
    # ISO 19905-1/ГОСТ: B ≥ 3.45·T·(1 + 1.025·D/B) при D/B ≤ 2.5
    ratio = d / B
    k_iso = 1.025 if ratio <= 2.5 else 1.1
    if B < 3.45 * T * (1.0 + k_iso * ratio):
        return 0.0

    a, b = 5.0, 0.33  # Meyerhof & Chaplin (рекомендовано)
    sc = shape_factor_clay(B, B)  # круглый башмак
    dc = 1.0 + 0.2 * (d / B)

    p0_prime = overburden_stress(layers, d, cache=cache)
    squeeze_factor = a + b * (B / T) + 1.2 * (d / B)

    # C.2.12 / C.2.13: без/с back-flow (в методике p0' отсутствует для full back-flow)
    add_overburden = 0.0 if use_backflow else p0_prime

    Fv_squeeze = A * (squeeze_factor * cu_weak + add_overburden)
    Fv_limit = A * (NC_CLAY * sc * dc * cu_weak + add_overburden)

    return min(Fv_squeeze, Fv_limit)


def bearing_capacity_punch_through_clay(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H: float,
    cu_top: float,
    cu_bottom: float,
    use_backflow: bool = False,
    cache: SoilProfileCache | None = None,
) -> float:
    """Несущая способность при протыкании: два слоя глин (C.2.14–C.2.16)."""
    B = foundation.B_eff
    A = foundation.area_prime

    if B <= 0 or A <= 0 or cu_top <= 0:
        return 0.0

    sc = shape_factor_clay(B, B)  # круглый башмак
    p0_prime = overburden_stress(layers, d, cache=cache)

    # C.2.14 (Brown & Meyerhof, 1969) — как базовый консервативный вариант
    Fv_c214_punch = A * (3.0 * (H / B) * cu_top + NC_CLAY * sc * cu_bottom)
    Fv_c214_upper = A * (NC_CLAY * sc * cu_top)
    Fv_c214 = min(Fv_c214_punch, Fv_c214_upper)

    # C.2.15 / C.2.16 (SNAME): для глубокого заложения, с/без back-flow
    dc_bottom = 1.0 + 0.2 * ((d + H) / B) if B > 0 else 1.0
    add_overburden = 0.0 if use_backflow else p0_prime

    left = 3.0 * (H / B) * cu_top + NC_CLAY * sc * dc_bottom * cu_bottom + add_overburden
    Fv_left = A * left

    # Правая часть (однородная глина верхнего слоя): Nc·sc·dc берём из табл. 2.3-1
    ncsdc_top = clay_factor_iso_table_23_1(d / B)
    Fv_right = A * (cu_top * ncsdc_top + add_overburden)

    Fv_c215_216 = min(Fv_left, Fv_right)

    return min(Fv_c214, Fv_c215_216)


def _punch_through_load_spread(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H_sand: float,
    gamma_sand: float,
    cu_clay: float,
    n: float = 5.0,
    cache: SoilProfileCache | None = None,
) -> float:
    """Метод расширения нагрузки (Load Spread, C.2.20)."""
    B = foundation.B_eff
    L = B
    A = foundation.area_prime

    if H_sand <= 0 or cu_clay <= 0:
        return 0.0

    B_star = B + 2.0 * H_sand / n
    A_star = (1.0 + 2.0 * H_sand / (n * B)) ** 2 * A

    Nc = NC_CLAY
    sc = shape_factor_clay(B_star, L + 2.0 * H_sand / n)

    p0_prime = overburden_stress(layers, d + H_sand, cache=cache)
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
    cache: SoilProfileCache | None = None,
) -> float:
    """Метод сдвига Ks (Punching Shear, C.2.19)."""
    B = foundation.B_eff
    L = B
    A = foundation.area_prime

    if H_sand <= 0 or cu_clay <= 0 or phi_sand <= 0:
        return 0.0

    Qv_clay = bearing_capacity_clay(
        layers,
        foundation,
        d + H_sand,
        cache=cache,
    )

    Ks = punch_through_coefficient_Ks(cu_clay, gamma_sand, B, phi_sand)
    tan_phi = np.tan(np.radians(phi_sand))
    sigma_v_avg = gamma_sand * H_sand / 2.0
    perimeter = np.pi * B
    As = perimeter * H_sand
    T_side = Ks * tan_phi * sigma_v_avg * As

    return max(0.0, Qv_clay + T_side)


def _punch_through_backflow_method(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H_sand: float,
    phi_sand: float,
    gamma_sand: float,
    cu_clay: float,
    backflow_height: float = 0.0,
    cache: SoilProfileCache | None = None,
) -> float:
    """Метод C.2.17–C.2.18 для песок→глина (back-flow/no back-flow).

    Для no back-flow:
        Fv = Fv,b - A·H·γ' + 2·(H/B)·(H·γ' + 2·p0')·(Ks·tanφ)·A

    Для full/partial back-flow дополнительно:
        Fv = ... - A·I·γ'

    Где:
      - H: толщина песка между подошвой и кровлей глины
      - I: высота back-flow (0..D), в реализации передаётся как backflow_height
      - p0': бытовое давление на глубине подошвы (depth=d)
      - Fv,b: несущая способность фиктивного основания на кровле глины (без засыпки)
    """
    B = foundation.B_eff
    L = B
    A = foundation.area_prime

    if B <= 0 or A <= 0 or H_sand <= 0 or gamma_sand <= 0 or phi_sand <= 0 or cu_clay <= 0:
        return 0.0

    # p0' на глубине подошвы (в формуле используется для среднего напряжения вдоль поверхности сдвига)
    p0_prime = overburden_stress(layers, d, cache=cache)

    # Fv,b: на кровле глины (C.2.3.1), при D/B=0 (по табл. 2.3-1) и без обратной засыпки в подошве.
    z_clay = d + H_sand
    cu_b = average_cu_below(layers, z_clay, 0.5 * B, cache=cache)
    if cu_b <= 0:
        layer_clay = get_layer_at_depth(layers, z_clay)
        cu_b = (layer_clay.cu if layer_clay and layer_clay.cu is not None else (layer_clay.c if layer_clay else 0.0))
    p0_prime_clay = overburden_stress(layers, z_clay, cache=cache)
    Fv_b = (cu_b * clay_factor_iso_table_23_1(0.0) + p0_prime_clay) * A

    # Ks·tanφ ≈ 3·cu / (B·γ') (C.2.19)
    Ks_tan_phi = 3.0 * cu_clay / (B * gamma_sand)

    term = 2.0 * (H_sand / B) * (H_sand * gamma_sand + 2.0 * p0_prime) * Ks_tan_phi * A
    W_plug = A * H_sand * gamma_sand
    W_backflow = A * max(0.0, backflow_height) * gamma_sand

    return max(0.0, Fv_b - W_plug - W_backflow + term)


def bearing_capacity_punch_through_sand_clay(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    H_sand: float,
    phi_sand: float,
    gamma_sand: float,
    cu_clay: float,
    use_backflow: bool = False,
    cache: SoilProfileCache | None = None,
) -> float:
    """Несущая способность при протыкании: песок над глиной (C.2.19-C.2.20).

    Использует методы и возвращает МИНИМУМ:
    - C.2.17 (no back-flow) и C.2.18 (full/partial back-flow)
    - Load Spread с n=3
    - Load Spread с n=5
    - Ks Shear (punching shear)
    
    По документу: расчёт для n=3 и n=5 с выбором минимума.
    """
    if H_sand <= 0 or cu_clay <= 0:
        return 0.0

    # C.2.17 / C.2.18: оцениваем высоту back-flow как глубину заглубления в пределах текущего слоя
    # (полный back-flow соответствует заполнению полости до уровня кровли слоя).
    backflow_height = 0.0
    if use_backflow:
        # В рамках C.2.18 принимаем full back-flow: I = D
        backflow_height = max(0.0, d)

    Fv_c217_218 = _punch_through_backflow_method(
        layers,
        foundation,
        d,
        H_sand,
        phi_sand,
        gamma_sand,
        cu_clay,
        backflow_height=backflow_height,
        cache=cache,
    )

    # Load Spread для n=3 и n=5, берём минимум (по документу C.2.20)
    Fv_load_spread_n3 = _punch_through_load_spread(
        layers, foundation, d, H_sand, gamma_sand, cu_clay, n=3.0, cache=cache
    )
    Fv_load_spread_n5 = _punch_through_load_spread(
        layers, foundation, d, H_sand, gamma_sand, cu_clay, n=5.0, cache=cache
    )
    Fv_load_spread = min(Fv_load_spread_n3, Fv_load_spread_n5)
    
    # Ks Shear метод
    Fv_ks_shear = _punch_through_ks_shear(
        layers,
        foundation,
        d,
        H_sand,
        phi_sand,
        gamma_sand,
        cu_clay,
        cache=cache,
    )

    candidates = [Fv_c217_218, Fv_load_spread, Fv_ks_shear]
    valid = [v for v in candidates if v > 0]
    return min(valid) if valid else 0.0

# =============================================================================
# Трёхслойный анализ (C.2.3.4.4)
# =============================================================================


def _collect_layer_params(
    layers: list[SoilLayer], d: float, influence_depth: float, max_layers: int = 3
) -> list[LayerWindow]:
    """Собрать параметры слоёв в зоне влияния."""
    z = 0.0
    layer_params: list[LayerWindow] = []
    
    for lyr in layers:
        z_top = z
        z_bot = z + lyr.thickness
        z = z_bot
        
        if z_bot <= d:
            continue
        if z_top >= d + influence_depth:
            break
            
        z_top_clip = max(z_top, d)
        z_bot_clip = min(z_bot, d + influence_depth)
        layer_params.append(
            LayerWindow(
                layer=lyr,
                z_top=z_top_clip,
                z_bot=z_bot_clip,
                H=z_bot_clip - z_top_clip,
                drainage=get_drainage(lyr),
                is_dual=is_dual_drainage(lyr),
                cu=lyr.cu if lyr.cu else lyr.c,
                phi=lyr.phi,
                gamma=lyr.gamma_prime,
            )
        )
        
        if len(layer_params) >= max_layers:
            break
    
    return layer_params


def _two_layer_results(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    top: LayerWindow,
    bottom: LayerWindow,
    use_backfill: bool,
    cache: SoilProfileCache | None,
    include_general_shear: bool,
    allow_dual: bool,
) -> list[float]:
    """Сформировать список кандидатов для двухслойной схемы."""
    results: list[float] = []
    drainages_top = ["drained", "undrained"] if allow_dual and top.is_dual else [top.drainage]
    drainages_bot = ["drained", "undrained"] if allow_dual and bottom.is_dual else [bottom.drainage]

    for d_top in drainages_top:
        if include_general_shear:
            if d_top == "undrained":
                results.append(bearing_capacity_clay(layers, foundation, d, cache=cache))
            else:
                results.append(bearing_capacity_sand(layers, foundation, d, cache=cache))

        for d_bot in drainages_bot:
            if d_top == "drained" and d_bot == "undrained":
                results.append(
                    bearing_capacity_punch_through_sand_clay(
                        layers,
                        foundation,
                        d,
                        top.H,
                        top.phi,
                        top.gamma,
                        bottom.cu,
                        use_backflow=use_backfill,
                        cache=cache,
                    )
                )
            if d_top == "undrained" and d_bot == "undrained":
                if top.cu > bottom.cu:
                    results.append(
                        bearing_capacity_punch_through_clay(
                            layers,
                            foundation,
                            d,
                            top.H,
                            top.cu,
                            bottom.cu,
                            use_backflow=use_backfill,
                            cache=cache,
                        )
                    )
                elif bottom.cu > top.cu:
                    results.append(
                        bearing_capacity_squeezing(
                            layers,
                            foundation,
                            d,
                            top.H,
                            top.cu,
                            use_backflow=use_backfill,
                            cache=cache,
                        )
                    )

    return results


def bearing_capacity_three_layer(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    layer_params: list[LayerWindow],
    use_backfill: bool = False,
    cache: SoilProfileCache | None = None,
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
    results.extend(
        _two_layer_results(
            layers,
            foundation,
            d,
            lp1,
            lp2,
            use_backfill,
            cache,
            include_general_shear=False,
            allow_dual=False,
        )
    )
    
    # === Сценарий 2: Двухслойная система (слои 2-3) ===
    # Глубина эквивалентного основания на кровле слоя 2
    d_equiv = lp2.z_top
    
    # === Сценарий 2: Двухслойная система (слои 2-3) ===
    results.extend(
        _two_layer_results(
            layers,
            foundation,
            d_equiv,
            lp2,
            lp3,
            use_backfill,
            cache,
            include_general_shear=False,
            allow_dual=False,
        )
    )
    
    # === Сценарий 3: Общий сдвиг в однородной толще ===
    if lp1.drainage == "undrained":
        Qv_gs = bearing_capacity_clay(layers, foundation, d, cache=cache)
    else:
        Qv_gs = bearing_capacity_sand(layers, foundation, d, cache=cache)
    results.append(Qv_gs)
    
    # Возвращаем минимум (наиболее консервативная оценка)
    return _min_positive(results)


# =============================================================================
# Итоговая несущая способность Qv и Vl
# =============================================================================


def bearing_capacity_Qv(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    use_backfill: bool = False,
    cache: SoilProfileCache | None = None,
) -> float:
    """Предельная вертикальная несущая способность Qv.

    Для пылеватых грунтов выполняется ДВОЙНОЙ расчёт и берётся МИНИМУМ.
    Для слоистых толщ (2-3 слоя) анализируются все возможные механизмы разрушения.
    """
    layer = get_layer_at_depth(layers, d)
    if layer is None:
        return 0.0

    drainage = get_drainage(layer)
    
    # Собираем параметры слоёв в зоне влияния (1.5·B)
    influence_depth = 1.5 * foundation.B_eff
    layer_params = _collect_layer_params(layers, d, influence_depth, max_layers=3)
    
    # === Однородная толща ===
    if len(layer_params) <= 1:
        if is_dual_drainage(layer):
            Qv_clay = bearing_capacity_clay(layers, foundation, d, cache=cache)
            Qv_sand = bearing_capacity_sand(layers, foundation, d, cache=cache)
            if Qv_clay > 0 and Qv_sand > 0:
                return min(Qv_clay, Qv_sand)
            return Qv_clay if Qv_clay > 0 else Qv_sand

        if drainage == "undrained":
            return bearing_capacity_clay(layers, foundation, d, cache=cache)
        return bearing_capacity_sand(layers, foundation, d, cache=cache)

    # === Трёхслойная система (C.2.3.4.4) ===
    if len(layer_params) >= 3:
        return bearing_capacity_three_layer(
            layers,
            foundation,
            d,
            layer_params,
            use_backfill=use_backfill,
            cache=cache,
        )

    # === Двухслойная система ===
    lp1, lp2 = layer_params[0], layer_params[1]
    results = _two_layer_results(
        layers,
        foundation,
        d,
        lp1,
        lp2,
        use_backfill,
        cache,
        include_general_shear=True,
        allow_dual=True,
    )

    # Возвращаем минимум (консервативная оценка)
    return _min_positive(results)


def bearing_capacity_Vl(
    layers: list[SoilLayer],
    foundation: Foundation,
    d: float,
    F: float = 0.0,
    use_backfill: bool = False,
    cache: SoilProfileCache | None = None,
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
    Qv = bearing_capacity_Qv(
        layers,
        foundation,
        d,
        use_backfill=use_backfill,
        cache=cache,
    )

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
    H_cav = cavity_depth(su_m, gamma, foundation.B_eff, p) if su_m > 0 else 0.0

    Wbf = min_backfill_weight(
        gamma, foundation.area_prime, d, H_cav,
        foundation.V_spud or 0.0, foundation.V_D or 0.0
    )

    return Qv - Wbf + Bs
