<p align="center">
  <img src="massive_dynamic.svg" width="110" alt="Massive Dynamic">
</p>

<h1 align="center">Massive Dynamic — Industrial Dashboard Demo</h1>

<p align="center">
  Dashboard de producción con KPIs de doblado de lámina, simulación de 12 meses de datos, filtros por período y logística.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3a3a3a?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3a3a3a?style=flat-square&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/PWA-3a3a3a?style=flat-square&logo=pwa&logoColor=white" alt="PWA">
</p>

---

## Propósito

Demo de dashboard industrial con datos sintéticos que simulan 12 meses de producción (1,797 órdenes, Ene–Dic 2026) para 5 líneas de manufactura. Incluye:

- KPIs de producción con filtro por período (7d–180d) y por línea
- Gráfico de producción diaria actualizable
- Sección de logística (OTD, Fill Rate, Past Due, Backorder)
- Filtro server-side (curl-friendly) + client-side (JS fetch + DOM update)
- Persistencia de filtros vía query params sin recarga de página
- 3–4 semanas de "hiccup" simuladas con capacidad reducida

---

## Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12 + Flask + Gunicorn |
| Frontend | Jinja2 + Vanilla JS + CSS3 (Catppuccin Latte/Mocha) |
| Datos | CSV sintéticos generados por script |
| AI Assistant | OpenRouter (Claude Haiku) vía `/api/chat` |
| PWA | `manifest.json` + `service-worker.js` |
| Deploy | Docker + Docker Compose + Coolify |

---

## Líneas de Producción

| Línea | Estaciones | Takt | Cliente principal |
|-------|-----------|------|-------------------|
| Corte LASER | 3 | 1,800s | Toyota |
| Doblado CNC Fine | 4 | 2,400s | Honda |
| Doblado CNC Heavy | 4 | 3,200s | Mitsubishi Heavy |
| Soldadura | 4 | 2,800s | Denso |
| Pintura y Acabado | 4 | 2,200s | Yazaki |

---

## Datasets

| Archivo | Registros | Propósito |
|---------|-----------|-----------|
| `produccion_diaria.csv` | 1,797 órdenes | Producción diaria (Ene–Dic 2026) |
| `dashboard_resumen.csv` | 15 KPIs | KPIs agregados del dashboard |
| `dashboard_estaciones.csv` | — | KPIs por estación de trabajo |
| `logistica_kpis.csv` | 12 meses | OTD, Fill Rate, Past Due, Backorder |
| `logistica_entregas.csv` | diario | Desempeño de entregas diarias |
| `ordenes_abiertas.csv` | 45 órdenes | Órdenes atrasadas/pendientes |
| `lines.csv` | 5 líneas | Configuración de líneas (id, code, takt, target) |

---

## Ejecución Local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PORT=5001 python app.py
# Abrir: http://127.0.0.1:5001

# O versión Streamlit:
streamlit run streamlit_app.py

# Regenerar datos sintéticos:
python scripts/generate_massive_dynamic_data.py
```

---

## Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `APP_TITLE` | `Massive Dynamic \| Ma. Fernanda Rocha` | Título de la app |
| `PORT` | `8743` | Puerto del servidor |
| `TAKT_SECONDS` | `1800` | Takt de referencia (s) |
| `LOGIN_REQUIRED` | `false` | Auth opcional |
| `OPENROUTER_API_KEY` | — | API key para chat AI |
| `OPENROUTER_MODEL` | `anthropic/claude-3-haiku` | Modelo de chat |

---

## Endpoints API

| Ruta | Propósito |
|------|-----------|
| `/api/produccion/metrics?from=&to=` | KPIs de producción filtrados |
| `/api/produccion/timeseries?from=&to=` | Serie temporal diaria filtrada |
| `/api/logistica/kpis` | KPIs logísticos mensuales |
| `/api/logistica/orders` | Órdenes abiertas/vencidas |
| `/api/logistica/entregas` | Entregas diarias |
| `/api/chat` | Chat con asistente AI |
| `/healthz` | Healthcheck |

---

## Generación de Datos

`scripts/generate_massive_dynamic_data.py` genera datos sintéticos realistas:

- **12 meses continuos** (Ene–Dic 2026, 258 fechas)
- **Capacidad 70–90%** con variación diaria
- **3–4 semanas "hiccup"** con capacidad reducida (65–78%) y OEE bajo
- **Logística** con OTD decreciente, Fill Rate, Past Due y Backorder
- **45 órdenes abiertas** en estado Atrasada/Pendiente/Completada
