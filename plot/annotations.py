"""Аннотации: слои, критические глубины, маркеры равновесия."""

import plotly.graph_objects as go

from core.models import PointResult, SoilLayer
from .styles import FONT_FAMILY, FONT_SIZE


def add_layers(plotter, layers: list[SoilLayer]):
    """Отрисовка границ слоёв с подписями."""
    z_top = 0.0
    layer_idx = 0

    for layer in layers:
        z_bottom = z_top + layer.thickness
        z_mid = z_top + layer.thickness / 2

        if z_top > plotter.max_depth:
            break

        # Лёгкая заливка слоёв для лучшей читаемости разреза
        fill_color = plotter.colors["layer_fill_a"] if layer_idx % 2 == 0 else plotter.colors["layer_fill_b"]
        for col in [1, 2]:
            plotter.fig.add_hrect(
                y0=z_top,
                y1=min(z_bottom, plotter.max_depth * 1.05),
                fillcolor=fill_color,
                opacity=1.0,
                line_width=0,
                layer="below",
                row=1,
                col=col,
            )

        if z_bottom <= plotter.max_depth * 1.05:
            for col in [1, 2]:
                plotter.fig.add_hline(
                    y=z_bottom, line_width=1, line_dash="solid",
                    line_color=plotter.colors["layer_line"], opacity=0.5, row=1, col=col,
                )

        if z_mid <= plotter.max_depth:
            layer_text = f"<b>{layer.name}</b><br>{z_top:.1f}–{min(z_bottom, plotter.max_depth):.1f} м"
            plotter.fig.add_annotation(
                x=1.01, y=z_mid, xref="paper", yref="y2",
                text=layer_text, showarrow=False,
                xanchor="left", yanchor="middle",
                font=dict(size=int(FONT_SIZE * 0.8), color=plotter.colors["text"], family=FONT_FAMILY),
                bgcolor=plotter.colors["annotation_bg"],
            )

        z_top = z_bottom
        layer_idx += 1


def add_critical_depth_annotations(plotter, d_op: float | None, d_pre: float | None):
    """Горизонтальные линии критических глубин."""

    def _add_line(d_val, col_idx, label: str, color: str, x_pos: float):
        if d_val is None or d_val <= 0:
            return

        plotter.fig.add_hline(
            y=d_val, line_width=2, line_dash="dot", line_color=color, row=1, col=col_idx,
        )

        axis_suffix = "" if col_idx == 1 else str(col_idx)
        plotter.fig.add_annotation(
            x=x_pos, y=d_val,
            xref=f"x{axis_suffix} domain", yref=f"y{axis_suffix}",
            text=f"<b>{label}: <i>d</i>* = {d_val:.2f} м</b>",
            showarrow=False, yshift=15, xanchor="right",
            bgcolor=plotter.colors["annotation_bg"],
            font=dict(color=color, size=FONT_SIZE - 4),
        )

    if d_op:
        _add_line(d_op, 1, "экспл", plotter.colors["F_operation"], 0.95)
        _add_line(d_op, 2, "экспл", plotter.colors["p_operation"], 0.95)

    if d_pre and (not d_op or abs(d_pre - d_op) > 0.1):
        _add_line(d_pre, 1, "предн", plotter.colors["F_preload"], 0.70)
        _add_line(d_pre, 2, "предн", plotter.colors["p_preload"], 0.70)


def add_equilibrium_markers(
    plotter,
    results: list[PointResult],
    F: float,
    area: float,
    gamma_n: float = 1.0,
    gamma_c: float = 1.0,
):
    """Маркеры точек равновесия (пересечение кривой с нагрузкой)."""
    if not results:
        return

    F_MN = F / 1000
    p = F / area

    # Левый график: Nu_design vs F
    for i in range(1, len(results)):
        prev_nu = results[i - 1].Nu * gamma_c / gamma_n / 1000
        curr_nu = results[i].Nu * gamma_c / gamma_n / 1000

        if (prev_nu < F_MN) != (curr_nu < F_MN):
            t = results[i]
            entering_safe = curr_nu >= F_MN and prev_nu < F_MN
            color = "#2ca02c" if entering_safe else "#d62728"
            symbol = "triangle-up" if entering_safe else "triangle-down"

            plotter.fig.add_trace(
                go.Scatter(
                    x=[curr_nu], y=[t.d], mode="markers",
                    marker=dict(size=14, color=color, symbol=symbol, line=dict(width=2, color=plotter.colors["marker_border"])),
                    name=f"<i>d</i>* = {t.d:.2f} м",
                    hovertemplate=f"d* = {t.d:.2f} м<br>F = {curr_nu:.1f} МН<extra></extra>",
                ),
                row=1, col=1,
            )

    # Правый график: R vs p
    for i in range(1, len(results)):
        prev_r = results[i - 1].R
        curr_r = results[i].R

        if (prev_r < p) != (curr_r < p):
            t = results[i]
            entering_safe = curr_r >= p and prev_r < p
            color = "#2ca02c" if entering_safe else "#d62728"
            symbol = "triangle-up" if entering_safe else "triangle-down"

            plotter.fig.add_trace(
                go.Scatter(
                    x=[curr_r], y=[t.d], mode="markers",
                    marker=dict(size=14, color=color, symbol=symbol, line=dict(width=2, color=plotter.colors["marker_border"])),
                    showlegend=False,
                    hovertemplate=f"d* = {t.d:.2f} м<br>R = {curr_r:.0f} кПа<extra></extra>",
                ),
                row=1, col=2,
            )
