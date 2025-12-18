"""Стили и константы для графиков."""

# Шрифты
FONT_FAMILY = "Inter, -apple-system, system-ui, Arial, sans-serif"
FONT_SIZE = 16

# Цветовая палитра (линии данных - одинаковые для обеих тем)
COLORS_DATA = {
    "Nu": "#d62728",           # красный
    "Nu_design": "#d62728",    # красный
    "R": "#9467bd",            # фиолетовый
    "p_operation": "#2ca02c",  # зелёный
    "p_preload": "#1f77b4",    # синий
    "F_operation": "#2ca02c",  # зелёный
    "F_preload": "#1f77b4",    # синий
    "safe_zone": "rgba(46, 204, 113, 0.15)",
    "danger_zone": "rgba(231, 76, 60, 0.25)",
}

# Светлая тема
COLORS_LIGHT = {
    **COLORS_DATA,
    "template": "plotly_white",
    "plot_bg": "white",
    "paper_bg": "white",
    "text": "black",
    "grid": "rgba(0,0,0,0.1)",
    "axis_line": "black",
    "axis_tick": "black",
    "legend_bg": "rgba(255,255,255,0.9)",
    "legend_border": "black",
    "annotation_bg": "rgba(255,255,255,0.8)",
    "marker_border": "black",
    "layer_line": "black",  # Черный для границ слоёв
    "layer_fill_a": "rgba(0,0,0,0.02)",
    "layer_fill_b": "rgba(0,0,0,0.05)",
}

# Тёмная тема (для Streamlit dark mode)
COLORS_DARK = {
    **COLORS_DATA,
    "template": "plotly_dark",
    "plot_bg": "rgba(14, 17, 23, 0)",
    "paper_bg": "rgba(14, 17, 23, 0)",
    "text": "#fafafa",
    "grid": "rgba(255,255,255,0.1)",
    "axis_line": "#fafafa",
    "axis_tick": "#fafafa",
    "legend_bg": "rgba(38, 39, 48, 0.9)",
    "legend_border": "#fafafa",
    "annotation_bg": "rgba(38, 39, 48, 0.8)",
    "marker_border": "#fafafa",
    "layer_line": "#aaa",
    "layer_fill_a": "rgba(255,255,255,0.02)",
    "layer_fill_b": "rgba(255,255,255,0.05)",
}

# Толщина линий
LINE_WIDTH_BOLD = 3
LINE_WIDTH_THIN = 2

# Тексты для разных методик
LABELS = {
    "russian": {
        "title_left": "<b>I группа ПС: <i>N<sub>u</sub></i>(<i>d</i>)</b>",
        "title_right": "<b>II группа ПС: <i>R</i>(<i>d</i>)</b>",
        "nu_label": "<i>N<sub>u</sub></i>",
        "nu_design_label": "<i>γ<sub>c</sub> N<sub>u</sub> / γ<sub>n</sub></i>",
        "r_label": "<i>R</i>",
        "show_nu_design": True,
    },
    "western": {
        "title_left": "<b>Предельная несущая способность: <i>V<sub>L</sub></i>(<i>d</i>)</b>",
        "title_right": "<b>Контактное давление: <i>R</i>(<i>d</i>)</b>",
        "nu_label": "<i>V<sub>L</sub></i>",
        "nu_design_label": "",
        "r_label": "<i>R</i> = <i>V<sub>L</sub></i>/<i>A</i>",
        "show_nu_design": False,
    },
}
