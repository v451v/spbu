"""Модели данных для расчёта основания СПБУ."""

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
