"""Базовый класс для построения графиков."""

from plotly.subplots import make_subplots

from .styles import COLORS_LIGHT, COLORS_DARK, FONT_FAMILY, FONT_SIZE, LABELS


def _auto_dtick(max_val: float, thresholds: list[tuple[float, float]]) -> float:
    """Автоматический выбор шага делений оси."""
    for threshold, dtick in thresholds:
        if max_val < threshold:
            return dtick
    return thresholds[-1][1]


# Пороги для разных осей
_DEPTH_THRESHOLDS = [(10, 0.5), (25, 1.0), (50, 2.0), (float("inf"), 5.0)]
_FORCE_THRESHOLDS = [(20, 5), (50, 10), (100, 20), (200, 50), (500, 100), (1000, 200), (2000, 500), (float("inf"), 1000)]
_PRESSURE_THRESHOLDS = [(100, 10), (200, 20), (400, 40), (600, 50), (1000, 100), (2000, 200), (float("inf"), 250)]


class BasePlotter:
    """Базовый класс с настройкой layout и осей."""

    def __init__(self, methodology: str = "russian", theme: str = "dark"):
        self.methodology = methodology
        self.theme = theme
        self.colors = COLORS_DARK if theme == "dark" else COLORS_LIGHT
        self.labels = LABELS.get(methodology, LABELS["russian"])
        self.fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.15, shared_yaxes=True)
        self._setup_layout()
        self.max_depth = 0.0
        self.max_nu = 0.0
        self.max_r = 0.0

    def _setup_layout(self):
        """Базовые настройки макета."""
        self.fig.update_layout(
            font=dict(family=FONT_FAMILY, size=FONT_SIZE, color=self.colors["text"]),
            template=self.colors["template"],
            height=900,
            width=1500,
            margin=dict(l=80, r=160, t=180, b=170),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top", y=-0.12,
                xanchor="center", x=0.5,
                bgcolor=self.colors["legend_bg"],
                bordercolor=self.colors["legend_border"],
                borderwidth=1,
                font=dict(size=13, color=self.colors["text"]),
            ),
            plot_bgcolor=self.colors["plot_bg"],
            paper_bgcolor=self.colors["paper_bg"],
        )

        # Заголовки
        for text, x in [(self.labels["title_left"], 0.225), (self.labels["title_right"], 0.775)]:
            self.fig.add_annotation(
                text=text, x=x, y=1.18, xref="paper", yref="paper",
                showarrow=False, font=dict(size=18, color=self.colors["text"]),
                xanchor="center", yanchor="bottom",
            )

    def _update_axes(self):
        """Обновление осей с учетом данных."""
        dtick_depth = _auto_dtick(self.max_depth, _DEPTH_THRESHOLDS)

        # Ось Y (глубина) для обоих графиков
        y_axis_config = dict(
            range=[self.max_depth * 1.05, 0],
            showgrid=True, gridwidth=0.75, gridcolor=self.colors["grid"],
            dtick=dtick_depth,
            linecolor=self.colors["axis_line"], linewidth=2,
            ticks="outside", tickwidth=2, tickcolor=self.colors["axis_tick"],
            tickfont=dict(family=FONT_FAMILY, size=FONT_SIZE, color=self.colors["text"]),
            mirror=True, showticklabels=True,
        )
        self.fig.update_yaxes(title=dict(text="<b>Глубина <i>d</i>, м</b>", standoff=15), **y_axis_config, row=1, col=1)
        self.fig.update_yaxes(**y_axis_config, row=1, col=2)

        # Общие настройки оси X
        x_axis_base = dict(
            side="top",
            showgrid=True, gridwidth=0.75, gridcolor=self.colors["grid"],
            tickangle=0,
            linecolor=self.colors["axis_line"], linewidth=2,
            ticks="outside", tickwidth=2, tickcolor=self.colors["axis_tick"],
            tickfont=dict(family=FONT_FAMILY, size=FONT_SIZE - 2, color=self.colors["text"]),
            mirror=True,
        )

        # Ось X для Nu/Vl (левый график)
        max_x_nu = self.max_nu * 1.1 if self.max_nu > 0 else 10
        self.fig.update_xaxes(
            title=dict(text="<b>Нагрузка <i>F</i>, МН</b>", standoff=2,
                       font=dict(family=FONT_FAMILY, size=FONT_SIZE, color=self.colors["text"])),
            range=[0, max_x_nu],
            dtick=_auto_dtick(max_x_nu, _FORCE_THRESHOLDS),
            **x_axis_base, row=1, col=1,
        )

        # Ось X для R (правый график)
        max_x_r = self.max_r * 1.1 if self.max_r > 0 else 100
        self.fig.update_xaxes(
            title=dict(text="<b>Давление <i>p</i>, кПа</b>", standoff=15,
                       font=dict(family=FONT_FAMILY, size=FONT_SIZE, color=self.colors["text"])),
            range=[0, max_x_r],
            dtick=_auto_dtick(max_x_r, _PRESSURE_THRESHOLDS),
            **x_axis_base, row=1, col=2,
        )

    def get_figure(self):
        """Возвращает figure с настройкой для высокого качества экспорта."""
        self.fig.update_layout(autosize=False, width=1500, height=900)
        return self.fig
