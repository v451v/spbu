"""Отображение результатов расчёта."""

import streamlit as st
import pandas as pd
from plot import PublicationPlotter
from core.models import SoilLayer, Foundation


def render_results():
    """Отображение результатов расчёта."""

    result = st.session_state.result
    if result is None:
        return

    method = st.session_state.method

    st.divider()
    st.subheader("Результаты расчёта")

    # Основные результаты
    col1, col2, col3 = st.columns(3)

    with col1:
        if result.d_operation:
            st.metric(
                "d* (эксплуатация)",
                f"{result.d_operation:.2f} м",
            )
        else:
            st.warning("Равновесие не найдено (эксплуатация)")

    with col2:
        if result.d_preload:
            st.metric(
                "d* (преднагрузка)",
                f"{result.d_preload:.2f} м",
            )
        else:
            st.warning("Равновесие не найдено (преднагрузка)")

    with col3:
        if method == "western" and result.punch_through_risk:
            st.error("⚠️ Риск punch-through!")
        elif method == "western":
            st.success("✓ Без риска punch-through")

    # График
    st.subheader("График пенетрации")
    fig = _build_plot()
    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displaylogo": False,
            "toImageButtonOptions": {
                "format": "png",
                "scale": 2,  # повышенное качество PNG из modebar
                "filename": "penetration",
            },
        },
    )

    # Таблица результатов
    with st.expander("Таблица кривой пенетрации"):
        df = pd.DataFrame([
            {
                "d, м": r.d,
                "Nu, кН": r.Nu,
                "R, кПа": r.R,
                "p, кПа": r.p,
                "η1": f"{r.eta1:.3f}",
                "η2": f"{r.eta2:.3f}",
                "Слой": r.layer_name,
                "Безопасно": "✓" if r.is_safe else "✗",
            }
            for r in result.curve
        ])
        st.dataframe(df, width="stretch", hide_index=True)


def _build_plot():
    """Построить график используя существующий PublicationPlotter."""

    result = st.session_state.result
    method = st.session_state.method
    foundation = st.session_state.foundation
    loads = st.session_state.loads
    coef = st.session_state.coefficients
    layers = st.session_state.layers

    # Коэффициенты для отрисовки
    if method == "russian":
        gamma_n = coef["gamma_n"]
        gamma_c = coef["gamma_c1"] * coef["gamma_c2"]
    else:
        gamma_n = 1.0
        gamma_c = 1.0

    # Используем тему из настроек
    theme = st.session_state.get("plot_theme", "dark")
    plotter = PublicationPlotter(methodology=method, theme=theme)

    plotter.plot_curves(results=result.curve, gamma_n=gamma_n, gamma_c=gamma_c)

    # Используем Pydantic-модель для расчёта приведённых размеров
    f = Foundation(**{k: v for k, v in foundation.items() if v is not None and v != 0} | {"area": foundation["area"]})

    plotter.add_load_lines(
        F_op=loads["operation"],
        F_pre=loads["preload"],
        area=f.area_prime,
        b=f.b_prime,
        l=f.l_prime
    )

    # Конвертируем слои в объекты SoilLayer
    layer_objects = [SoilLayer(**layer) for layer in layers]
    plotter.add_layers(layer_objects)

    plotter.add_critical_depth_annotations(
        d_op=result.d_operation,
        d_pre=result.d_preload
    )

    plotter.add_equilibrium_markers(
        results=result.curve,
        F=loads["operation"],
        area=f.area_prime,
        gamma_n=gamma_n,
        gamma_c=gamma_c,
    )

    if method == "western":
        plotter.add_punch_through_zones(result.curve, loads["operation"])

    return plotter.get_figure()
