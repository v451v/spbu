"""Форма нагрузок."""

import streamlit as st


def render_loads_form():
    """Форма нагрузок."""

    st.subheader("Нагрузки")

    loads = st.session_state.loads

    loads["operation"] = st.number_input(
        "Эксплуатационная нагрузка, кН",
        min_value=0.0,
        value=loads.get("operation", 57290.0),
        step=100.0,
        format="%.0f",
    )

    loads["preload"] = st.number_input(
        "Преднагрузка, кН",
        min_value=0.0,
        value=loads.get("preload", 76700.0),
        step=100.0,
        format="%.0f",
    )

    # Информация в МН
    st.caption(
        f"Эксплуатация: {loads['operation']/1000:.1f} МН, "
        f"Преднагрузка: {loads['preload']/1000:.1f} МН"
    )

    st.session_state.loads = loads
