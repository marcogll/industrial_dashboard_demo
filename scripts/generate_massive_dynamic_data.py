#!/usr/bin/env python3
"""Generate synthetic operational data for Massive Dynamic sheet metal plant."""

import csv
import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
CURATED = DATA / "curated"
CURATED.mkdir(parents=True, exist_ok=True)

LINES = [
    {"name": "Corte LASER", "stations": ["Alimentación", "Corte", "Inspección"], "takt": 1800, "target": 48, "client": "Toyota", "scrap_rate": 0.02, "downtime_avg": 25, "downtime_std": 10, "oee_base": 0.85},
    {"name": "Doblado Fine", "stations": ["P1", "P2", "P3", "P4"], "takt": 2400, "target": 36, "client": "Honda", "scrap_rate": 0.015, "downtime_avg": 20, "downtime_std": 8, "oee_base": 0.88},
    {"name": "Doblado Heavy", "stations": ["P5", "P6", "P7", "P8"], "takt": 3200, "target": 27, "client": "Mitsubishi Heavy Industries", "scrap_rate": 0.03, "downtime_avg": 35, "downtime_std": 15, "oee_base": 0.78},
    {"name": "Soldadura", "stations": ["Preparación", "Soldadura MIG", "Soldadura TIG", "Acabado"], "takt": 2800, "target": 30, "client": "Denso", "scrap_rate": 0.025, "downtime_avg": 30, "downtime_std": 12, "oee_base": 0.82},
    {"name": "Pintura", "stations": ["Pretratamiento", "Pintura polvo", "Curado", "Inspección"], "takt": 2200, "target": 36, "client": "Yazaki", "scrap_rate": 0.04, "downtime_avg": 40, "downtime_std": 18, "oee_base": 0.72},
]

PRODUCTS = [
    {"pn": "MD-SOP-001-A", "name": "Soporte chasis", "client": "Toyota", "programa": "CHASIS-2026-A"},
    {"pn": "MD-BAS-001-B", "name": "Base gabinete", "client": "Honda", "programa": "GABINETE-2026-B"},
    {"pn": "MD-PAN-001-C", "name": "Panel lateral", "client": "Mitsubishi Heavy Industries", "programa": "PANEL-2026-C"},
    {"pn": "MD-BRA-001-D", "name": "Bracket refuerzo", "client": "Denso", "programa": "BRACKET-2026-D"},
    {"pn": "MD-MON-001-E", "name": "Montante rack", "client": "Yazaki", "programa": "RACK-2026-E"},
    {"pn": "MD-TAP-001-F", "name": "Tapa blindaje", "client": "Toyota", "programa": "BLINDAJE-2026-F"},
    {"pn": "MD-ESC-001-G", "name": "Escuadra unión", "client": "Honda", "programa": "ESCUADRA-2026-G"},
    {"pn": "MD-PLACA-001-H", "name": "Placa base", "client": "Mitsubishi Heavy Industries", "programa": "PLACA-2026-H"},
]

BASE_OPS = {
    "Corte LASER": [2, 1, 1],
    "Doblado Fine": [1, 1, 1, 1],
    "Doblado Heavy": [1, 1, 1, 1],
    "Soldadura": [2, 1, 1, 1],
    "Pintura": [2, 1, 1, 1],
}


def normal_clamped(mu, sigma, lo, hi):
    v = random.gauss(mu, sigma)
    return max(lo, min(hi, round(v)))


def workdays(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def write_csv(path, rows, delimiter=","):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=delimiter)
        w.writeheader()
        w.writerows(rows)
    print(f"  {path} ({len(rows)} rows)")


def gen_stations():
    rows = []
    sid = 1
    for line in LINES:
        ops_list = BASE_OPS.get(line["name"], [1])
        n = len(line["stations"])
        base_ct = line["takt"] / n * 0.85
        # Create realistic spread: early stations faster, later stations slower, one bottleneck
        for i, s in enumerate(line["stations"]):
            ops = ops_list[i] if i < len(ops_list) else 1
            # Each station gets a distinct CT — some above, some below base
            offset_pct = (i / (n - 1) - 0.5) * 0.3 if n > 1 else 0
            ct = normal_clamped(base_ct * (1 + offset_pct), 25, 50, line["takt"])
            rows.append({
                "station_id": sid,
                "station_name": s,
                "time_seconds": ct,
                "operators": ops,
                "line": line["name"],
            })
            sid += 1
    return rows


def gen_balanceo(stations):
    rows = []
    for s in stations:
        line = next(l for l in LINES if l["name"] == s["line"])
        takt = line["takt"]
        ct = s["time_seconds"]
        bal_target = takt / len(line["stations"])
        delta = round(ct - bal_target, 1)
        pct = round(ct / takt * 100, 1)
        ct_op = int(round(ct / s["operators"]))
        pct_takt = round(ct_op / takt * 100, 1)
        if pct_takt > 95:
            status = "CUELLO"
        elif pct_takt > 85:
            status = "≈Takt"
        else:
            status = "OK"
        rows.append({
            "linea": s["line"], "estacion": s["station_name"], "ct_actual": ct,
            "takt": takt, "delta": delta, "pct_utilizacion": pct,
            "status": status, "ops": s["operators"], "ct_op": ct_op, "pct_takt": pct_takt,
        })
    return rows


def gen_produccion_diaria():
    rows = []
    # 12 months: enero a diciembre 2026 (~260 workdays)
    months_12 = [
        (date(2026, 1, 5), date(2026, 1, 31)),
        (date(2026, 2, 2), date(2026, 2, 28)),
        (date(2026, 3, 2), date(2026, 3, 31)),
        (date(2026, 4, 1), date(2026, 4, 30)),
        (date(2026, 5, 4), date(2026, 5, 31)),
        (date(2026, 6, 1), date(2026, 6, 30)),
        (date(2026, 7, 1), date(2026, 7, 31)),
        (date(2026, 8, 3), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 9, 30)),
        (date(2026, 10, 1), date(2026, 10, 31)),
        (date(2026, 11, 2), date(2026, 11, 30)),
        (date(2026, 12, 1), date(2026, 12, 31)),
    ]
    # Hiccup weeks: 3-4 periods where capacity drops
    hiccup_weeks: set[tuple[int, int]] = set()
    for _ in range(random.randint(3, 4)):
        week_start = random.randint(2, 50)
        month_idx = random.randint(0, 11)
        hiccup_weeks.add((month_idx, week_start))

    orders = 0
    for month_idx, (start, end) in enumerate(months_12):
        for d in workdays(start, end):
            is_hiccup = False
            for mi, wk in hiccup_weeks:
                if mi == month_idx and abs(d.isocalendar()[1] - wk) <= 1:
                    is_hiccup = True
                    break
            # Stable company: most days 80-90%, hiccup days 60-75%
            if is_hiccup:
                cap_range = (0.65, 0.78)
            else:
                # slight monthly trend
                monthly_trend = 0.80 + (month_idx / 11) * 0.08  # 80% → 88% over year
                cap_range = (monthly_trend - 0.04, monthly_trend + 0.06)

            dow_factor = {0: 0.85, 1: 0.95, 2: 1.05, 3: 1.05, 4: 0.90}[d.weekday()]
            for line in LINES:
                n_orders = 2 if random.random() < 0.4 else 1
                primary_products = [p for p in PRODUCTS if p["client"] == line["client"]]
                fallback = [p for p in PRODUCTS if p["client"] != line["client"]]
                for _ in range(n_orders):
                    orders += 1
                    if primary_products and random.random() < 0.75:
                        prod = random.choice(primary_products)
                    else:
                        prod = random.choice(fallback or PRODUCTS)
                    cap = random.uniform(*cap_range)
                    target = max(1, int(line["target"] * dow_factor * cap))
                    produced = max(0, int(target * random.uniform(0.85, 1.02)))
                    scrap = int(target * random.uniform(line["scrap_rate"] * 0.5, line["scrap_rate"] * 2.0))
                    downtime = round(max(0, min(150, random.gauss(line["downtime_avg"], line["downtime_std"]))))
                    # OEE range 70-90%, lower during hiccups
                    oee_base = line["oee_base"] - (0.12 if is_hiccup else 0)
                    oee = round(max(0.50, min(0.98, random.gauss(oee_base, 0.06))), 3)
                    rows.append({
                        "fecha": d.isoformat(), "linea": line["name"],
                        "orden": f"MD-{d.strftime('%y%m%d')}-{orders:03d}",
                        "producto": prod["pn"], "cliente": prod["client"],
                        "meta": target, "producido": produced,
                        "scrap": scrap, "downtime_min": downtime, "oee": oee,
                    })
    return rows


def gen_plan_accion():
    data = [
        (1, "Reducir tiempo de setup en prensas P1-P4", "Doblado Fine", "Setup", "Alta", "2026-06-01", "2026-07-15", "Ing. José López", "Cronómetro, checklist SMED", "Setup < 30 min"),
        (2, "Implementar mantenimiento autónomo en Corte LASER", "Corte LASER", "Mantenimiento", "Alta", "2026-06-01", "2026-06-30", "Ing. Mario Gómez", "Formato TPM, lubricantes", "MTBF > 120 hrs"),
        (3, "Estandarizar parámetros de soldadura MIG", "Soldadura", "Calidad", "Alta", "2026-05-15", "2026-06-15", "Ing. Ana Martínez", "WPS, medidores espesor", "FPY > 95%"),
        (4, "Reducir caminatas en Pintura (reacomodo)", "Pintura", "Lean", "Media", "2026-06-15", "2026-07-30", "Ing. Luis Fernández", "Layout propuesto, cintas", "Distancia < 50 m"),
        (5, "Capacitar operadores en Doblado Heavy", "Doblado Heavy", "Capacitación", "Media", "2026-06-01", "2026-06-20", "RH / Karla Ruiz", "Manuales, videos, evaluación", "90% operadores certificados"),
        (6, "Implementar kanban entre Corte y Doblado", "Corte LASER", "Flujo", "Alta", "2026-07-01", "2026-08-15", "Ing. Pedro Sánchez", "Tarjetas kanban, racks", "WIP < 200 pzs"),
        (7, "Reducir scrap en Pintura (pretratamiento)", "Pintura", "Calidad", "Alta", "2026-05-20", "2026-06-30", "Ing. Carmen Torres", "Control baños, análisis laboratorio", "Scrap < 3%"),
        (8, "Ajustar takt de Doblado Fine a 2200 seg", "Doblado Fine", "Mejora", "Media", "2026-07-01", "2026-08-01", "Ing. José López", "Estudio de tiempos, cronómetro", "CT < 2200 seg"),
        (9, "Automatizar inspección en Corte LASER", "Corte LASER", "Tecnología", "Media", "2026-08-01", "2026-10-01", "Ing. Mario Gómez", "Cámara visión, software", "Inspección 100%"),
        (10, "Reducir cambios de formato en Heavy", "Doblado Heavy", "Setup", "Alta", "2026-06-15", "2026-07-31", "Ing. Ricardo Mendoza", "Prensas rápidas, matrices modulares", "Setup < 45 min"),
        (11, "Implementar 5S en área de Soldadura", "Soldadura", "Lean", "Media", "2026-06-01", "2026-06-30", "Supervisor Turno A", "Formatos 5S, etiquetas, estantes", "Auditoría > 80%"),
        (12, "Balancear estaciones de Pintura", "Pintura", "Balanceo", "Media", "2026-07-01", "2026-07-31", "Ing. Luis Fernández", "Estudio de tiempos, redistribución", "Pct utilización < 90%"),
        (13, "Reducir retrabajo en soldadura TIG", "Soldadura", "Calidad", "Alta", "2026-05-20", "2026-06-20", "Ing. Ana Martínez", "Plantilla alineación, parametría", "Rework < 2%"),
        (14, "Programar mantenimiento preventivo P5-P8", "Doblado Heavy", "Mantenimiento", "Media", "2026-06-01", "2026-06-30", "Mantenimiento General", "Plan MTTO, refacciones", "Disponibilidad > 90%"),
        (15, "Optimizar consumo de polvo en Pintura", "Pintura", "Costo", "Baja", "2026-07-15", "2026-08-30", "Ing. Carmen Torres", "Medidor flujo, boquillas", "Costo < $12/hr"),
        (16, "Implementar doble turno en Corte LASER", "Corte LASER", "Producción", "Media", "2026-08-01", "2026-09-01", "Gerencia Planta", "Contratación, horarios", "Output > 96 pzs/día"),
        (17, "Reducir mermas en manipulación de lámina", "Doblado Heavy", "Calidad", "Baja", "2026-06-15", "2026-07-15", "Supervisor Turno B", "Capacitación manipulación, EPP", "Merma < 1%"),
        (18, "Estandarizar checklist de arranque", "Soldadura", "Proceso", "Media", "2026-06-01", "2026-06-15", "Ing. Ana Martínez", "Checklist laminado, formato digital", "100% cumplimiento"),
        (19, "Implementar Andon en Doblado Fine", "Doblado Fine", "Tecnología", "Baja", "2026-09-01", "2026-10-15", "Ing. José López", "Tablero andon, luces, buzzer", "Tiempo respuesta < 3 min"),
        (20, "Reducir tiempo de curado en Pintura", "Pintura", "Mejora", "Media", "2026-07-01", "2026-07-31", "Ing. Luis Fernández", "Horno, perfil temperatura", "Curado < 20 min"),
    ]
    return [{
        "num": a[0], "accion": a[1], "linea": a[2], "area": a[3], "prioridad": a[4],
        "inicio": a[5], "fin": a[6], "responsable": a[7], "recursos": a[8],
        "kpi": a[9], "status": "pendiente",
    } for a in data]


def gen_demanda():
    rows = []
    for p in PRODUCTS:
        base = (int(p["pn"].split("-")[1].split("0")[-1]) * 120 + 50
                if p["pn"].split("-")[1].split("0")[-1].isdigit()
                else 200)
        months = ["ene", "feb", "mar", "abr", "may", "jun",
                   "jul", "ago", "sep", "oct", "nov", "dic"]
        vals = [int(base * (1.0 + 0.08 * (i / 11) + random.uniform(-0.06, 0.06))) for i in range(len(months))]
        rows.append({
            "programa": p["programa"], "part_number": p["pn"],
            **dict(zip(months, vals)),
            "total": sum(vals), "pico": max(vals),
        })
    return rows


def gen_desperdicios():
    return [
        {"categoria": "Trabajo productivo", "tiempo_seg": 1820, "pct": 65.0, "causa_raiz": "Proceso estable", "accion": "Mantener"},
        {"categoria": "Esperas", "tiempo_seg": 280, "pct": 10.0, "causa_raiz": "Falta de material en estación", "accion": "Implementar kanban"},
        {"categoria": "Retrabajo", "tiempo_seg": 196, "pct": 7.0, "causa_raiz": "Parámetros de soldadura no estandarizados", "accion": "Estandarizar WPS"},
        {"categoria": "Caminatas", "tiempo_seg": 168, "pct": 6.0, "causa_raiz": "Layout ineficiente", "accion": "Reacomodar estaciones"},
        {"categoria": "Setup", "tiempo_seg": 140, "pct": 5.0, "causa_raiz": "SMED no implementado", "accion": "Capacitar en SMED"},
        {"categoria": "Mantenimiento", "tiempo_seg": 84, "pct": 3.0, "causa_raiz": "Falta de TPM", "accion": "Implementar mantenimiento autónomo"},
        {"categoria": "Calidad", "tiempo_seg": 56, "pct": 2.0, "causa_raiz": "Inspección manual", "accion": "Automatizar inspección"},
        {"categoria": "Otros", "tiempo_seg": 56, "pct": 2.0, "causa_raiz": "Varios", "accion": "Análisis adicional"},
    ]


def gen_throughput():
    return [
        {"etapa": "Baseline (Actual)", "pzas_hr": 28},
        {"etapa": "Reducción Setup (SMED)", "pzas_hr": 32},
        {"etapa": "Balanceo de Línea", "pzas_hr": 36},
        {"etapa": "Kanban + WIP Reducido", "pzas_hr": 40},
        {"etapa": "TPM + Mantenimiento Autónomo", "pzas_hr": 42},
        {"etapa": "Optimizado (Meta)", "pzas_hr": 48},
    ]


def gen_kanban():
    return [
        {"part_number": "MD-SOP-001-A", "days_left": 1, "owner": "Ing. Mario Gómez", "linea": "Corte LASER"},
        {"part_number": "MD-BAS-001-B", "days_left": 2, "owner": "Ing. José López", "linea": "Doblado Fine"},
        {"part_number": "MD-PAN-001-C", "days_left": 1, "owner": "Ing. Ricardo Mendoza", "linea": "Doblado Heavy"},
        {"part_number": "MD-BRA-001-D", "days_left": 3, "owner": "Ing. Ana Martínez", "linea": "Soldadura"},
        {"part_number": "MD-TAP-001-F", "days_left": 2, "owner": "Supervisor Turno A", "linea": "Corte LASER"},
        {"part_number": "MD-ESC-001-G", "days_left": 5, "owner": "Ing. José López", "linea": "Doblado Fine"},
        {"part_number": "MD-MON-001-E", "days_left": 1, "owner": "Ing. Luis Fernández", "linea": "Pintura"},
        {"part_number": "MD-PLACA-001-H", "days_left": 4, "owner": "Ing. Ricardo Mendoza", "linea": "Doblado Heavy"},
    ]


def gen_bom():
    data = [
        ("MD-BAS-001-B", "Base gabinete acero 14Ga", "Estructura", "pza", "Honda", "GABINETE-2026-B"),
        ("MD-BAS-002-B", "Refuerzo base gabinete", "Estructura", "pza", "Honda", "GABINETE-2026-B"),
        ("MD-BAS-003-B", "Tornillo M8x20", "Sujeción", "pza", "Honda", "GABINETE-2026-B"),
        ("MD-BAS-004-B", "Tornillo M6x16", "Sujeción", "pza", "Honda", "GABINETE-2026-B"),
        ("MD-BAS-005-B", "Arandela plana 8mm", "Sujeción", "pza", "Honda", "GABINETE-2026-B"),
        ("MD-BAS-006-B", "Tuerca M8", "Sujeción", "pza", "Honda", "GABINETE-2026-B"),
        ("MD-SOP-001-A", "Soporte chasis acero 12Ga", "Estructura", "pza", "Toyota", "CHASIS-2026-A"),
        ("MD-SOP-002-A", "Refuerzo soporte chasis", "Estructura", "pza", "Toyota", "CHASIS-2026-A"),
        ("MD-SOP-003-A", "Buje soporte 20mm", "Componente", "pza", "Toyota", "CHASIS-2026-A"),
        ("MD-SOP-004-A", "Perno M10x25", "Sujeción", "pza", "Toyota", "CHASIS-2026-A"),
        ("MD-SOP-005-A", "Arandela presión 10mm", "Sujeción", "pza", "Toyota", "CHASIS-2026-A"),
        ("MD-SOP-006-A", "Etiqueta identificación", "Consumible", "pza", "Toyota", "CHASIS-2026-A"),
        ("MD-PAN-001-C", "Panel lateral acero 16Ga", "Estructura", "pza", "Mitsubishi Heavy Industries", "PANEL-2026-C"),
        ("MD-PAN-002-C", "Refuerzo panel lateral", "Estructura", "pza", "Mitsubishi Heavy Industries", "PANEL-2026-C"),
        ("MD-PAN-003-C", "Tornillo M5x12", "Sujeción", "pza", "Mitsubishi Heavy Industries", "PANEL-2026-C"),
        ("MD-PAN-004-C", "Clip fijación panel", "Sujeción", "pza", "Mitsubishi Heavy Industries", "PANEL-2026-C"),
        ("MD-BRA-001-D", "Bracket refuerzo acero 10Ga", "Estructura", "pza", "Denso", "BRACKET-2026-D"),
        ("MD-BRA-002-D", "Tornillo M12x30", "Sujeción", "pza", "Denso", "BRACKET-2026-D"),
        ("MD-BRA-003-D", "Tuerca M12", "Sujeción", "pza", "Denso", "BRACKET-2026-D"),
        ("MD-BRA-004-D", "Arandela plana 12mm", "Sujeción", "pza", "Denso", "BRACKET-2026-D"),
        ("MD-BRA-005-D", "Protector anticorrosivo", "Consumible", "ml", "Denso", "BRACKET-2026-D"),
        ("MD-MON-001-E", "Montante rack acero 12Ga", "Estructura", "pza", "Yazaki", "RACK-2026-E"),
        ("MD-MON-002-E", "Base montante", "Estructura", "pza", "Yazaki", "RACK-2026-E"),
        ("MD-MON-003-E", "Tornillo M8x16", "Sujeción", "pza", "Yazaki", "RACK-2026-E"),
        ("MD-MON-004-E", "Tuerca M8", "Sujeción", "pza", "Yazaki", "RACK-2026-E"),
        ("MD-MON-005-E", "Nivelador montante", "Componente", "pza", "Yazaki", "RACK-2026-E"),
        ("MD-MON-006-E", "Tapón plástico", "Componente", "pza", "Yazaki", "RACK-2026-E"),
        ("MD-TAP-001-F", "Tapa blindaje acero 8Ga", "Estructura", "pza", "Toyota", "BLINDAJE-2026-F"),
        ("MD-TAP-002-F", "Bisagra tapa blindaje", "Componente", "pza", "Toyota", "BLINDAJE-2026-F"),
        ("MD-TAP-003-F", "Manija tapa", "Componente", "pza", "Toyota", "BLINDAJE-2026-F"),
        ("MD-TAP-004-F", "Tornillo M6x20", "Sujeción", "pza", "Toyota", "BLINDAJE-2026-F"),
        ("MD-TAP-005-F", "Cerrojo tapa", "Componente", "pza", "Toyota", "BLINDAJE-2026-F"),
        ("MD-ESC-001-G", "Escuadra unión acero 14Ga", "Estructura", "pza", "Honda", "ESCUADRA-2026-G"),
        ("MD-ESC-002-G", "Tornillo M10x25", "Sujeción", "pza", "Honda", "ESCUADRA-2026-G"),
        ("MD-ESC-003-G", "Tuerca M10", "Sujeción", "pza", "Honda", "ESCUADRA-2026-G"),
        ("MD-ESC-004-G", "Arandela presión 10mm", "Sujeción", "pza", "Honda", "ESCUADRA-2026-G"),
        ("MD-PLACA-001-H", "Placa base acero 6Ga", "Estructura", "pza", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("MD-PLACA-002-H", "Refuerzo placa base", "Estructura", "pza", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("MD-PLACA-003-H", "Tornillo M16x40", "Sujeción", "pza", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("MD-PLACA-004-H", "Tuerca M16", "Sujeción", "pza", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("MD-PLACA-005-H", "Arandela plana 16mm", "Sujeción", "pza", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("MD-PLACA-006-H", "Placa niveladora", "Componente", "pza", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("MD-PLACA-007-H", "Anclaje expansivo M16", "Sujeción", "pza", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("MD-PLACA-008-H", "Sello neopreno", "Consumible", "m", "Mitsubishi Heavy Industries", "PLACA-2026-H"),
        ("PIN-001", "Pin de posicionamiento 10mm", "Herramienta", "pza", "General", "HERR-2026"),
        ("PIN-002", "Pin de posicionamiento 12mm", "Herramienta", "pza", "General", "HERR-2026"),
        ("DIS-001", "Disco corte 4.5\"", "Consumible", "pza", "General", "CONS-2026"),
        ("DIS-002", "Disco desbaste 7\"", "Consumible", "pza", "General", "CONS-2026"),
        ("GAS-001", "Gas Argón (cilindro)", "Consumible", "pza", "General", "CONS-2026"),
        ("GAS-002", "Gas CO2 (cilindro)", "Consumible", "pza", "General", "CONS-2026"),
        ("VAR-001", "Pintura polvo negro", "Consumible", "kg", "General", "CONS-2026"),
        ("VAR-002", "Pintura polvo gris", "Consumible", "kg", "General", "CONS-2026"),
        ("VAR-003", "Desengrasante industrial", "Consumible", "L", "General", "CONS-2026"),
    ]
    return [{"part_number": d[0], "description": d[1], "category": d[2], "unit": d[3], "client": d[4], "programa": d[5]} for d in data]


def gen_dashboard_resumen():
    return [
        {"indicador": "Takt Promedio (seg)", "valor": 2480},
        {"indicador": "CT Promedio (seg)", "valor": 2210},
        {"indicador": "OEE Global (%)", "valor": 80.7},
        {"indicador": "Scrap Global (%)", "valor": 1.4},
        {"indicador": "Downtime Promedio (min/orden)", "valor": 29.4},
        {"indicador": "Producción Total 12 meses (pzs)", "valor": 46865},
        {"indicador": "Utilización Promedio (%)", "valor": 78.3},
        {"indicador": "Productividad (pzs/operator/hr)", "valor": 4.2},
        {"indicador": "Tasa de Defectos (PPM)", "valor": 12500},
        {"indicador": "MTBF (hrs)", "valor": 96},
        {"indicador": "MTTR (min)", "valor": 45},
        {"indicador": "Costo por Unidad ($)", "valor": 12.80},
        {"indicador": "On-Time Delivery (%)", "valor": 86.5},
        {"indicador": "Fill Rate (%)", "valor": 91.2},
        {"indicador": "Past Due Orders", "valor": 18},
    ]


def gen_dashboard_estaciones(stations):
    # Group stations by line
    by_line: dict[str, list[dict]] = {}
    for line in LINES:
        key = line["name"]
        by_line[key] = []
        for st in line["stations"]:
            s = next(x for x in stations if x["station_name"] == st and x["line"] == line["name"])
            ct = s["time_seconds"]
            pct = round(ct / line["takt"] * 100, 1)
            if pct > 95:
                status = "CUELLO"
            elif pct > 85:
                status = "≈Takt"
            else:
                status = "OK"
            by_line[key].append({"estacion": st, "ct_seg": ct, "pct_takt": pct, "status": status})
    # Pivot to wide format — one row per station index, columns prefixed by line slug
    line_keys = list(by_line.keys())
    max_n = max(len(v) for v in by_line.values())
    prefixed = []
    for line_key in line_keys:
        slug = line_key.lower().replace(" ", "_")
        if slug == "corte_laser":
            slug = "corte"
        for i, st in enumerate(by_line[line_key]):
            if i >= len(prefixed):
                prefixed.append({})
            prefixed[i][f"{slug}_estacion"] = st["estacion"]
            prefixed[i][f"{slug}_descripcion"] = st["estacion"]
            prefixed[i][f"{slug}_ct_seg"] = st["ct_seg"]
            prefixed[i][f"{slug}_pct_takt"] = st["pct_takt"]
            prefixed[i][f"{slug}_estado"] = st["status"]
    # Fill missing slots
    for i in range(len(prefixed)):
        for line_key in line_keys:
            slug = line_key.lower().replace(" ", "_")
            for col in ("estacion", "descripcion", "ct_seg", "pct_takt", "estado"):
                key = f"{slug}_{col}"
                if key not in prefixed[i]:
                    prefixed[i][key] = ""
    return prefixed


def gen_flujo_proceso():
    return [
        {"corte": "Alimentación de lámina en mesa de corte", "doblado_fine": "Carga de pieza en prensa P1", "doblado_heavy": "Carga de pieza en prensa P5", "soldadura": "Preparación de bordes y limpieza", "pintura": "Desengrase y fosfatizado"},
        {"corte": "Programación CNC y corte LASER", "doblado_fine": "Doblado secuencia P1-P2-P3-P4", "doblado_heavy": "Doblado secuencia P5-P6-P7-P8", "soldadura": "Soldadura MIG (cordón continuo)", "pintura": "Aplicación de pintura polvo"},
        {"corte": "Inspección dimensional post-corte", "doblado_fine": "Verificación angular con galgas", "doblado_heavy": "Verificación angular y dimensional", "soldadura": "Soldadura TIG (puntos críticos)", "pintura": "Curado en horno a 200°C x 25 min"},
        {"corte": "Clasificación y etiquetado de piezas", "doblado_fine": "Etiquetado y liberación al PT", "doblado_heavy": "Liberación al PT con registro", "soldadura": "Acabado y desbaste de cordones", "pintura": "Inspección visual y espesor"},
    ]


def gen_herramental():
    data = [
        ("Corte LASER", "Corte", "Lente focal 7.5\"", "Óptica CO2", "5000 hrs", 2, "Consumible"),
        ("Corte LASER", "Corte", "Boquilla 1.4mm", "Cobre", "200 hrs", 10, "Consumible"),
        ("Corte LASER", "Corte", "Espejo plano", "Silicio", "3000 hrs", 4, "Consumible"),
        ("Doblado Fine", "P1", "Punzón recto 20mm", "Acero D2", "50000 ciclos", 2, "Herramienta"),
        ("Doblado Fine", "P2", "Matriz V 12mm", "Acero D2", "50000 ciclos", 2, "Herramienta"),
        ("Doblado Fine", "P3", "Punzón gozne 88°", "Acero D2", "40000 ciclos", 1, "Herramienta"),
        ("Doblado Fine", "P4", "Matriz V 20mm", "Acero D2", "50000 ciclos", 2, "Herramienta"),
        ("Doblado Heavy", "P5", "Punzón recto 30mm", "Acero D2", "40000 ciclos", 2, "Herramienta"),
        ("Doblado Heavy", "P6", "Matriz V 25mm", "Acero D2", "40000 ciclos", 2, "Herramienta"),
        ("Doblado Heavy", "P7", "Punzón gozne 88° heavy", "Acero D2", "30000 ciclos", 1, "Herramienta"),
        ("Doblado Heavy", "P8", "Matriz V 16mm", "Acero D2", "50000 ciclos", 2, "Herramienta"),
        ("Soldadura", "Soldadura MIG", "Antorcha MIG 400A", "Binzel", "2000 hrs", 4, "Consumible"),
        ("Soldadura", "Soldadura TIG", "Antorcha TIG 250A", "Weldcraft", "3000 hrs", 3, "Consumible"),
        ("Soldadura", "Preparación", "Esmeril angular 4.5\"", "Makita 9557B", "500 hrs", 4, "Equipo"),
        ("Pintura", "Pintura polvo", "Pistola corona", "Nordson", "2000 hrs", 3, "Equipo"),
        ("Pintura", "Pretratamiento", "Bomba dosificadora", "Graco", "3000 hrs", 2, "Equipo"),
        ("Pintura", "Curado", "Termopar tipo K", "Omega", "1000 hrs", 6, "Instrumento"),
        ("Pintura", "Inspección", "Medidor espesor", "PosiTector 6000", "2000 hrs", 2, "Instrumento"),
        ("Pintura", "Inspección", "Galga P256", "BYK", "5000 ciclos", 3, "Herramienta"),
    ]
    return [{"linea": d[0], "estacion": d[1], "herramienta": d[2], "especificacion": d[3], "uso": d[4], "cantidad": d[5], "tipo": d[6], "status": "active"} for d in data]


def gen_inversion():
    data = [
        ("Capacitación SMED", 3500, "Capacitación 10 operadores, materiales, cronómetros"),
        ("Implementación TPM", 2800, "Formatos, lubricantes, kits limpieza, capacitación"),
        ("Equipo de Visión Artificial", 4200, "Cámara industrial, software, iluminación LED"),
        ("Tableros Kanban", 1800, "5 tableros, tarjetas, soportes, rack magnético"),
        ("Herramental SMED", 2700, "Prensas rápidas, matrices modulares, calibradores"),
    ]
    return [{"categoria": d[0], "monto": d[1], "items": d[2]} for d in data]


def gen_roi():
    return [
        {"concepto": "Inversión Total", "valor": 15000},
        {"concepto": "Ahorro Anual Estimado", "valor": 48600},
        {"concepto": "Payback (meses)", "valor": 3.7},
        {"concepto": "ROI Anual (%)", "valor": 224},
        {"concepto": "Reducción de Setup (%)", "valor": 45},
        {"concepto": "Aumento de OEE (%)", "valor": 8.5},
        {"concepto": "Reducción de Scrap (%)", "valor": 35},
    ]


def gen_kpis_unificados():
    def status_fn(v, thresholds):
        if thresholds[0] == "le":
            return "OK" if v <= thresholds[1] else ("Alerta" if v <= thresholds[2] else "Crítico")
        else:
            return "OK" if v >= thresholds[1] else ("Alerta" if v >= thresholds[2] else "Crítico")

    kpis = [
        {"kpi": "OEE (%)", "vals": [85.2, 88.7, 75.3, 80.1, 70.8], "th": ["ge", 80, 70]},
        {"kpi": "Utilización (%)", "vals": [82.0, 85.0, 72.0, 78.0, 68.0], "th": ["ge", 80, 70]},
        {"kpi": "Scrap (%)", "vals": [2.0, 1.5, 3.0, 2.5, 4.0], "th": ["le", 2.5, 4.0]},
        {"kpi": "FPY (%)", "vals": [95.0, 96.5, 92.0, 93.5, 89.0], "th": ["ge", 95, 90]},
        {"kpi": "Downtime (min/día)", "vals": [25, 20, 35, 30, 40], "th": ["le", 25, 40]},
        {"kpi": "Productividad (pzs/hr)", "vals": [6.0, 4.5, 3.4, 3.8, 4.5], "th": ["ge", 5.0, 3.5]},
        {"kpi": "MTBF (hrs)", "vals": [120, 150, 80, 95, 60], "th": ["ge", 120, 80]},
        {"kpi": "MTTR (min)", "vals": [30, 25, 45, 35, 55], "th": ["le", 30, 45]},
        {"kpi": "Rework (%)", "vals": [1.5, 1.0, 2.5, 2.0, 3.5], "th": ["le", 1.5, 3.0]},
        {"kpi": "Cumplimiento Prod. (%)", "vals": [92.0, 95.0, 85.0, 88.0, 78.0], "th": ["ge", 90, 80]},
    ]
    names = ["corte", "doblado_fine", "doblado_heavy", "soldadura", "pintura"]
    rows = []
    for k in kpis:
        st = status_fn(k["vals"][0], k["th"])
        acc = "" if st == "OK" else ("Revisar proceso" if st == "Alerta" else "Acción correctiva urgente")
        row = {"kpi": k["kpi"], "status": st, "accion": acc}
        for i, n in enumerate(names):
            row[n] = k["vals"][i]
        rows.append(row)
    return rows


def gen_kanban_tasks():
    return [
        {"id": 1, "title": "Reducir setup Corte LASER", "column_name": "In Progress", "priority": "high", "assignee": "Mario Gómez", "due_date": "2026-06-15"},
        {"id": 2, "title": "Implementar TPM Doblado Fine", "column_name": "Done", "priority": "high", "assignee": "José López", "due_date": "2026-05-30"},
        {"id": 3, "title": "Balancear estaciones Pintura", "column_name": "Todo", "priority": "medium", "assignee": "Luis Fernández", "due_date": "2026-07-01"},
        {"id": 4, "title": "Estandarizar soldadura MIG", "column_name": "In Progress", "priority": "high", "assignee": "Ana Martínez", "due_date": "2026-06-10"},
        {"id": 5, "title": "Capacitar operadores SMED", "column_name": "Todo", "priority": "medium", "assignee": "Karla Ruiz", "due_date": "2026-06-20"},
    ]

def gen_activities():
    return [
        {"activity_type": "Producción", "duration_minutes": 480, "created_at": "2026-05-22T08:00:00Z"},
        {"activity_type": "Mantenimiento", "duration_minutes": 120, "created_at": "2026-05-22T09:00:00Z"},
        {"activity_type": "Calidad", "duration_minutes": 60, "created_at": "2026-05-23T10:00:00Z"},
        {"activity_type": "Setup", "duration_minutes": 90, "created_at": "2026-05-24T07:30:00Z"},
        {"activity_type": "Capacitación", "duration_minutes": 240, "created_at": "2026-05-25T11:00:00Z"},
    ]

def gen_improvements():
    return [
        {"title": "SMED Corte LASER", "expected_savings_usd_annual": 12500},
        {"title": "TPM Doblado Fine", "expected_savings_usd_annual": 9800},
        {"title": "Kanban Material", "expected_savings_usd_annual": 7200},
        {"title": "Balanceo Línea", "expected_savings_usd_annual": 10500},
        {"title": "Visión Artificial", "expected_savings_usd_annual": 8600},
    ]

def gen_lines():
    return [
        {"id": 1, "code": "CL", "name": "Corte LASER", "takt_seconds": 2821, "target_pieces_per_shift": 115, "status": "active", "stations": 3, "oee": 85.2},
        {"id": 2, "code": "DF", "name": "Doblado Fine", "takt_seconds": 1927, "target_pieces_per_shift": 168, "status": "active", "stations": 4, "oee": 88.7},
        {"id": 3, "code": "DH", "name": "Doblado Heavy", "takt_seconds": 2217, "target_pieces_per_shift": 146, "status": "active", "stations": 4, "oee": 75.3},
        {"id": 4, "code": "SL", "name": "Soldadura", "takt_seconds": 2472, "target_pieces_per_shift": 131, "status": "active", "stations": 4, "oee": 80.1},
        {"id": 5, "code": "PT", "name": "Pintura", "takt_seconds": 2020, "target_pieces_per_shift": 128, "status": "active", "stations": 4, "oee": 70.8},
    ]

def gen_kpis_calidad():
    return [
        {"kpi": "First Pass Yield (%)", "corte_laser": 95.0, "doblado_fine": 96.5, "doblado_heavy": 92.0, "soldadura": 93.5, "pintura": 89.0},
        {"kpi": "Scrap Rate (%)", "corte_laser": 2.0, "doblado_fine": 1.5, "doblado_heavy": 3.0, "soldadura": 2.5, "pintura": 4.0},
        {"kpi": "Rework Rate (%)", "corte_laser": 1.5, "doblado_fine": 1.0, "doblado_heavy": 2.5, "soldadura": 2.0, "pintura": 3.5},
        {"kpi": "Customer Returns (PPM)", "corte_laser": 8500, "doblado_fine": 4500, "doblado_heavy": 15000, "soldadura": 12000, "pintura": 22000},
        {"kpi": "Defect Density (defectos/pza)", "corte_laser": 0.02, "doblado_fine": 0.015, "doblado_heavy": 0.04, "soldadura": 0.03, "pintura": 0.05},
    ]


def gen_ordenes_abiertas():
    """Generate past-due / open orders for logistics view."""
    clients = ["Toyota", "Honda", "Mitsubishi Heavy Industries", "Denso", "Yazaki"]
    statuses_weights = [("Atrasada", 0.25), ("Pendiente", 0.35), ("Completada", 0.40)]
    rows = []
    for i in range(1, 46):
        cliente = random.choice(clients)
        line_products = [p for p in PRODUCTS if p["client"] == cliente] or PRODUCTS
        prod = random.choice(line_products)
        # Delivery dates spread across the year, some already past
        order_month = random.randint(1, 12)
        delivery_day = random.randint(1, 28)
        delivery = date(2026, order_month, delivery_day)
        # How many days late (negative = early, positive = late)
        offset_days = random.randint(-5, 25) if random.random() < 0.6 else random.randint(-15, 5)
        actual = delivery + timedelta(days=offset_days)
        delay = (actual - delivery).days
        if delay > 7:
            status = "Atrasada"
        elif delay > 0:
            status = "Pendiente"
        else:
            status = "Completada"
        qty = random.randint(10, 500)
        value = round(qty * random.uniform(5, 45), 2)
        rows.append({
            "orden": f"PO-2026-{i:04d}",
            "cliente": cliente,
            "producto": prod["pn"],
            "cantidad": qty,
            "fecha_prometida": delivery.isoformat(),
            "fecha_real": actual.isoformat(),
            "dias_retraso": max(0, delay),
            "valor": value,
            "status": status,
        })
    return rows


def gen_logistica_kpis():
    """Monthly logistics KPIs for the year."""
    months = ["ene", "feb", "mar", "abr", "may", "jun",
              "jul", "ago", "sep", "oct", "nov", "dic"]
    # Stable but imperfect: OTD 82-92%, Fill Rate 88-95%
    rows = []
    trend = 0.82
    for i, m in enumerate(months):
        trend = min(0.92, trend + random.uniform(0, 0.015))
        otd = round(trend + random.uniform(-0.03, 0.02), 3)
        fill = round(min(0.96, otd + random.uniform(0.02, 0.06)), 3)
        past_due = random.randint(8, 28)
        avg_delay = round(random.uniform(2.5, 8.0), 1)
        rows.append({
            "mes": m,
            "otd_pct": otd * 100,
            "fill_rate_pct": fill * 100,
            "past_due_orders": past_due,
            "avg_delay_days": avg_delay,
            "backorder_usd": round(past_due * random.uniform(200, 800), 0),
        })
    return rows


def gen_logistica_entregas():
    """Daily delivery performance for charting."""
    rows = []
    for d in workdays(date(2026, 1, 5), date(2026, 12, 31)):
        total = random.randint(8, 25)
        on_time = int(total * random.uniform(0.75, 0.95))
        delayed = total - on_time
        rows.append({
            "fecha": d.isoformat(),
            "entregas_total": total,
            "entregas_a_tiempo": on_time,
            "entregas_retrasadas": delayed,
        })
    return rows


def main():
    print("Generating Massive Dynamic plant data...\n")

    print("A. stations.csv")
    stations = gen_stations()
    write_csv(DATA / "stations.csv", stations)

    print("B. balanceo_lineas.csv")
    write_csv(CURATED / "balanceo_lineas.csv", gen_balanceo(stations))

    print("C. produccion_diaria.csv")
    write_csv(DATA / "produccion_diaria.csv", gen_produccion_diaria())

    print("D. plan_accion.csv")
    write_csv(CURATED / "plan_accion.csv", gen_plan_accion())

    print("E. demanda_md.csv")
    write_csv(CURATED / "demanda_md.csv", gen_demanda())

    print("F. desperdicios.csv")
    write_csv(CURATED / "desperdicios.csv", gen_desperdicios())

    print("G. throughput_mejoras.csv")
    write_csv(CURATED / "throughput_mejoras.csv", gen_throughput())

    print("H. kanban_notifications.csv")
    write_csv(CURATED / "kanban_notifications.csv", gen_kanban())

    print("I. bom_items.csv")
    write_csv(CURATED / "bom_items.csv", gen_bom())

    print("J. dashboard_resumen.csv")
    write_csv(CURATED / "dashboard_resumen.csv", gen_dashboard_resumen())

    print("K. dashboard_estaciones.csv")
    write_csv(CURATED / "dashboard_estaciones.csv", gen_dashboard_estaciones(stations))

    print("L. flujo_proceso.csv")
    write_csv(CURATED / "flujo_proceso.csv", gen_flujo_proceso())

    print("M. herramental.csv")
    write_csv(CURATED / "herramental.csv", gen_herramental())

    print("N. inversion_15k.csv")
    write_csv(CURATED / "inversion_15k.csv", gen_inversion())

    print("O. roi_summary.csv")
    write_csv(CURATED / "roi_summary.csv", gen_roi())

    print("P. kpis_unificados.csv")
    write_csv(CURATED / "kpis_unificados.csv", gen_kpis_unificados())

    print("Q. kpis_calidad.csv")
    write_csv(CURATED / "kpis_calidad.csv", gen_kpis_calidad())

    print("R. improvements.csv")
    write_csv(CURATED / "improvements.csv", gen_improvements())

    print("S. lines.csv")
    write_csv(CURATED / "lines.csv", gen_lines())

    print("T. kanban_tasks.csv")
    write_csv(CURATED / "kanban_tasks.csv", gen_kanban_tasks())

    print("U. activities.csv")
    write_csv(CURATED / "activities.csv", gen_activities())

    print("V. ordenes_abiertas.csv")
    write_csv(CURATED / "ordenes_abiertas.csv", gen_ordenes_abiertas())

    print("W. logistica_kpis.csv")
    write_csv(CURATED / "logistica_kpis.csv", gen_logistica_kpis())

    print("X. logistica_entregas.csv")
    write_csv(CURATED / "logistica_entregas.csv", gen_logistica_entregas())

    print("Y. usuarios.json")
    usuarios = {
        "mafer": {"password": "scrypt:32768:8:1$CAe7EKxE46ys8rO0$8e05779e5bebc0e02df63e7e92fb721c8ff888675dedfe4d6961c8540bfe4c767f7a4b967cee15da01102acd828e7c54c223f66ed221494a2bc46d646237520b", "display_name": "Ma. Fernanda Rocha", "role": "admin"},
        "viewer": {"password": "scrypt:32768:8:1$Vz2JTjQYcRSEkhns$147a2f97f8d20314bb456eca45ca0b47df455cb4474af0c4fd2d375cc4df311dbea0c851b7eae6c55a1534869adc59a13507833776f5cf866c751e8c320e1a0c", "display_name": "Operador", "role": "viewer"},
        "admin": {"password": "scrypt:32768:8:1$ImnxyUQmXD73er1n$7ed406a03385240fac0be89bd213dee82cdbc83ffdb20e6860234e503bdc4a8c210c55ef1fd12f45ec3e3078819117c6343bf3f79ed0cf477b15fc8bcd796c92", "display_name": "Admin", "role": "god"},
    }
    with open(DATA / "usuarios.json", "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)
    print(f"  {DATA / 'usuarios.json'} ({len(usuarios)} users)")

    print("\nDone! All files generated successfully.")


if __name__ == "__main__":
    main()
