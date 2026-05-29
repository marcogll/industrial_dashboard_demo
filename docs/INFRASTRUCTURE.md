# Infraestructura — Massive Dynamic

## Despliegue

El stack se despliega con Docker Compose. Se sirve con Gunicorn detrás de Traefik/Coolify.

```bash
docker compose up -d --build
```

## Servicios

### Dashboard

```yaml
services:
  dashboard:
    build: .
    container_name: md-dashboard
    env_file: [.env]
    expose: ["8743"]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8743/healthz')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Dockerfile

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8743
EXPOSE 8743
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 4 --timeout 30 --access-logfile - --error-logfile - app:app
```

## Variables de Entorno

| Variable | Default | Requerido |
|----------|---------|-----------|
| `PORT` | `8743` | No |
| `TAKT_SECONDS` | `1800` | No |
| `LOGIN_REQUIRED` | `false` | No |
| `OPENROUTER_API_KEY` | — | Para chat AI |
