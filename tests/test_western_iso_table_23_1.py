from core.western.tables import clay_factor_iso_table_23_1


def test_iso_table_23_1_exact_nodes():
    assert clay_factor_iso_table_23_1(0.0) == 6.0
    assert clay_factor_iso_table_23_1(0.1) == 6.3
    assert clay_factor_iso_table_23_1(0.25) == 6.6
    assert clay_factor_iso_table_23_1(0.5) == 7.0
    assert clay_factor_iso_table_23_1(1.0) == 7.7
    assert clay_factor_iso_table_23_1(2.5) == 9.0


def test_iso_table_23_1_interpolation_and_clamping():
    # Clamp
    assert clay_factor_iso_table_23_1(-1.0) == 6.0
    assert clay_factor_iso_table_23_1(10.0) == 9.0
    # Midpoint between 0.0 (6.0) and 0.1 (6.3) => 6.15
    assert clay_factor_iso_table_23_1(0.05) == 6.15

