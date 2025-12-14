"""Streamlit приложение для расчёта основания СПБУ."""

import streamlit as st
from ui.state import init_state
from ui.components.soil_editor import render_soil_editor
from ui.components.foundation_form import render_foundation_form
from ui.components.loads_form import render_loads_form
from ui.components.coefficients_form import render_coefficients_form
from ui.components.results_view import render_results
from ui.utils import build_models, export_toml, import_toml
from core.calculator import calculate


def render_sidebar():
    """Боковая панель с настройками."""

    st.header("Настройки")

    # Выбор методики
    method = st.radio(
        "Методика расчёта",
        options=["russian", "western"],
        format_func=lambda x: "Российская (СП)" if x == "russian" else "Западная (SNAME/ISO)",
        index=0 if st.session_state.method == "russian" else 1,
    )
    st.session_state.method = method

    st.divider()

    # Тема графиков
    st.subheader("Тема графиков")

    plot_theme = st.radio(
        "Выберите тему",
        options=["dark", "light"],
        format_func=lambda x: "🌙 Тёмная" if x == "dark" else "☀️ Светлая",
        index=0 if st.session_state.get("plot_theme", "dark") == "dark" else 1,
        help="Тёмная тема подходит для экрана, светлая — для печати и отчётов",
    )
    st.session_state.plot_theme = plot_theme

    st.divider()

    # Параметры расчёта
    st.subheader("Параметры расчёта")

    calc_params = st.session_state.calc_params
    calc_params["d_max"] = st.number_input(
        "d_max, м",
        min_value=5.0,
        max_value=100.0,
        value=calc_params.get("d_max", 20.0),
        step=1.0,
    )
    calc_params["d_step"] = st.number_input(
        "d_step, м",
        min_value=0.01,
        max_value=1.0,
        value=calc_params.get("d_step", 0.1),
        step=0.05,
    )

    if st.session_state.method == "russian":
        st.subheader("Распределение напряжений (σz)")
        calc_params["stress_distribution"] = st.radio(
            "Модель σz под подошвой",
            options=["alpha", "boussinesq"],
            format_func=lambda x: "α (СП 22, табл. 5.8)" if x == "alpha" else "Буссинеск (формула)",
            index=0 if calc_params.get("stress_distribution", "alpha") == "alpha" else 1,
            help="Влияет на расчёт Hc и осадок (только российская методика).",
        )

    st.session_state.calc_params = calc_params

    st.divider()

    # Импорт/Экспорт
    st.subheader("Импорт / Экспорт")

    # Импорт
    uploaded_file = st.file_uploader(
        "Импорт TOML",
        type=["toml"],
        help="Загрузить конфигурацию из файла",
    )

    if uploaded_file is not None:
        # Проверяем, что файл не был уже загружен
        file_id = uploaded_file.file_id
        if "last_uploaded_file_id" not in st.session_state or st.session_state.last_uploaded_file_id != file_id:
            try:
                new_state = import_toml(uploaded_file.read())
                # Обновляем все поля session_state
                for key, value in new_state.items():
                    st.session_state[key] = value
                # Очищаем результат расчёта при загрузке новых данных
                st.session_state.result = None
                # Очищаем внутреннее состояние data_editor для обновления таблицы
                if "layers_editor" in st.session_state:
                    del st.session_state["layers_editor"]
                # Сохраняем ID файла
                st.session_state.last_uploaded_file_id = file_id
                st.success("✅ Данные успешно загружены из TOML!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Ошибка загрузки TOML: {e}")

    # Экспорт
    toml_content = export_toml({
        "method": st.session_state.method,
        "layers": st.session_state.layers,
        "foundation": st.session_state.foundation,
        "loads": st.session_state.loads,
        "coefficients": st.session_state.coefficients,
        "calc_params": st.session_state.calc_params,
    })

    st.download_button(
        "📥 Экспорт TOML",
        data=toml_content,
        file_name="spbu_config.toml",
        mime="text/plain",
    )


def run_calculation():
    """Запуск расчёта."""

    try:
        layers, foundation, coef = build_models({
            "layers": st.session_state.layers,
            "foundation": st.session_state.foundation,
            "coefficients": st.session_state.coefficients,
        })

        result = calculate(
            layers=layers,
            foundation=foundation,
            coef=coef,
            F_operation=st.session_state.loads["operation"],
            F_preload=st.session_state.loads["preload"],
            d_max=st.session_state.calc_params["d_max"],
            d_step=st.session_state.calc_params["d_step"],
            method=st.session_state.method,
            stress_distribution=st.session_state.calc_params.get("stress_distribution", "alpha"),
        )

        st.session_state.result = result
        st.success("Расчёт выполнен!")

    except Exception as e:
        st.error(f"Ошибка расчёта: {e}")
        st.session_state.result = None


def main():
    st.set_page_config(
        page_title="Расчёт основания СПБУ",
        page_icon="🏗️",
        layout="wide"
    )

    init_state()

    # Sidebar
    with st.sidebar:
        render_sidebar()

    # Main area
    st.title("Расчёт основания СПБУ")

    render_soil_editor()

    col1, col2 = st.columns(2)
    with col1:
        render_foundation_form()
    with col2:
        render_loads_form()

    with st.expander("Коэффициенты надёжности"):
        render_coefficients_form()

    if st.button("Рассчитать", type="primary", width="stretch"):
        run_calculation()

    if st.session_state.get("result"):
        render_results()


if __name__ == "__main__":
    main()
