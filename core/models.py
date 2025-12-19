"""Модели данных для расчёта основания СПБУ."""

import math
from bisect import bisect_left
from dataclasses import dataclass
from typing import Literal
from pydantic import BaseModel, Field, computed_field, model_validator


# --- Грунт ---


class SoilLayer(BaseModel):
    """Слой грунта (ИГЭ/РГЭ)."""

    name: str
    thickness: float = Field(gt=0, description="Мощность слоя, м")
    gamma_prime: float = Field(gt=0, description="Удельный вес с учётом взвешивания, кН/м³")
    phi: float = Field(ge=0, le=45, description="Угол внутреннего трения, °")
    c: float = Field(ge=0, default=0.0, description="Удельное сцепление, кПа")
    E: float | None = Field(default=None, gt=0, description="Модуль деформации, МПа")
    soil_type: str | None = Field(default=None, description="Тип грунта для визуализации")
    
    # II группа ПС (если не заданы — берутся из I группы)
    phi_II: float | None = Field(default=None, ge=0, le=45, description="φ для II группы ПС, °")
    c_II: float | None = Field(default=None, ge=0, description="c для II группы ПС, кПа")
    gamma_prime_II: float | None = Field(default=None, gt=0, description="γ' для II группы ПС, кН/м³")
    
    # Скальные грунты (СП 22.13330)
    Rc: float | None = Field(default=None, gt=0, description="Предел прочности на одноосное сжатие, МПа")
    
    # Западная методика (C2)
    cu: float | None = Field(default=None, ge=0, description="Недренированная прочность, кПа")
    drainage: Literal["drained", "undrained"] | None = Field(default=None, description="Условия дренирования")

    @model_validator(mode="after")
    def fill_group_II_defaults(self):
        """Заполнить параметры II группы ПС значениями I группы, если не заданы."""
        if self.phi_II is None:
            self.phi_II = self.phi
        if self.c_II is None:
            self.c_II = self.c
        if self.gamma_prime_II is None:
            self.gamma_prime_II = self.gamma_prime
        return self


class SoilProfile(BaseModel):
    """Геологический разрез."""

    layers: list[SoilLayer] = Field(default_factory=list)
    name: str = ""
    water_depth: float = Field(ge=0, default=0.0, description="Глубина воды, м")

    @computed_field
    @property
    def total_thickness(self) -> float:
        return sum(layer.thickness for layer in self.layers)


@dataclass(frozen=True)
class SoilProfileCache:
    """Кэш параметров разреза для ускорения повторных расчётов."""

    layers: list[SoilLayer]
    boundaries: list[float]
    gamma_prime: list[float]
    phi: list[float]
    cu: list[float]
    total_thickness: float
    cum_gamma: list[float]

    @classmethod
    def from_layers(cls, layers: list[SoilLayer]) -> "SoilProfileCache":
        if not layers:
            return cls(
                layers=[],
                boundaries=[0.0],
                gamma_prime=[],
                phi=[],
                cu=[],
                total_thickness=0.0,
                cum_gamma=[0.0],
            )

        boundaries = [0.0]
        gamma_prime = []
        phi = []
        cu = []
        cum_gamma = [0.0]

        for layer in layers:
            thickness = layer.thickness
            boundaries.append(boundaries[-1] + thickness)
            gamma_prime.append(layer.gamma_prime)
            phi.append(layer.phi)
            cu_value = layer.cu if layer.cu is not None else layer.c
            cu.append(cu_value)
            cum_gamma.append(cum_gamma[-1] + layer.gamma_prime * thickness)

        return cls(
            layers=layers,
            boundaries=boundaries,
            gamma_prime=gamma_prime,
            phi=phi,
            cu=cu,
            total_thickness=boundaries[-1],
            cum_gamma=cum_gamma,
        )

    def _layer_index(self, depth: float) -> int:
        if not self.gamma_prime:
            return 0
        if depth <= 0.0:
            return 0
        if depth >= self.total_thickness:
            return len(self.gamma_prime) - 1

        idx = bisect_left(self.boundaries, depth) - 1
        return max(0, min(idx, len(self.gamma_prime) - 1))

    def overburden_stress(self, depth: float) -> float:
        if depth <= 0 or not self.gamma_prime:
            return 0.0

        if depth >= self.total_thickness:
            extra = depth - self.total_thickness
            return self.cum_gamma[-1] + self.gamma_prime[-1] * extra

        idx = self._layer_index(depth)
        z_top = self.boundaries[idx]
        return self.cum_gamma[idx] + self.gamma_prime[idx] * (depth - z_top)

    def average_cu_below(self, d: float, z_thickness: float) -> float:
        if not self.cu or z_thickness <= 0:
            return self.cu[-1] if self.cu else 0.0

        z_start, z_end = d, d + z_thickness
        total_h = 0.0
        cu_sum = 0.0

        start_idx = self._layer_index(z_start)
        end_idx = self._layer_index(min(z_end, self.total_thickness))

        for i in range(start_idx, end_idx + 1):
            z_top = self.boundaries[i]
            z_bot = self.boundaries[i + 1]
            h = min(z_bot, z_end) - max(z_top, z_start)
            if h <= 0:
                continue
            total_h += h
            cu_sum += self.cu[i] * h

        if z_end > self.total_thickness:
            extra = z_end - max(self.total_thickness, z_start)
            if extra > 0:
                total_h += extra
                cu_sum += self.cu[-1] * extra

        return cu_sum / total_h if total_h > 0 else 0.0

    def average_sand_props_below(self, d: float, z_thickness: float) -> tuple[float, float]:
        if not self.phi or not self.gamma_prime or z_thickness <= 0:
            if self.phi and self.gamma_prime:
                return self.phi[-1], self.gamma_prime[-1]
            return 30.0, 10.0

        z_start, z_end = d, d + z_thickness
        total_h = 0.0
        phi_sum = 0.0
        gamma_sum = 0.0

        start_idx = self._layer_index(z_start)
        end_idx = self._layer_index(min(z_end, self.total_thickness))

        for i in range(start_idx, end_idx + 1):
            z_top = self.boundaries[i]
            z_bot = self.boundaries[i + 1]
            h = min(z_bot, z_end) - max(z_top, z_start)
            if h <= 0:
                continue
            total_h += h
            phi_sum += self.phi[i] * h
            gamma_sum += self.gamma_prime[i] * h

        if z_end > self.total_thickness:
            extra = z_end - max(self.total_thickness, z_start)
            if extra > 0:
                total_h += extra
                phi_sum += self.phi[-1] * extra
                gamma_sum += self.gamma_prime[-1] * extra

        if total_h <= 0:
            return self.phi[-1], self.gamma_prime[-1]

        return phi_sum / total_h, gamma_sum / total_h


# --- Фундамент ---


class Foundation(BaseModel):
    """Фундамент (башмак СПБУ)."""

    area: float = Field(gt=0, description="Площадь подошвы, м²")
    e_x: float = Field(ge=0, default=0.0, description="Эксцентриситет по X, м")
    e_y: float = Field(ge=0, default=0.0, description="Эксцентриситет по Y, м")
    
    # Западная методика (C2)
    V_spud: float | None = Field(default=None, gt=0, description="Полный объём башмака, м³")
    V_D: float | None = Field(default=None, gt=0, description="Объём ниже макс. площади, м³")
    D_eff: float | None = Field(default=None, gt=0, description="Эффективный диаметр шипа, м")
    beta: float | None = Field(default=None, gt=0, le=180, description="Угол конуса шипа, °")

    @computed_field
    @property
    def b(self) -> float:
        """Ширина (круг: √A)."""
        return self.area ** 0.5

    @computed_field
    @property
    def l(self) -> float:
        """Длина (круг: √A)."""
        return self.area ** 0.5

    @computed_field
    @property
    def b_prime(self) -> float:
        """Приведённая ширина b' = b - 2e_x (СП 22 п.5.29)."""
        return max(0.01, self.b - 2.0 * self.e_x)

    @computed_field
    @property
    def l_prime(self) -> float:
        """Приведённая длина l' = l - 2e_y (СП 22 п.5.29)."""
        return max(0.01, self.l - 2.0 * self.e_y)

    @computed_field
    @property
    def area_prime(self) -> float:
        """Приведённая площадь A' = b'·l'."""
        return self.b_prime * self.l_prime

    @computed_field
    @property
    def eta(self) -> float:
        """η = l'/b' (≥1, для круглого = 1)."""
        return max(1.0, self.l_prime / self.b_prime)

    @computed_field
    @property
    def B_eff(self) -> float:
        """Эффективный диаметр B для западной методики (C.2).

        Определение из методики: B — эффективный диаметр опоры (башмака) на глубине
        максимального его соприкосновения с грунтом; для прямоугольного башмака равен ширине.

        В текущей реализации предполагается круглая эквивалентная площадь A' => B = √(4A'/π).
        """
        return math.sqrt(4.0 * self.area_prime / math.pi)


# --- Коэффициенты ---


class Coefficients(BaseModel):
    """Коэффициенты надёжности."""

    gamma_n: float = Field(default=1.25, gt=0, description="Коэф. надёжности по ответственности")
    gamma_lc: float = Field(default=1.0, gt=0, description="Коэф. сочетания нагрузок")
    gamma_c1: float = Field(default=1.0, gt=0, description="Коэф. условий работы 1")
    gamma_c2: float = Field(default=1.0, gt=0, description="Коэф. условий работы 2")
    k: float = Field(default=1.0, ge=1.0, le=1.1, description="1.0 — испытания, 1.1 — таблицы")
    
    # Западная методика (C2)
    use_backfill: bool = Field(default=False, description="Учитывать обратную засыпку")


# --- Результаты ---


class PointResult(BaseModel):
    """Результат расчёта для глубины d."""

    d: float = Field(ge=0, description="Глубина, м")
    Nu: float = Field(ge=0, description="Несущая способность, кН")
    R: float = Field(ge=0, description="Расчётное сопротивление, кПа")
    p: float = Field(ge=0, description="Среднее давление, кПа")
    eta1: float = Field(description="η₁ = γlc·F·γn / Nu")
    eta2: float = Field(description="η₂ = p / R")
    layer_name: str

    @computed_field
    @property
    def is_safe_I(self) -> bool:
        """Выполнение условия I группы ПС."""
        return self.eta1 <= 1.0

    @computed_field
    @property
    def is_safe_II(self) -> bool:
        """Выполнение условия II группы ПС."""
        return self.eta2 <= 1.0

    @computed_field
    @property
    def is_safe(self) -> bool:
        """Выполнение обоих условий."""
        return self.is_safe_I and self.is_safe_II


class CalculationResult(BaseModel):
    """Результаты расчёта."""

    curve: list[PointResult]
    d_operation: float | None = None
    d_preload: float | None = None
    eq_operation: PointResult | None = None
    eq_preload: PointResult | None = None
    depths: list[float]
    settlements: list[float] = Field(description="Осадки, мм")
    punch_through_risk: bool = Field(
        default=False, 
        description="Флаг риска punch-through (только для западной методики)"
    )
