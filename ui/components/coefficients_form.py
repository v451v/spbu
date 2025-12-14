"""Форма коэффициентов надёжности."""

import streamlit as st


def render_coefficients_form():
    """Форма коэффициентов надёжности."""

    coef = st.session_state.coefficients
    method = st.session_state.method

    col1, col2, col3 = st.columns(3)

    with col1:
        coef["gamma_n"] = st.number_input(
            "γn (надёжность)",
            min_value=1.0,
            max_value=2.0,
            value=coef.get("gamma_n", 1.25),
            step=0.05,
            help="Коэффициент надёжности по ответственности",
        )
        coef["gamma_lc"] = st.number_input(
            "γlc (нагрузки)",
            min_value=0.5,
            max_value=2.0,
            value=coef.get("gamma_lc", 1.0),
            step=0.1,
        )

    with col2:
        coef["gamma_c1"] = st.number_input(
            "γc1 (условия 1)",
            min_value=0.5,
            max_value=2.0,
            value=coef.get("gamma_c1", 1.0),
            step=0.1,
        )
        coef["gamma_c2"] = st.number_input(
            "γc2 (условия 2)",
            min_value=0.5,
            max_value=2.0,
            value=coef.get("gamma_c2", 1.0),
            step=0.1,
        )

    with col3:
        coef["k"] = st.number_input(
            "k (источник)",
            min_value=1.0,
            max_value=1.1,
            value=coef.get("k", 1.0),
            step=0.1,
            help="1.0 — испытания, 1.1 — таблицы",
        )

        if method == "western":
            coef["use_backfill"] = st.checkbox(
                "Учитывать обратную засыпку",
                value=coef.get("use_backfill", False),
            )

    st.session_state.coefficients = coef
