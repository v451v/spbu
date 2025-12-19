import pytest

from core.models import Coefficients, Foundation, PointResult, SoilLayer
from core.western import penetration
from core.western import bearing


def _dummy_inputs():
    layers = [SoilLayer(name="dummy", thickness=1.0, gamma_prime=10.0, phi=0.0, c=0.0, cu=10.0)]
    foundation = Foundation(area=100.0)
    coef = Coefficients()
    return layers, foundation, coef


@pytest.mark.parametrize(
    ("eta1_values", "expected_d"),
    [
        # Последняя неустойчивость на индексе 2 => возвращаем первую безопасную точку после неё (idx 3)
        ([1.2, 0.9, 1.1, 0.95, 0.9], 0.4),
        # Провалов нет => первая безопасная точка
        ([0.8, 0.7, 0.6], 0.1),
    ],
)
def test_find_equilibrium_depth_returns_min_stable_depth(monkeypatch, eta1_values, expected_d):
    curve = [
        PointResult(d=0.1 * (i + 1), Nu=1.0, R=1.0, p=1.0, eta1=eta, eta2=0.5, layer_name="x")
        for i, eta in enumerate(eta1_values)
    ]

    def _fake_curve(*_args, **_kwargs):
        return curve

    monkeypatch.setattr(penetration, "penetration_curve", _fake_curve)

    layers, foundation, coef = _dummy_inputs()
    res = penetration.find_equilibrium_depth(layers, foundation, coef, F=1.0, d_max=1.0, d_step=0.1)
    assert res is not None
    assert res.d == expected_d


def test_find_equilibrium_depth_none_when_never_safe(monkeypatch):
    curve = [
        PointResult(d=0.1 * (i + 1), Nu=1.0, R=1.0, p=1.0, eta1=1.01, eta2=0.5, layer_name="x")
        for i in range(5)
    ]

    def _fake_curve(*_args, **_kwargs):
        return curve

    monkeypatch.setattr(penetration, "penetration_curve", _fake_curve)

    layers, foundation, coef = _dummy_inputs()
    res = penetration.find_equilibrium_depth(layers, foundation, coef, F=1.0, d_max=1.0, d_step=0.1)
    assert res is None


def test_c217_c218_backflow_method_basic():
    layers = [
        SoilLayer(name="sand", thickness=10.0, gamma_prime=10.0, phi=30.0, c=0.0, drainage="drained"),
        SoilLayer(name="clay", thickness=10.0, gamma_prime=8.0, phi=0.0, c=0.0, cu=50.0, drainage="undrained"),
    ]
    foundation = Foundation(area=100.0)

    # Выбираем d=2м внутри песка и H_sand=8м до кровли глины
    val_no_backflow = bearing._punch_through_backflow_method(
        layers,
        foundation,
        d=2.0,
        H_sand=8.0,
        phi_sand=30.0,
        gamma_sand=10.0,
        cu_clay=50.0,
        backflow_height=0.0,
    )
    val_with_backflow = bearing._punch_through_backflow_method(
        layers,
        foundation,
        d=2.0,
        H_sand=8.0,
        phi_sand=30.0,
        gamma_sand=10.0,
        cu_clay=50.0,
        backflow_height=2.0,
    )

    assert val_no_backflow > 0
    assert val_with_backflow > 0
    assert val_with_backflow < val_no_backflow
