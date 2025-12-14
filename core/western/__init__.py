"""Западная методика расчёта основания СПБУ (SNAME/ISO 19905-1).

Источники:
- SNAME 5-5A
- ISO 19905-1 / ГОСТ Р 59997
- InSafeJIP

Использование:
    from core.western import (
        bearing_capacity_Qv,
        bearing_capacity_Vl,
        penetration_curve,
        find_equilibrium_depth,
        has_punch_through_risk,
    )
"""

from .bearing import (
    bearing_capacity_clay,
    bearing_capacity_punch_through_clay,
    bearing_capacity_punch_through_sand_clay,
    bearing_capacity_Qv,
    bearing_capacity_sand,
    bearing_capacity_squeezing,
    bearing_capacity_Vl,
    detect_failure_mechanism,
)
from core.helpers import (
    buoyancy_force,
    cavity_depth,
    cavity_depth_ratio,
    get_drainage,
    is_dual_drainage,
    min_backfill_weight,
    spud_cone_volume,
)
from .penetration import (
    calculate_point,
    find_all_equilibrium_depths,
    find_equilibrium_depth,
    has_punch_through_risk,
    penetration_curve,
)

__all__ = [
    # Helpers
    "get_drainage",
    "is_dual_drainage",
    "spud_cone_volume",
    "cavity_depth_ratio",
    "cavity_depth",
    "min_backfill_weight",
    "buoyancy_force",
    # Bearing capacity
    "bearing_capacity_clay",
    "bearing_capacity_sand",
    "bearing_capacity_squeezing",
    "bearing_capacity_punch_through_clay",
    "bearing_capacity_punch_through_sand_clay",
    "detect_failure_mechanism",
    "bearing_capacity_Qv",
    "bearing_capacity_Vl",
    # Penetration
    "calculate_point",
    "penetration_curve",
    "find_equilibrium_depth",
    "find_all_equilibrium_depths",
    "has_punch_through_risk",
]
