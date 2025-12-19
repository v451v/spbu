import pytest

from core.helpers import (
    average_cu_below,
    average_sand_props_below,
    build_profile_cache,
    overburden_stress,
)
from core.models import SoilLayer


def _layers():
    return [
        SoilLayer(name="layer1", thickness=2.0, gamma_prime=10.0, phi=30.0, c=0.0, cu=20.0),
        SoilLayer(name="layer2", thickness=3.0, gamma_prime=12.0, phi=35.0, c=0.0, cu=40.0),
    ]


@pytest.mark.parametrize("depth", [0.0, 1.0, 2.0, 4.0, 6.0])
def test_overburden_stress_cache_matches_uncached(depth):
    layers = _layers()
    cache = build_profile_cache(layers)
    assert overburden_stress(layers, depth) == pytest.approx(
        overburden_stress(layers, depth, cache=cache)
    )


@pytest.mark.parametrize("d,z", [(0.0, 1.0), (1.0, 2.0), (2.0, 2.0), (4.0, 2.0)])
def test_average_cu_below_cache_matches_uncached(d, z):
    layers = _layers()
    cache = build_profile_cache(layers)
    assert average_cu_below(layers, d, z) == pytest.approx(
        average_cu_below(layers, d, z, cache=cache)
    )


@pytest.mark.parametrize("d,z", [(0.0, 1.0), (1.0, 2.0), (2.0, 2.0), (4.0, 2.0)])
def test_average_sand_props_cache_matches_uncached(d, z):
    layers = _layers()
    cache = build_profile_cache(layers)
    phi_ref, gamma_ref = average_sand_props_below(layers, d, z)
    phi_cached, gamma_cached = average_sand_props_below(layers, d, z, cache=cache)
    assert phi_ref == pytest.approx(phi_cached)
    assert gamma_ref == pytest.approx(gamma_cached)
