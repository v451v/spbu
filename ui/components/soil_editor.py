"""Редактор слоёв грунта — простая реализация на отдельных виджетах."""

import streamlit as st
import uuid


_SOIL_TYPES = [
    "sand_fine", "sand_medium", "sand_coarse",
    "silt", "sandy_silt", "silty_sand",
    "clay_soft", "clay_plastic", "clay_stiff",
    "gravel", "rock",
]

_SOIL_TYPE_LABELS = {
    "sand_fine": "Песок мелкий",
    "sand_medium": "Песок средний",
    "sand_coarse": "Песок крупный",
    "silt": "Супесь",
    "sandy_silt": "Супесь песчанистая",
    "silty_sand": "Песок пылеватый",
    "clay_soft": "Глина мягкая",
    "clay_plastic": "Глина пластичная",
    "clay_stiff": "Глина твёрдая",
    "gravel": "Гравий",
    "rock": "Скала",
}


def _new_layer() -> dict:
    """Создаёт новый слой с уникальным ID."""
    return {
        "_id": str(uuid.uuid4())[:8],  # Уникальный ID для ключей виджетов
        "name": "Новый слой",
        "thickness": 1.0,
        "gamma_prime": 10.0,
        "phi": 25.0,
        "c": 0.0,
        "E": 20.0,
        "soil_type": "sand_medium",
        "cu": None,  # None для западной методики
        "drainage": "drained",
        "phi_II": None,  # None — Pydantic возьмёт из I группы
        "c_II": None,
    }


def _ensure_layer_id(layer: dict) -> dict:
    """Гарантирует наличие _id у слоя."""
    if "_id" not in layer:
        layer["_id"] = str(uuid.uuid4())[:8]
    return layer


def _parse_float(value: str, default: float = 0.0, min_val: float = None, max_val: float = None) -> tuple[float, bool]:
    """
    Парсит строку в float, поддерживает запятую как разделитель.
    Возвращает (значение, is_valid).
    """
    if not value or not value.strip():
        return default, True

    try:
        cleaned = value.strip().replace(",", ".")
        result = float(cleaned)

        if min_val is not None and result < min_val:
            return min_val, False
        if max_val is not None and result > max_val:
            return max_val, False

        return result, True
    except ValueError:
        return default, False


def _float_input(label: str, value: float, key: str, min_val: float = None, max_val: float = None, help: str = None) -> float:
    """
    Поле ввода float с поддержкой запятой.
    Автоматически нормализует запятую в точку.
    """
    # Инициализируем session_state если ключа нет
    if key not in st.session_state:
        display = f"{value:.4g}" if value is not None else ""
        st.session_state[key] = display
    else:
        # Нормализуем запятую в точку
        current = st.session_state[key]
        if "," in current:
            parsed, _ = _parse_float(current, default=value or 0.0, min_val=min_val, max_val=max_val)
            st.session_state[key] = f"{parsed:.4g}"

    text = st.text_input(
        label,
        key=key,
        help=help,
    )

    parsed, is_valid = _parse_float(text, default=value or 0.0, min_val=min_val, max_val=max_val)

    if not is_valid and text.strip():
        if min_val is not None and max_val is not None:
            st.caption(f"⚠️ {min_val}–{max_val}")
        elif min_val is not None:
            st.caption(f"⚠️ ≥ {min_val}")

    return parsed


def _float_input_optional(label: str, value: float | None, key: str, min_val: float = None, max_val: float = None, help: str = None) -> float | None:
    """
    Поле ввода float с поддержкой None (пустое поле = None).
    """
    if key not in st.session_state:
        display = f"{value:.4g}" if value is not None else ""
        st.session_state[key] = display
    else:
        current = st.session_state[key]
        if current and "," in current:
            parsed, _ = _parse_float(current, default=0.0, min_val=min_val, max_val=max_val)
            st.session_state[key] = f"{parsed:.4g}"

    text = st.text_input(
        label,
        key=key,
        help=help,
    )

    if not text or not text.strip():
        return None

    parsed, is_valid = _parse_float(text, default=0.0, min_val=min_val, max_val=max_val)

    if not is_valid:
        if min_val is not None and max_val is not None:
            st.caption(f"⚠️ {min_val}–{max_val}")

    return parsed


def _render_layer(layer: dict, method: str, layer_num: int) -> dict | None:
    """Рендерит один слой. Возвращает обновлённый слой или None если удалён."""

    layer = _ensure_layer_id(layer)
    lid = layer["_id"]  # Уникальный ID для ключей

    with st.expander(f"Слой {layer_num}: {layer.get('name', 'Без названия')}", expanded=True):
        col_del, col_name = st.columns([1, 5])

        with col_del:
            if st.button("🗑️", key=f"del_{lid}", help="Удалить слой"):
                return None

        with col_name:
            # Для текстового поля тоже нужна инициализация
            name_key = f"name_{lid}"
            if name_key not in st.session_state:
                st.session_state[name_key] = layer.get("name", "")

            name = st.text_input(
                "Название",
                key=name_key,
                label_visibility="collapsed",
                placeholder="Название слоя",
            )

        # Основные параметры
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            thickness = _float_input(
                "Мощность, м",
                value=layer.get("thickness") or 1.0,
                key=f"thickness_{lid}",
                min_val=0.0,
                max_val=100.0,
            )

        with c2:
            gamma_prime = _float_input(
                "γ', кН/м³",
                value=layer.get("gamma_prime") or 10.0,
                key=f"gamma_{lid}",
                min_val=0.0,
                max_val=30.0,
            )

        with c3:
            phi = _float_input(
                "φ, °",
                value=layer.get("phi") or 0.0,
                key=f"phi_{lid}",
                min_val=0.0,
                max_val=45.0,
            )

        with c4:
            c = _float_input(
                "c, кПа",
                value=layer.get("c") or 0.0,
                key=f"c_{lid}",
                min_val=0.0,
                max_val=500.0,
            )

        c5, c6, c7, c8 = st.columns(4)

        with c5:
            E = _float_input(
                "E, МПа",
                value=layer.get("E") or 20.0,
                key=f"E_{lid}",
                min_val=0.0,
                max_val=1000.0,
            )

        with c6:
            soil_type_key = f"soil_type_{lid}"
            current_soil = layer.get("soil_type", "sand_medium")

            if soil_type_key not in st.session_state:
                st.session_state[soil_type_key] = current_soil

            soil_type = st.selectbox(
                "Тип грунта",
                options=_SOIL_TYPES,
                format_func=lambda x: _SOIL_TYPE_LABELS.get(x, x),
                key=soil_type_key,
            )

        # Дополнительные поля в зависимости от методики
        if method == "western":
            with c7:
                cu = _float_input_optional(
                    "cu, кПа",
                    value=layer.get("cu"),
                    key=f"cu_{lid}",
                    min_val=0.0,
                    max_val=500.0,
                    help="Недренированная прочность (пусто = не задано)",
                )

            with c8:
                drainage_opts = ["drained", "undrained"]
                drainage_key = f"drainage_{lid}"
                current_drainage = layer.get("drainage", "drained")

                if drainage_key not in st.session_state:
                    st.session_state[drainage_key] = current_drainage

                drainage = st.selectbox(
                    "Дренирование",
                    options=drainage_opts,
                    format_func=lambda x: "Дренированный" if x == "drained" else "Недренированный",
                    key=drainage_key,
                )

            return {
                "_id": lid,
                "name": name,
                "thickness": thickness,
                "gamma_prime": gamma_prime,
                "phi": phi,
                "c": c,
                "E": E,
                "soil_type": soil_type,
                "cu": cu,
                "drainage": drainage,
            }
        else:
            with c7:
                phi_II = _float_input_optional(
                    "φ_II, °",
                    value=layer.get("phi_II"),
                    key=f"phi_II_{lid}",
                    min_val=0.0,
                    max_val=45.0,
                    help="Угол трения II гр. ПС (пусто = взять из I группы)",
                )

            with c8:
                c_II = _float_input_optional(
                    "c_II, кПа",
                    value=layer.get("c_II"),
                    key=f"c_II_{lid}",
                    min_val=0.0,
                    max_val=500.0,
                    help="Сцепление II гр. ПС (пусто = взять из I группы)",
                )

            return {
                "_id": lid,
                "name": name,
                "thickness": thickness,
                "gamma_prime": gamma_prime,
                "phi": phi,
                "c": c,
                "E": E,
                "soil_type": soil_type,
                "phi_II": phi_II,
                "c_II": c_II,
            }


def clear_soil_editor_keys():
    """Очищает все ключи soil_editor из session_state. Вызывать при импорте TOML."""
    keys_to_delete = [
        key for key in st.session_state.keys()
        if any(key.startswith(prefix) for prefix in [
            "del_", "name_", "thickness_", "gamma_", "phi_", "c_", "E_",
            "soil_type_", "cu_", "drainage_", "phi_II_", "c_II_"
        ])
    ]
    for key in keys_to_delete:
        del st.session_state[key]


def render_soil_editor():
    """Редактор слоёв грунта."""
    st.subheader("Слои грунта")

    method = st.session_state.method
    layers = st.session_state.layers

    # Если слоёв нет — добавляем один по умолчанию
    if not layers:
        layers = [_new_layer()]

    # Рендерим каждый слой
    new_layers = []
    for idx, layer in enumerate(layers):
        result = _render_layer(layer, method, idx + 1)
        if result is not None:
            new_layers.append(result)

    # Сохраняем текущие слои
    st.session_state.layers = new_layers

    # Кнопка добавления слоя (после сохранения, чтобы rerun не потерял данные)
    if st.button("➕ Добавить слой", use_container_width=True):
        st.session_state.layers.append(_new_layer())
        st.rerun()

    # Суммарная мощность
    total = sum(layer.get("thickness", 0) or 0 for layer in new_layers)
    st.caption(f"Суммарная мощность: {total:.2f} м | Слоёв: {len(new_layers)}")
