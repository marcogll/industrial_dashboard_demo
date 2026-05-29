# Arquitectura — Massive Dynamic

## Visión General

Aplicación Flask monolítica para dashboard industrial con datos sintéticos. No requiere base de datos externa — todo se sirve desde CSVs generados por script.

```
┌─────────────────────────────────────────────────────────────┐
│                   Usuario / Navegador                        │
│  (PWA, Responsive, Theme Toggle, AI Chat)                   │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  Coolify       │
                    │  + Traefik     │
                    │  (SSL/Proxy)   │
                    └───────┬────────┘
                            │
                            ▼
                   ┌────────────────────┐
                   │ Massive Dynamic    │
                   │ Flask + Gunicorn   │
                   │      :8743         │
                   └────────┬───────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
      ┌──────────────┐ ┌──────────┐ ┌──────────┐
      │ data/        │ │templates/│ │ static/  │
      │ (CSV/JSON)   │ │ (Jinja2) │ │ (CSS/JS) │
      └──────────────┘ └──────────┘ └──────────┘
```

---

## Componentes

### Capa de Presentación (Templates Jinja2)

| Ruta | Template | Propósito |
|------|----------|-----------|
| `/` | `dashboard_master.html` | Dashboard principal con KPIs, gráficos, filtros |
| `/massive/` | `kadrix/hq.html` | Centro de control |
| `/massive/board/*` | `kadrix/board.html` | Tablero kanban |
| `/massive/fixtures` | `kadrix/fixtures.html` | Catálogo de fixtures |
| `/massive/projects` | `kadrix/projects.html` | Proyectos de mejora |
| `/massive/activity` | `kadrix/activity.html` | Registro de actividades |
| `/login` | `login.html` | Auth local (opt-in) |
| `/datos` | `datos.html` | Gestión de datasets |

**Base layout (`base.html`)**:
- Sidebar responsive con breakpoint `1024px`
- Theme toggle (dark/light) persistido en `localStorage`
- Registro automático de Service Worker para PWA

### Capa de Aplicación (`app.py`)

| Módulo | Responsabilidad |
|--------|-----------------|
| `KPI Engine` | Cálculo de KPIs, filtros por período, cuellos de botella |
| `Filtro Server-side` | `from`/`to` query params → filtra `prod_timeseries` + recalcula KPIs |
| `API REST` | `/api/*` endpoints para métricas, producción, logística, chat |
| `Auth` | Login opcional (`LOGIN_REQUIRED`), sesiones Flask |
| `Healthcheck` | `/healthz` para orquestadores |

### Blueprint Massive (`massive/`)

| Archivo | Propósito |
|---------|-----------|
| `views.py` | Rutas para HQ, kanban, fixtures, projects, activity |
| `db.py` | Lector de CSVs curados |
| `analytics.py` | Agregaciones y métricas |

---

## Flujo de Filtro por Período

```
Usuario selecciona período (7d / 30d / 90d / 180d / Todo)
                      │
              ┌───────┴───────┐
              ▼               ▼
     Server-side (curl)   Client-side (JS)
     ────────────────    ────────────────
     ?from=X&to=Y        fetch(/api/produccion/metrics?from=X&to=Y)
     → app.py filtra     → actualiza KPIs vía DOM
       prod_timeseries
     → render_template
       con prod_filtered
```

**Persistencia**: `history.replaceState` actualiza URL params sin recargar.  
**Cambio de línea**: `setGroup()` arrastra `from`/`to` en query params.  
**Sin params**: valores completos (46,865 piezas, 80.6% OEE, 1.4% scrap).

---

## Datos

### Fuentes

Todos los datos son generados por `scripts/generate_massive_dynamic_data.py` y almacenados en CSVs en `data/` y `data/curated/`.

### Datasets Principales

| Dataset | Archivo | Descripción |
|---------|---------|-------------|
| Producción | `produccion_diaria.csv` | 1,797 órdenes, Ene–Dic 2026 |
| Resumen | `dashboard_resumen.csv` | 15 KPIs agregados |
| Estaciones | `dashboard_estaciones.csv` | KPIs por estación |
| Logística KPIs | `logistica_kpis.csv` | OTD, Fill Rate mensual |
| Logística entregas | `logistica_entregas.csv` | Desempeño diario de entregas |
| Órdenes abiertas | `ordenes_abiertas.csv` | 45 órdenes con retraso |
| Líneas | `lines.csv` | Configuración de 5 líneas |
| Balanceo | `balanceo_lineas.csv` | Estaciones, CT, takt por línea |
| Demanda | `demanda_md.csv` | Demanda mensual por cliente |
| Kanban | `kanban_notifications.csv` | Alertas de inventario |
| Herramental | `herramental.csv` | Catálogo de fixtures |
| Plan acción | `plan_accion.csv` | Proyectos de mejora |

---

## Despliegue

### Docker

```bash
docker compose up -d --build
```

### Variables de Entorno Clave

| Variable | Requerido | Default |
|----------|-----------|---------|
| `PORT` | No | `8743` |
| `TAKT_SECONDS` | No | `1800` |
| `LOGIN_REQUIRED` | No | `false` |
| `OPENROUTER_API_KEY` | Para chat | — |
