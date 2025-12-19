import math

from core.models import Foundation
from core.western.tables import NC_CLAY, shape_factor_clay, shape_factors_sand


def test_foundation_B_eff_is_circle_diameter_from_area_prime():
    # A = π => circle diameter = 2
    foundation = Foundation(area=math.pi)
    assert math.isclose(foundation.B_eff, 2.0, rel_tol=0.0, abs_tol=1e-12)


def test_shape_factor_clay_matches_method_formula():
    # sc = 1 + (1/Nc)·(B/L); for B=L => 1 + 1/Nc
    sc = shape_factor_clay(10.0, 10.0)
    assert sc == 1.0 + (1.0 / NC_CLAY)


def test_shape_factor_sand_sq_uses_tan_phi():
    # sq = 1 + (B/L)·tanφ; for B=L and φ=45° => 2
    _, s_q = shape_factors_sand(10.0, 10.0, 45.0)
    assert s_q == 2.0
