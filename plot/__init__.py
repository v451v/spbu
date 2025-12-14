"""Модуль визуализации результатов расчёта СПБУ."""

from core.models import PointResult, SoilLayer

from .base import BasePlotter
from .curves import add_load_lines, plot_curves
from .annotations import add_critical_depth_annotations, add_equilibrium_markers, add_layers
from .zones import add_punch_through_zones


class PublicationPlotter(BasePlotter):
    """Класс для построения графиков в стиле научных публикаций."""

    def plot_curves(self, results: list[PointResult], gamma_n: float = 1.0, gamma_c: float = 1.0):
        plot_curves(self, results, gamma_n, gamma_c)

    def add_load_lines(self, F_op: float, F_pre: float | None, area: float, b: float = None, l: float = None):
        add_load_lines(self, F_op, F_pre, area, b, l)

    def add_layers(self, layers: list[SoilLayer]):
        add_layers(self, layers)

    def add_critical_depth_annotations(self, d_op: float | None, d_pre: float | None):
        add_critical_depth_annotations(self, d_op, d_pre)

    def add_punch_through_zones(self, results: list[PointResult], F: float):
        add_punch_through_zones(self, results, F)

    def add_equilibrium_markers(
        self,
        results: list[PointResult],
        F: float,
        area: float,
        gamma_n: float = 1.0,
        gamma_c: float = 1.0,
    ):
        add_equilibrium_markers(self, results, F, area, gamma_n, gamma_c)


__all__ = ["PublicationPlotter"]
