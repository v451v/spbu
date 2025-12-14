"""Вспомогательные функции для UI."""

import io
import tomllib
import tomli_w

from core.models import SoilLayer, Foundation, Coefficients


def build_models(state):
    """Конвертировать state в Pydantic-модели."""
    cleaned_layers = []
    for layer in state["layers"]:
        cleaned = {k: v for k, v in layer.items() if v is not None}
        cleaned.setdefault("c", 0.0)
        cleaned_layers.append(cleaned)

    layers = [SoilLayer(**layer) for layer in cleaned_layers]

    foundation_data = {k: v for k, v in state["foundation"].items() if v is not None and v != 0}
    foundation_data.setdefault("area", state["foundation"]["area"])
    foundation = Foundation(**foundation_data)

    return layers, foundation, Coefficients(**state["coefficients"])


def export_toml(state) -> str:
    """Экспортировать state в TOML-строку."""
    # Фильтруем None значения из слоёв
    layers = [{k: v for k, v in layer.items() if v is not None} for layer in state["layers"]]

    # Фильтруем None и нулевые значения из foundation (кроме area)
    foundation = {k: v for k, v in state["foundation"].items() if v is not None and (v != 0 or k == "area")}

    # Формируем calculation с учётом метода
    calculation = {
        "method": state["method"],
        "d_max": state["calc_params"]["d_max"],
        "d_step": state["calc_params"]["d_step"],
    }
    if state["method"] == "russian":
        calculation["stress_distribution"] = state["calc_params"].get("stress_distribution", "alpha")

    doc = {
        "project": {"name": "Экспорт из Streamlit"},
        "foundation": foundation,
        "loads": state["loads"],
        "coefficients": state["coefficients"],
        "calculation": calculation,
        "layers": layers,
    }
    return tomli_w.dumps(doc)


def import_toml(content: bytes) -> dict:
    """Импортировать TOML в формат state."""
    data = tomllib.load(io.BytesIO(content))

    # Обработка слоёв: добавляем отсутствующие поля как None
    optional_keys = ["E", "cu", "drainage", "phi_II", "c_II", "gamma_prime_II"]
    layers = []
    for layer_data in data.get("layers", []):
        layer = dict(layer_data)
        for key in optional_keys:
            layer.setdefault(key, None)
        layers.append(layer)

    # Обработка фундамента с дефолтами
    foundation_defaults = {
        "area": 154.0, "e_x": 0.0, "e_y": 0.0,
        "V_spud": None, "V_D": None, "D_eff": None, "beta": None,
    }
    foundation = {**foundation_defaults, **data.get("foundation", {})}

    # Обработка коэффициентов с дефолтами
    coefficients_defaults = {
        "gamma_n": 1.25, "gamma_lc": 1.0, "gamma_c1": 1.0,
        "gamma_c2": 1.0, "k": 1.0, "use_backfill": False,
    }
    coefficients = {**coefficients_defaults, **data.get("coefficients", {})}

    calc_data = data.get("calculation", {})
    return {
        "method": calc_data.get("method", "russian"),
        "layers": layers,
        "foundation": foundation,
        "loads": data.get("loads", {"operation": 57290.0, "preload": 76700.0}),
        "coefficients": coefficients,
        "calc_params": {
            "d_max": calc_data.get("d_max", 20.0),
            "d_step": calc_data.get("d_step", 0.1),
            "stress_distribution": calc_data.get("stress_distribution", "alpha"),
        },
    }
