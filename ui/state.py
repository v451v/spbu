"""Управление состоянием Streamlit приложения."""

import streamlit as st


def init_state():
    """Инициализация session_state значениями по умолчанию."""

    defaults = {
        # Методика
        "method": "russian",

        # Тема графиков
        "plot_theme": "dark",

        # Слои грунта (список словарей)
        "layers": [
            {
                "name": "Песок мелкий",
                "thickness": 5.0,
                "gamma_prime": 10.0,
                "phi": 30.0,
                "c": 0.0,
                "E": 25.0,
                "soil_type": "sand_fine",
                # Опциональные поля для II группы ПС
                "phi_II": None,
                "c_II": None,
                "gamma_prime_II": None,
                # Западная методика
                "cu": None,
                "drainage": None,
            }
        ],

        # Фундамент
        "foundation": {
            "area": 154.0,
            "e_x": 0.0,
            "e_y": 0.0,
            # Западная методика
            "V_spud": None,
            "V_D": None,
            "D_eff": None,
            "beta": None,
        },

        # Нагрузки
        "loads": {
            "operation": 57290.0,
            "preload": 76700.0,
        },

        # Коэффициенты
        "coefficients": {
            "gamma_n": 1.25,
            "gamma_lc": 1.0,
            "gamma_c1": 1.0,
            "gamma_c2": 1.0,
            "k": 1.0,
            "use_backfill": False,
        },

        # Параметры расчёта
        "calc_params": {
            "d_max": 20.0,
            "d_step": 0.1,
            "stress_distribution": "alpha",  # russian: "alpha" | "boussinesq"
        },

        # Результат расчёта (None до первого расчёта)
        "result": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_state(key: str):
    """Получить значение из state."""
    return st.session_state.get(key)


def set_state(key: str, value):
    """Установить значение в state."""
    st.session_state[key] = value
