from core.helpers import additional_stress_boussinesq
from core.models import Foundation, SoilLayer
from core.russian.settlement import settlement, vertical_stress
from core.russian.tables import stress_coefficient_alpha


def test_vertical_stress_alpha_matches_table_for_eta_1():
    foundation = Foundation(area=100.0, e_x=0.0, e_y=0.0)  # b=l=10
    z = 4.0
    p0 = 123.0
    expected = stress_coefficient_alpha(z, foundation.b_prime) * p0
    got = vertical_stress(p0, foundation, z, stress_distribution="alpha")
    assert got == expected


def test_vertical_stress_boussinesq_differs_from_alpha():
    foundation = Foundation(area=100.0, e_x=0.0, e_y=0.0)  # b=l=10
    z = 10.0
    p0 = 1.0
    alpha_val = stress_coefficient_alpha(z, foundation.b_prime) * p0
    bouss_val = additional_stress_boussinesq(p0, foundation.b_prime, foundation.l_prime, z)
    got = vertical_stress(p0, foundation, z, stress_distribution="boussinesq")
    assert got == bouss_val
    assert abs(bouss_val - alpha_val) > 0.01


def test_settlement_toggle_changes_result():
    layers = [
        SoilLayer(
            name="Test soil",
            thickness=50.0,
            gamma_prime=10.0,
            phi=30.0,
            c=0.0,
            E=25.0,
        )
    ]
    foundation = Foundation(area=100.0, e_x=0.0, e_y=0.0)  # b=l=10

    d = 0.0
    p = 100.0  # кПа

    s_alpha = settlement(layers, foundation, d, p, stress_distribution="alpha")
    s_bouss = settlement(layers, foundation, d, p, stress_distribution="boussinesq")

    assert s_alpha > 0
    assert s_bouss > 0
    assert s_alpha != s_bouss
