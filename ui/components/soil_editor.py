"""Редактор слоёв грунта."""

import streamlit as st
import pandas as pd


def _num_col(label: str, min_v: float, max_v: float = None, required: bool = False, help: str = None):
    """Фабрика для NumberColumn с общими параметрами."""
    return st.column_config.NumberColumn(
        label, min_value=min_v, max_value=max_v,
        step=0.00001, format="%.5g", required=required, help=help,
    )


# Типы грунтов
_SOIL_TYPES = [
    "sand_fine", "sand_medium", "sand_coarse",
    "silt", "sandy_silt", "silty_sand",
    "clay_soft", "clay_plastic", "clay_stiff",
    "gravel", "rock",
]

# Базовые колонки (всегда видимые)
_BASE_COLUMNS = {
    "name": st.column_config.TextColumn("Название", width="medium", required=True),
    "thickness": _num_col("Мощность, м", 0.1, 100.0, required=True),
    "gamma_prime": _num_col("γ', кН/м³", 1.0, 30.0, required=True),
    "phi": _num_col("φ, °", 0.0, 45.0, required=True),
    "c": _num_col("c, кПа", 0.0, 500.0),
    "E": _num_col("E, МПа", 0.1, 1000.0),
    "soil_type": st.column_config.SelectboxColumn("Тип грунта", options=_SOIL_TYPES, width="medium"),
}

# Дополнительные колонки для западной методики
_WESTERN_COLUMNS = {
    "cu": _num_col("cu, кПа", 0.0, 500.0, help="Недренированная прочность (для глин)"),
    "drainage": st.column_config.SelectboxColumn("Дренирование", options=["drained", "undrained"]),
}

# Колонки для II группы ПС (российская методика)
_GROUP_II_COLUMNS = {
    "phi_II": _num_col("φ_II, °", 0.0, 45.0, help="Угол трения для II группы ПС"),
    "c_II": _num_col("c_II, кПа", 0.0, help="Сцепление для II группы ПС"),
}


def render_soil_editor():
    """Редактор слоёв грунта с использованием st.data_editor."""
    st.subheader("Слои грунта")

    method = st.session_state.method
    extra_cols = _WESTERN_COLUMNS if method == "western" else _GROUP_II_COLUMNS
    column_config = {**_BASE_COLUMNS, **extra_cols}
    visible_columns = list(_BASE_COLUMNS.keys()) + list(extra_cols.keys())

    # Преобразуем в DataFrame, добавляя недостающие колонки
    df = pd.DataFrame(st.session_state.layers)
    for col in visible_columns:
        if col not in df.columns:
            df[col] = None

    edited_df = st.data_editor(
        df[visible_columns],
        column_config=column_config,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="layers_editor",
    )

    # Сохраняем изменения в state (заменяем NaN на None для Pydantic)
    st.session_state.layers = [
        {k: (None if pd.isna(v) else v) for k, v in layer.items()}
        for layer in edited_df.to_dict("records")
    ]

    st.caption(f"Суммарная мощность: {edited_df['thickness'].sum():.1f} м")
