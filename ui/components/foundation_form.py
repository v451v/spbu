"""Форма параметров фундамента."""

import streamlit as st


def render_foundation_form():
    """Форма параметров фундамента."""

    st.subheader("Фундамент")

    foundation = st.session_state.foundation
    method = st.session_state.method

    def _float_or(default: float, value) -> float:
        if value is None:
            return float(default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    # Основные параметры
    foundation["area"] = st.number_input(
        "Площадь подошвы, м²",
        min_value=1.0,
        max_value=1000.0,
        value=_float_or(154.0, foundation.get("area", 154.0)),
        step=1.0,
        help="Для круглого башмака: A = πD²/4",
    )

    col1, col2 = st.columns(2)
    with col1:
        foundation["e_x"] = st.number_input(
            "Эксцентриситет e_x, м",
            min_value=0.0,
            max_value=10.0,
            value=_float_or(0.0, foundation.get("e_x", 0.0)),
            step=0.1,
        )
    with col2:
        foundation["e_y"] = st.number_input(
            "Эксцентриситет e_y, м",
            min_value=0.0,
            max_value=10.0,
            value=_float_or(0.0, foundation.get("e_y", 0.0)),
            step=0.1,
        )

    # Дополнительные параметры для западной методики
    if method == "western":
        st.markdown("**Параметры башмака (западная методика)**")

        col1, col2 = st.columns(2)
        with col1:
            foundation["V_spud"] = st.number_input(
                "V_spud, м³",
                min_value=0.0,
                value=_float_or(0.0, foundation.get("V_spud")),
                step=1.0,
                help="Полный объём башмака",
            )
            foundation["D_eff"] = st.number_input(
                "D_eff, м",
                min_value=0.0,
                value=_float_or(0.0, foundation.get("D_eff")),
                step=0.1,
                help="Эффективный диаметр шипа",
            )
        with col2:
            foundation["V_D"] = st.number_input(
                "V_D, м³",
                min_value=0.0,
                value=_float_or(0.0, foundation.get("V_D")),
                step=1.0,
                help="Объём ниже уровня макс. площади",
            )
            foundation["beta"] = st.number_input(
                "β, °",
                min_value=0.0,
                max_value=180.0,
                value=_float_or(60.0, foundation.get("beta")),
                step=1.0,
                help="Угол конуса шипа",
            )

    # Вычисляемые параметры (информационно)
    b = foundation["area"] ** 0.5
    b_prime = max(0.01, b - 2 * foundation["e_x"])
    l_prime = max(0.01, b - 2 * foundation["e_y"])
    area_prime = b_prime * l_prime

    st.caption(f"b = {b:.2f} м, b' = {b_prime:.2f} м, A' = {area_prime:.1f} м²")

    st.session_state.foundation = foundation
