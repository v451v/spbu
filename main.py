import sys
import tomllib

from core.models import SoilLayer, Foundation, Coefficients
from core.calculator import calculate
from plot import PublicationPlotter


def load_input(path: str) -> tuple[list[SoilLayer], Foundation, Coefficients, dict]:
    """Загрузить входные данные из TOML."""
    with open(path, "rb") as f:
        data = tomllib.load(f)

    layers = [
        SoilLayer(
            name=L["name"],
            thickness=L["thickness"],
            gamma_prime=L["gamma_prime"],
            phi=L["phi"],
            c=L.get("c", 0.0),
            E=L.get("E"),
            soil_type=L.get("soil_type"),
            phi_II=L.get("phi_II"),
            c_II=L.get("c_II"),
            gamma_prime_II=L.get("gamma_prime_II"),
            # Скальные грунты (СП 22.13330)
            Rc=L.get("Rc"),  # МПа — предел прочности на одноосное сжатие
            # Западная методика (C2)
            cu=L.get("cu"),
            drainage=L.get("drainage"),
        )
        for L in data["layers"]
    ]

    foundation_data = data.get("foundation", {})
    foundation = Foundation(
        area=foundation_data["area"],
        e_x=foundation_data.get("e_x", 0.0),
        e_y=foundation_data.get("e_y", 0.0),
        # Западная методика (C2)
        V_spud=foundation_data.get("V_spud"),
        V_D=foundation_data.get("V_D"),
        D_eff=foundation_data.get("D_eff"),
        beta=foundation_data.get("beta"),
    )

    coef_data = data.get("coefficients", {})
    coef = Coefficients(
        gamma_n=coef_data.get("gamma_n", 1.25),
        gamma_lc=coef_data.get("gamma_lc", 1.0),
        gamma_c1=coef_data.get("gamma_c1", 1.0),
        gamma_c2=coef_data.get("gamma_c2", 1.0),
        k=coef_data.get("k", 1.0),
        # Западная методика (C2)
        use_backfill=coef_data.get("use_backfill", False),
    )

    calc_data = data.get("calculation", {})
    params = {
        "name": data.get("project", {}).get("name", ""),
        "F_operation": data["loads"]["operation"],
        "F_preload": data["loads"]["preload"],
        "d_max": calc_data.get("d_max", 20.0),
        "d_step": calc_data.get("d_step", 0.2),
        "method": calc_data.get("method", "russian"),
        "stress_distribution": calc_data.get("stress_distribution", "alpha"),
    }

    return layers, foundation, coef, params


def main(input_file: str = "input.toml"):
    """Загрузка → расчёт → вывод → графики."""
    layers, foundation, coef, params = load_input(input_file)

    method = params["method"]
    result = calculate(
        layers=layers,
        foundation=foundation,
        coef=coef,
        F_operation=params["F_operation"],
        F_preload=params["F_preload"],
        d_max=params["d_max"],
        d_step=params["d_step"],
        method=method,
        stress_distribution=params.get("stress_distribution", "alpha"),
    )

    method_name = "Российская (СП)" if method == "russian" else "Западная (SNAME/ISO)"
    print(f"Проект: {params['name']}")
    print(f"Методика: {method_name}")
    if result.d_operation:
        print(f"d* (эксплуатация) = {result.d_operation:.2f} м")
    if result.d_preload:
        print(f"d* (преднагрузка) = {result.d_preload:.2f} м")

    # --- Отрисовка (Обновленная) ---
    # Для западной методики gamma = 1.0
    if method == "russian":
        gamma_n = coef.gamma_n
        gamma_c = coef.gamma_c1 * coef.gamma_c2
    else:
        gamma_n = 1.0
        gamma_c = 1.0

    plotter = PublicationPlotter(methodology=method, theme="light")
    
    # 1. Рисуем кривые
    plotter.plot_curves(results=result.curve, gamma_n=gamma_n, gamma_c=gamma_c)
    
    # 2. Добавляем линии нагрузок (с распределением по Буссинеску)
    plotter.add_load_lines(
        F_op=params["F_operation"],
        F_pre=params["F_preload"],
        area=foundation.area_prime,
        b=foundation.b_prime,
        l=foundation.l_prime
    )
    
    # 3. Добавляем отметки слоёв
    plotter.add_layers(layers)
    
    # 4. Добавляем аннотации найденных глубин
    plotter.add_critical_depth_annotations(
        d_op=result.d_operation,
        d_pre=result.d_preload
    )

    # 5. Маркеры точек равновесия
    plotter.add_equilibrium_markers(
        results=result.curve,
        F=params["F_operation"],
        area=foundation.area_prime,
        gamma_n=gamma_n,
        gamma_c=gamma_c,
    )

    # 6. Зоны punch-through (только для западной методики)
    if method == "western":
        plotter.add_punch_through_zones(result.curve, params["F_operation"])

    fig = plotter.get_figure()
    output_name = input_file.replace(".toml", ".html")
    fig.write_html(output_name)
    print(f"График: {output_name}")

    return result


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "input.toml"
    main(input_file)
