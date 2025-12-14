"""Методы для отрисовки кривых и линий нагрузки."""

import numpy as np
import plotly.graph_objects as go

from core.models import PointResult
from core.helpers import additional_stress_boussinesq
from .styles import FONT_SIZE, LINE_WIDTH_BOLD, LINE_WIDTH_THIN


def plot_curves(plotter, results: list[PointResult], gamma_n: float = 1.0, gamma_c: float = 1.0):
    """Отрисовка основных кривых Nu/Vl и R."""
    if not results:
        return

    depths = [r.d for r in results]
    nu_values = [r.Nu / 1000 for r in results]
    r_values = [r.R for r in results]
    customdata = [(r.eta1, r.eta2, r.p, r.layer_name) for r in results]

    plotter.max_depth = max(depths)
    plotter.max_nu = max(nu_values)
    plotter.max_r = max(r_values)

    # Шаблоны hover
    def hover_tpl(label: str, fmt: str, unit: str) -> str:
        return (
            f"d = %{{y:.2f}} м<br>{label} = %{{x:{fmt}}} {unit}<br>"
            "η₁ = %{customdata[0]:.3f}<br>η₂ = %{customdata[1]:.3f}<br>"
            "p = %{customdata[2]:.0f} кПа<br>Слой: %{customdata[3]}<extra></extra>"
        )

    hover_nu = hover_tpl(plotter.labels["nu_label"], ".2f", "МН")
    hover_r = hover_tpl(plotter.labels["r_label"], ".0f", "кПа")

    # Кривые Nu/Vl
    if plotter.labels["show_nu_design"]:
        nu_design = [r.Nu * gamma_c / gamma_n / 1000 for r in results]
        plotter.fig.add_trace(go.Scatter(
            x=nu_values, y=depths, mode="lines", name=plotter.labels["nu_label"],
            line=dict(color=plotter.colors["Nu"], width=LINE_WIDTH_THIN, dash="dash"),
            customdata=customdata, hovertemplate=hover_nu,
        ), row=1, col=1)
        plotter.fig.add_trace(go.Scatter(
            x=nu_design, y=depths, mode="lines", name=plotter.labels["nu_design_label"],
            line=dict(color=plotter.colors["Nu_design"], width=LINE_WIDTH_BOLD),
            customdata=customdata, hovertemplate=hover_nu,
        ), row=1, col=1)
    else:
        plotter.fig.add_trace(go.Scatter(
            x=nu_values, y=depths, mode="lines", name=plotter.labels["nu_label"],
            line=dict(color=plotter.colors["Nu"], width=LINE_WIDTH_BOLD),
            customdata=customdata, hovertemplate=hover_nu,
        ), row=1, col=1)

    # Кривая R
    plotter.fig.add_trace(go.Scatter(
        x=r_values, y=depths, mode="lines", name=plotter.labels["r_label"],
        line=dict(color=plotter.colors["R"], width=LINE_WIDTH_BOLD),
        customdata=customdata, hovertemplate=hover_r,
    ), row=1, col=2)

    plotter._update_axes()


def _add_force_line(plotter, F_MN: float, color: str, name: str, y_offset: float):
    """Добавить вертикальную линию нагрузки F на левый график."""
    plotter.fig.add_trace(go.Scatter(
        x=[F_MN, F_MN], y=[0, plotter.max_depth],
        mode="lines", name=name,
        line=dict(color=color, width=LINE_WIDTH_THIN),
    ), row=1, col=1)
    plotter.fig.add_annotation(
        x=F_MN, y=plotter.max_depth * y_offset, xref="x", yref="y",
        text=f"<b>{F_MN:.1f}</b>", showarrow=False,
        font=dict(color=color, size=FONT_SIZE - 4),
        bgcolor=plotter.colors["annotation_bg"], xanchor="center",
    )


def _add_pressure_line(plotter, p_surface: float, color: str, name: str, y_offset: float,
                       b: float = None, l: float = None, depths: np.ndarray = None):
    """Добавить линию давления на правый график (вертикальную или Буссинеска)."""
    use_boussinesq = b is not None and l is not None and b > 0 and l > 0

    if use_boussinesq and depths is not None:
        p_values = [additional_stress_boussinesq(p_surface, b, l, d) for d in depths]
        plotter.fig.add_trace(go.Scatter(
            x=p_values, y=depths, mode="lines", name=name,
            line=dict(color=color, width=LINE_WIDTH_THIN),
        ), row=1, col=2)
        ann_y = 0
    else:
        plotter.fig.add_trace(go.Scatter(
            x=[p_surface, p_surface], y=[0, plotter.max_depth],
            mode="lines", name=name,
            line=dict(color=color, width=LINE_WIDTH_THIN),
        ), row=1, col=2)
        ann_y = plotter.max_depth * y_offset

    plotter.fig.add_annotation(
        x=p_surface, y=ann_y, xref="x2", yref="y2",
        text=f"<b>{p_surface:.0f}</b>", showarrow=False,
        font=dict(color=color, size=FONT_SIZE - 4),
        bgcolor=plotter.colors["annotation_bg"], xanchor="center",
    )


def add_load_lines(plotter, F_op: float, F_pre: float | None, area: float, b: float = None, l: float = None):
    """Добавление линий нагрузок с учётом распределения давления по Буссинеску."""
    use_boussinesq = b is not None and l is not None and b > 0 and l > 0
    depths = np.linspace(0, plotter.max_depth, 100) if use_boussinesq else None

    # Эксплуатационная нагрузка
    _add_force_line(plotter, F_op / 1000, plotter.colors["F_operation"], "<i>F</i><sub>экспл</sub>", 0.95)
    _add_pressure_line(
        plotter, F_op / area, plotter.colors["p_operation"],
        "<i>σ<sub>zp</sub></i><sub>экспл</sub>" if use_boussinesq else "<i>p</i><sub>экспл</sub>",
        0.95, b, l, depths
    )

    # Преднагрузка
    if F_pre:
        _add_force_line(plotter, F_pre / 1000, plotter.colors["F_preload"], "<i>F</i><sub>предн</sub>", 0.90)
        _add_pressure_line(
            plotter, F_pre / area, plotter.colors["p_preload"],
            "<i>σ<sub>zp</sub></i><sub>предн</sub>" if use_boussinesq else "<i>p</i><sub>предн</sub>",
            0.90, b, l, depths
        )
