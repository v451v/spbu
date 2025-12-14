"""Визуализация зон punch-through."""

import plotly.graph_objects as go

from core.models import PointResult


def add_punch_through_zones(plotter, results: list[PointResult], F: float):
    """Закрашивает области между кривой Vl и линией F.
    
    - Зелёная: Vl > F (безопасно)
    - Красная: Vl < F (punch-through риск)
    """
    if not results:
        return

    F_MN = F / 1000

    # Разбиваем на сегменты
    segments = []
    current = {"safe": results[0].Nu >= F, "points": [results[0]]}

    for i in range(1, len(results)):
        is_safe = results[i].Nu >= F
        if is_safe == current["safe"]:
            current["points"].append(results[i])
        else:
            segments.append(current)
            current = {"safe": is_safe, "points": [results[i]]}
    segments.append(current)

    safe_added = danger_added = False

    for seg in segments:
        pts = seg["points"]
        if len(pts) < 2:
            continue

        x_poly = [r.Nu / 1000 for r in pts] + [F_MN, F_MN]
        y_poly = [r.d for r in pts] + [pts[-1].d, pts[0].d]

        if seg["safe"]:
            plotter.fig.add_trace(
                go.Scatter(
                    x=x_poly, y=y_poly, fill="toself",
                    fillcolor=plotter.colors["safe_zone"], line=dict(width=0),
                    name="Safe zone" if not safe_added else None,
                    showlegend=not safe_added, hoverinfo="skip",
                ),
                row=1, col=1,
            )
            safe_added = True
        else:
            plotter.fig.add_trace(
                go.Scatter(
                    x=x_poly, y=y_poly, fill="toself",
                    fillcolor=plotter.colors["danger_zone"], line=dict(width=0),
                    name="Punch-through risk" if not danger_added else None,
                    showlegend=not danger_added, hoverinfo="skip",
                ),
                row=1, col=1,
            )
            danger_added = True
