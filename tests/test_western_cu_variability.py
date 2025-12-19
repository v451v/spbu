import math

import pytest

from core.helpers import cu_variability_ratio
from core.models import Foundation, SoilLayer
from core.western.bearing import bearing_capacity_clay
from core.western.tables import clay_factor_iso_table_23_1


def _make_layers(cu_values, thickness):
    return [
        SoilLayer(
            name=f"layer_{i}",
            thickness=thickness,
            gamma_prime=10.0,
            phi=0.0,
            c=0.0,
            cu=cu,
            drainage="undrained",
        )
        for i, cu in enumerate(cu_values)
    ]


def test_cu_variability_ratio_threshold():
    layers = _make_layers([10.0, 30.0], thickness=1.0)
    ratio = cu_variability_ratio(layers, d=0.0, z_thickness=2.0)
    assert ratio > 0.5


def test_cu_variability_ratio_below_threshold():
    layers = _make_layers([10.0, 14.0], thickness=1.0)
    ratio = cu_variability_ratio(layers, d=0.0, z_thickness=2.0)
    assert ratio <= 0.5


@pytest.mark.parametrize(
    ("cu_values", "expected_cu"),
    [
        ([10.0, 30.0], 20.0),  # variability > 50% -> average over B
        ([10.0, 14.0], 10.0),  # variability <= 50% -> average over B/2
    ],
)
def test_bearing_capacity_clay_uses_variability_rule(cu_values, expected_cu):
    layers = _make_layers(cu_values, thickness=1.0)
    foundation = Foundation(area=math.pi)  # B_eff = 2.0
    d = 0.0
    ncsdc = clay_factor_iso_table_23_1(0.0)
    expected = (expected_cu * ncsdc) * foundation.area_prime
    assert bearing_capacity_clay(layers, foundation, d) == pytest.approx(expected)
