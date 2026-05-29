"""
BRIS Dashboard - Streamlit Edition
Dashboard interactivo para KPIs de ensamble Massive Dynamic.
Correr localmente:  streamlit run streamlit_app.py
"""

import csv
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Massive Dynamic - Doblado de Lámina",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CURATED_DIR = BASE_DIR / "data" / "curated"
FALLBACKS_DIR = DATA_DIR / "fallbacks"

AVAILABLE_SECONDS = 39900.0
TAKT_SECONDS = 2216.666667


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def as_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_fallback(filename: str) -> list[dict]:
    p = FALLBACKS_DIR / filename
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


# ──────────────────────────────────────────────
#  Data loaders
# ──────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_stations():
    path = DATA_DIR / "stations.csv"
    rows = read_csv(path)
    stations = []
    for i, row in enumerate(rows):
        name = (row.get("station_name") or row.get("station") or "").strip()
        if not name:
            continue
        stations.append(
            {
                "id": (row.get("station_id") or str(i + 1)).strip(),
                "name": name,
                "time_seconds": as_float(row.get("time_seconds")),
                "operators": as_float(row.get("operators"), 1),
                "capacity_per_hour": (
                    as_float(row.get("operators"), 1) * 3600 / as_float(row.get("time_seconds"))
                    if as_float(row.get("time_seconds")) > 0
                    else 0
                ),
            }
        )
    return pd.DataFrame(stations)


@st.cache_data(ttl=60)
def load_balanceo():
    rows = read_csv(CURATED_DIR / "balanceo_lineas.csv")
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_plan():
    rows = read_csv(CURATED_DIR / "plan_accion.csv")
    if not rows:
        rows = load_fallback("plan_accion.json")
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_demanda():
    rows = read_csv(CURATED_DIR / "demanda_md.csv")
    if not rows:
        rows = load_fallback("demanda.json")
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_kanban():
    rows = read_csv(CURATED_DIR / "kanban_notifications.csv")
    if not rows:
        return pd.DataFrame()
    for r in rows:
        try:
            days = float(r.get("days_left", 0) or 0)
        except ValueError:
            days = 0
        r["_urgency"] = "critical" if days <= 3 else "warning" if days <= 7 else "ok"
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_bom():
    rows = read_csv(CURATED_DIR / "bom_items.csv")
    return pd.DataFrame(rows[:50])  # limit for speed


@st.cache_data(ttl=60)
def load_desperdicios():
    rows = read_csv(CURATED_DIR / "desperdicios.csv")
    return pd.DataFrame(rows if rows else load_fallback("desperdicios.json"))


@st.cache_data(ttl=60)
def load_throughput():
    rows = read_csv(CURATED_DIR / "throughput_mejoras.csv")
    return pd.DataFrame(rows if rows else load_fallback("throughput.json"))


# ──────────────────────────────────────────────
#  Metrics
# ──────────────────────────────────────────────
def compute_metrics(stations_df: pd.DataFrame):
    if stations_df.empty:
        return {}
    total_work = stations_df["time_seconds"].sum()
    target_units = AVAILABLE_SECONDS / TAKT_SECONDS
    bottleneck = stations_df.loc[stations_df["capacity_per_hour"].idxmin()]
    actual_units = bottleneck["capacity_per_hour"] * AVAILABLE_SECONDS / 3600
    gap_units = target_units - actual_units
    takt_util = (actual_units / target_units * 100) if target_units else 0
    return {
        "total_work_seconds": total_work,
        "total_work_minutes": total_work / 60,
        "target_units": target_units,
        "actual_units": actual_units,
        "gap_units": gap_units,
        "takt_utilization": takt_util,
        "bottleneck_name": bottleneck["name"],
        "bottleneck_capacity": bottleneck["capacity_per_hour"],
    }


# ──────────────────────────────────────────────
#  Sidebar
# ──────────────────────────────────────────────
st.sidebar.title("🏭 Massive Dynamic")
st.sidebar.caption("Massive Dynamic — Doblado de Lámina")
page = st.sidebar.radio(
    "Navegacion",
    ["KPIs", "Produccion", "Plan de Accion", "Demanda", "Partes / BOM", "Kanban"],
)

# ──────────────────────────────────────────────
#  KPIs Page
# ──────────────────────────────────────────────
if page == "KPIs":
    st.header("KPIs Operativos")

    stations_df = load_stations()
    metrics = compute_metrics(stations_df)

    if metrics:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Capacidad actual", f"{metrics['actual_units']:.1f} pzs/turno")
        c2.metric("Meta por takt", f"{metrics['target_units']:.1f} pzs/turno")
        c3.metric(
            "Gap vs meta",
            f"{metrics['gap_units']:.1f} pzs",
            delta="Faltante" if metrics["gap_units"] > 0 else "OK",
            delta_color="inverse",
        )
        c4.metric("Utilizacion takt", f"{metrics['takt_utilization']:.1f}%")
        c5.metric("Trabajo total", f"{metrics['total_work_minutes']:.1f} min")

        st.divider()
        st.subheader("Capacidad por estacion")

        if not stations_df.empty:
            max_cap = stations_df["capacity_per_hour"].max()
            stations_df["bar_width"] = stations_df["capacity_per_hour"] / max_cap * 100 if max_cap else 0
            stations_df["takt_gap"] = stations_df["time_seconds"] - TAKT_SECONDS
            stations_df["status"] = stations_df.apply(
                lambda r: "critical"
                if r["name"] == metrics["bottleneck_name"]
                else "warning" if r["takt_gap"] > 0 else "ok",
                axis=1,
            )

            color_map = {"critical": "#dc2626", "warning": "#d97706", "ok": "#16a34a"}
            fig = px.bar(
                stations_df.sort_values("capacity_per_hour", ascending=True),
                x="capacity_per_hour",
                y="name",
                orientation="h",
                color="status",
                color_discrete_map=color_map,
                labels={"capacity_per_hour": "Piezas/hora", "name": "Estacion"},
                height=350,
            )
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Detalle de estaciones")
            display = stations_df[["name", "time_seconds", "operators", "capacity_per_hour", "status"]].copy()
            display.columns = ["Estacion", "Tiempo (s)", "Operadores", "Pzs/h", "Status"]
            st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos de estaciones cargados.")

# ──────────────────────────────────────────────
#  Produccion Page
# ──────────────────────────────────────────────
elif page == "Produccion":
    st.header("Produccion — Balanceo de Lineas")

    bal_df = load_balanceo()
    if not bal_df.empty and "linea" in bal_df.columns:
        lineas = bal_df["linea"].unique().tolist()
        tabs = st.tabs(lineas + ["Desperdicios", "Throughput"])

        for i, linea in enumerate(lineas):
            with tabs[i]:
                df_linea = bal_df[bal_df["linea"] == linea]
                st.dataframe(df_linea, use_container_width=True, hide_index=True)

        with tabs[-2]:
            desp_df = load_desperdicios()
            if not desp_df.empty:
                fig = px.pie(
                    desp_df,
                    values="tiempo_seg",
                    names="categoria",
                    title="Composicion del tiempo",
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(desp_df, use_container_width=True, hide_index=True)

        with tabs[-1]:
            tp_df = load_throughput()
            if not tp_df.empty:
                st.dataframe(tp_df, use_container_width=True, hide_index=True)
                if "pzas_hr" in tp_df.columns:
                    fig = px.bar(
                        tp_df,
                        x="etapa",
                        y="pzas_hr",
                        labels={"etapa": "Etapa", "pzas_hr": "Piezas/hora"},
                        height=300,
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de balanceo. Verifica `data/curated/balanceo_lineas.csv`")

# ──────────────────────────────────────────────
#  Plan de Accion Page
# ──────────────────────────────────────────────
elif page == "Plan de Accion":
    st.header("Plan de Accion")

    plan_df = load_plan()
    if not plan_df.empty:
        prioridad_filter = st.multiselect(
            "Filtrar por prioridad",
            options=["ALTA", "MEDIA", "BAJA"],
            default=["ALTA", "MEDIA", "BAJA"],
        )
        filtered = plan_df[plan_df["prioridad"].isin(prioridad_filter)] if prioridad_filter else plan_df

        c1, c2, c3 = st.columns(3)
        c1.metric("ALTA", len(plan_df[plan_df["prioridad"] == "ALTA"]))
        c2.metric("MEDIA", len(plan_df[plan_df["prioridad"] == "MEDIA"]))
        c3.metric("BAJA", len(plan_df[plan_df["prioridad"] == "BAJA"]))

        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de plan de accion.")

# ──────────────────────────────────────────────
#  Demanda Page
# ──────────────────────────────────────────────
elif page == "Demanda":
    st.header("Demanda Massive Dynamic")

    dem_df = load_demanda()
    if not dem_df.empty:
        st.dataframe(dem_df, use_container_width=True, hide_index=True)

        # Simple chart if numeric columns exist
        months = ["dic", "ene", "feb", "mar", "abr", "may"]
        if all(m in dem_df.columns for m in months):
            melted = dem_df.melt(
                id_vars=["programa", "part_number"],
                value_vars=months,
                var_name="mes",
                value_name="unidades",
            )
            melted["unidades"] = pd.to_numeric(melted["unidades"], errors="coerce").fillna(0)
            fig = px.bar(
                melted,
                x="mes",
                y="unidades",
                color="part_number",
                labels={"mes": "Mes", "unidades": "Unidades"},
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin datos de demanda.")

# ──────────────────────────────────────────────
#  Partes / BOM Page
# ──────────────────────────────────────────────
elif page == "Partes / BOM":
    st.header("Partes / BOM")

    bom_df = load_bom()
    if not bom_df.empty:
        search = st.text_input("Buscar por parte, descripcion o parent...")
        if search:
            s = search.lower()
            bom_df = bom_df[
                bom_df.astype(str).apply(
                    lambda row: any(s in str(v).lower() for v in row), axis=1
                )
            ]
        st.dataframe(bom_df, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos BOM.")

# ──────────────────────────────────────────────
#  Kanban Page
# ──────────────────────────────────────────────
elif page == "Kanban":
    st.header("Kanban — Notificaciones")

    kb_df = load_kanban()
    if not kb_df.empty:
        color_map = {"critical": "#dc2626", "warning": "#d97706", "ok": "#16a34a"}
        if "_urgency" in kb_df.columns:
            c1, c2, c3 = st.columns(3)
            c1.metric("Critical", len(kb_df[kb_df["_urgency"] == "critical"]))
            c2.metric("Warning", len(kb_df[kb_df["_urgency"] == "warning"]))
            c3.metric("OK", len(kb_df[kb_df["_urgency"] == "ok"]))

            fig = px.bar(
                kb_df.sort_values("days_left"),
                x="part_number",
                y="days_left",
                color="_urgency",
                color_discrete_map=color_map,
                labels={"part_number": "Parte", "days_left": "Dias restantes"},
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(kb_df, use_container_width=True, hide_index=True)
    else:
        st.info("Sin notificaciones kanban.")
