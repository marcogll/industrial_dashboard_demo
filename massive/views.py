"""Massive Dynamic — Flask views/routes."""
import csv
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from . import massive_bp
from .db import read_csv


BASE_DIR = Path(__file__).resolve().parent.parent
CURATED_DIR = BASE_DIR / "data" / "curated"
FALLBACKS_DIR = BASE_DIR / "data" / "fallbacks"
TELEGRAM_EVENTS_FILE = BASE_DIR / "data" / "telegram_events.jsonl"
AVAILABLE_SECONDS = float(os.getenv("AVAILABLE_SECONDS", "39900"))
TAKT_SECONDS = float(os.getenv("TAKT_SECONDS", "2216.666667"))


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def _ensure_default_board():
    return 1


def _ensure_fizzy_user(username: str = "fizzy") -> int:
    return 1


def _log_activity(
    activity_type: str,
    description: str,
    *,
    task_id: int | None = None,
    fixture_id: int | None = None,
    duration_minutes: int | None = None,
    username: str = "fizzy",
) -> None:
    pass


def _board_data(board_id: int) -> dict:
    tasks = read_csv("kanban_tasks.csv")
    columns = read_csv("kanban_columns.csv")
    board = {"id": board_id, "name": "Produccion y Mantenimiento"}
    return {
        "board": board,
        "columns": columns or [
            {"id": 1, "name": "Propuesto", "position": 0},
            {"id": 2, "name": "Asignado", "position": 1},
            {"id": 3, "name": "In Process", "position": 2},
            {"id": 4, "name": "Bloqueado", "position": 3},
            {"id": 5, "name": "Done", "position": 4},
        ],
        "tasks": tasks,
    }


def _fixtures_stats() -> dict:
    fixtures = read_csv("herramental.csv")
    total = len(fixtures)
    by_status: dict[str, int] = {}
    by_line: dict[str, int] = {}
    in_maintenance = 0
    damaged = 0
    for f in fixtures:
        st = f.get("status", "active")
        by_status[st] = by_status.get(st, 0) + 1
        line = f.get("line", "")
        if line:
            by_line[line] = by_line.get(line, 0) + 1
        if st == "maintenance":
            in_maintenance += 1
        elif st == "inactive":
            damaged += 1
    return {
        "total": total,
        "by_status": by_status,
        "by_line": by_line,
        "in_maintenance": in_maintenance,
        "damaged": damaged,
    }


def _projects_stats() -> dict:
    projects = read_csv("plan_accion.csv")
    total = len(projects)
    active = len([p for p in projects if p.get("status") == "active"])
    completed = len([p for p in projects if p.get("status") == "completed"])
    return {"total": total, "active": active, "completed": completed}


def _overdue_tasks() -> list:
    tasks = read_csv("kanban_tasks.csv")
    today = date.today().isoformat()
    overdue = []
    for t in tasks:
        due = t.get("due_date", "")
        if due and due < today and t.get("column_name", "") != "Done":
            overdue.append(t)
    return sorted(overdue, key=lambda x: x.get("due_date", ""))[:20]


def _pct(part: float, total: float) -> float:
    if not total:
        return 0
    return round((part / total) * 100, 1)


def _as_float(value, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_csv_safe(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _load_json_safe(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _read_balanceo() -> dict[str, list[dict]]:
    rows = _read_csv_safe(CURATED_DIR / "balanceo_lineas.csv")
    if not rows:
        fallback = _load_json_safe(FALLBACKS_DIR / "balanceo_lineas.json")
        rows = fallback if fallback else []
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        linea = (row.get("linea") or row.get("line") or "GENERAL").strip().upper()
        grouped.setdefault(linea, []).append(row)
    return grouped


def _read_demanda() -> list[dict]:
    return _read_csv_safe(CURATED_DIR / "demanda_md.csv") or _load_json_safe(FALLBACKS_DIR / "demanda.json")


def _read_kanban() -> list[dict]:
    rows = _read_csv_safe(CURATED_DIR / "kanban_notifications.csv")
    for row in rows:
        try:
            days = float(row.get("days_left", "") or 999)
        except ValueError:
            days = 999
        row["_urgency"] = "critical" if days <= 3 else ("warning" if days <= 7 else "ok")
    return rows


def _telegram_tarde_count() -> int:
    if not TELEGRAM_EVENTS_FILE.exists():
        return 0
    count = 0
    try:
        for line in TELEGRAM_EVENTS_FILE.read_text(encoding="utf-8").splitlines():
            if '"turno": "tarde"' in line or '"tag": "tarde"' in line:
                count += 1
    except Exception:
        return 0
    return count


def _operations_summary() -> dict:
    balanceo = _read_balanceo()
    stations = []
    cuellos = []
    for line_name, rows in balanceo.items():
        for row in rows:
            ct = _as_float(row.get("ct_actual", 0), 0)
            takt = _as_float(row.get("takt", TAKT_SECONDS), TAKT_SECONDS)
            station = row.get("estacion", "")
            if ct > 0:
                capacity = 3600 / ct
                stations.append({
                    "line": line_name,
                    "station": station,
                    "ct": ct,
                    "takt": takt,
                    "capacity": capacity,
                })
            if takt and ct > takt:
                cuellos.append({"line": line_name, "station": station, "gap": ct - takt, "ct": ct, "takt": takt})
    bottleneck = min(stations, key=lambda s: s["capacity"]) if stations else None
    actual_units = (bottleneck["capacity"] * AVAILABLE_SECONDS / 3600) if bottleneck else 0
    target_units = AVAILABLE_SECONDS / TAKT_SECONDS if TAKT_SECONDS else 0
    demanda = _read_demanda()
    demanda_total = sum(int(float(d.get("total", 0) or 0)) for d in demanda)
    demanda_pico = max((int(float(d.get("may", 0) or 0)) for d in demanda), default=0)
    kanban = _read_kanban()
    return {
        "stations": len(stations),
        "actual_units": round(actual_units, 1),
        "target_units": round(target_units, 1),
        "gap_units": round(target_units - actual_units, 1),
        "utilization": round((actual_units / target_units * 100), 1) if target_units else 0,
        "cuellos": len(cuellos),
        "bottleneck": f"{bottleneck['line']} {bottleneck['station']}" if bottleneck else "N/A",
        "demanda_total": demanda_total,
        "demanda_pico": demanda_pico,
        "kanban_crit": len([k for k in kanban if k.get("_urgency") == "critical"]),
        "kanban_warn": len([k for k in kanban if k.get("_urgency") == "warning"]),
        "tarde_events": _telegram_tarde_count(),
    }


# ──────────────────────────────────────────────
#  HQ Dashboard
# ──────────────────────────────────────────────
@massive_bp.route("/")
def massive_hq():
    bid = _ensure_default_board()
    board_data = _board_data(bid)
    fixture_stats = _fixtures_stats()
    project_stats = _projects_stats()
    overdue = _overdue_tasks()
    ops = _operations_summary()

    total_tasks = len(board_data.get("tasks", []))
    active_tasks = len(
        [t for t in board_data.get("tasks", []) if t.get("column_name") != "Done"]
    )
    done_tasks = max(total_tasks - active_tasks, 0)
    total_fixtures = fixture_stats.get("total", 0)
    fixtures_ok = total_fixtures - fixture_stats.get("in_maintenance", 0) - fixture_stats.get("damaged", 0)
    project_total = project_stats.get("total", 0)
    project_active = project_stats.get("active", 0)

    return render_template(
        "massive/hq.html",
        title="Massive Dynamic — Centro de Control",
        nav_active="massive",
        board=board_data.get("board"),
        total_tasks=total_tasks,
        active_tasks=active_tasks,
        done_tasks=done_tasks,
        active_tasks_pct=_pct(active_tasks, total_tasks),
        done_tasks_pct=_pct(done_tasks, total_tasks),
        total_fixtures=total_fixtures,
        fixtures_ok=fixtures_ok,
        fixtures_ok_pct=_pct(fixtures_ok, total_fixtures),
        fixtures_maintenance=fixture_stats.get("in_maintenance", 0),
        fixtures_maintenance_pct=_pct(fixture_stats.get("in_maintenance", 0), total_fixtures),
        fixtures_damaged=fixture_stats.get("damaged", 0),
        fixtures_damaged_pct=_pct(fixture_stats.get("damaged", 0), total_fixtures),
        project_active=project_active,
        project_total=project_total,
        project_active_pct=_pct(project_active, project_total),
        overdue=overdue,
        overdue_pct=_pct(len(overdue), total_tasks),
        bri_model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku"),
        ops=ops,
    )


# ──────────────────────────────────────────────
#  Kanban Board
# ──────────────────────────────────────────────
@massive_bp.route("/board/<int:board_id>")
def massive_board(board_id: int):
    data = _board_data(board_id)
    if not data:
        return "Board not found", 404
    users = read_csv("users.csv") or [{"id": 1, "name": "Usuario"}]
    return render_template(
        "massive/board.html",
        title=f"Massive Dynamic — {data['board']['name']}",
        nav_active="massive",
        board=data["board"],
        columns=data["columns"],
        tasks=data["tasks"],
        users=users,
    )


@massive_bp.route("/board/<int:board_id>/task/create", methods=["POST"])
def create_task(board_id: int):
    title = request.form.get("title", "").strip()
    column_id = request.form.get("column_id", type=int)
    if not title or not column_id:
        return jsonify({"ok": False, "error": "Title and column required"}), 400
    return jsonify({"ok": True, "task_id": 0})


@massive_bp.route("/task/<int:task_id>/move", methods=["POST"])
def move_task(task_id: int):
    column_id = request.json.get("column_id", type=int) if request.is_json else None
    if not column_id:
        return jsonify({"ok": False, "error": "column_id required"}), 400
    return jsonify({"ok": True, "task_id": task_id, "column_id": column_id})


# ──────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────
@massive_bp.route("/fixtures")
def massive_fixtures():
    line_filter = request.args.get("line", "").strip()
    status_filter = request.args.get("status", "").strip()
    fixtures = read_csv("herramental.csv")
    if line_filter:
        fixtures = [f for f in fixtures if f.get("line") == line_filter]
    if status_filter:
        fixtures = [f for f in fixtures if f.get("status") == status_filter]
    lines = sorted(set(f.get("line", "") for f in fixtures if f.get("line")))
    stats = _fixtures_stats()
    return render_template(
        "massive/fixtures.html",
        title="Massive Dynamic — Catalogo de Fixtures",
        nav_active="massive",
        fixtures=fixtures,
        lines=lines,
        stats=stats,
        line_filter=line_filter,
        status_filter=status_filter,
    )


@massive_bp.route("/fixtures/create", methods=["POST"])
def create_fixture():
    code = request.form.get("code", "").strip()
    name = request.form.get("name", "").strip()
    if not code or not name:
        return jsonify({"ok": False, "error": "Code and name required"}), 400
    return jsonify({"ok": True, "fixture_id": 0})


@massive_bp.route("/fixtures/<int:fixture_id>/maintenance", methods=["POST"])
def create_maintenance(fixture_id: int):
    description = request.form.get("description", "").strip()
    if not description:
        return jsonify({"ok": False, "error": "Description required"}), 400
    return jsonify({"ok": True, "maintenance_id": 0})


# ──────────────────────────────────────────────
#  Projects
# ──────────────────────────────────────────────
@massive_bp.route("/projects")
def massive_projects():
    projects = read_csv("plan_accion.csv")
    for p in projects:
        p["progress"] = 0
    return render_template(
        "massive/projects.html",
        title="Massive Dynamic — Proyectos de Mejora",
        nav_active="massive",
        projects=projects,
    )


@massive_bp.route("/projects/create", methods=["POST"])
def create_project():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name required"}), 400
    return jsonify({"ok": True, "project_id": 0})


# ──────────────────────────────────────────────
#  Activities
# ──────────────────────────────────────────────
@massive_bp.route("/activity")
def massive_activity():
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    activities = read_csv("activities.csv")
    today_activities = [a for a in activities if str(a.get("created_at", ""))[:10] == today]
    hours_by_type: list[dict] = []
    fixtures = read_csv("herramental.csv")
    return render_template(
        "massive/activity.html",
        title="Massive Dynamic — Registro de Actividades",
        nav_active="massive",
        activities=activities,
        today_activities=today_activities,
        hours_by_type=hours_by_type,
        fixtures=fixtures,
    )


@massive_bp.route("/activity/create", methods=["POST"])
def create_activity():
    description = request.form.get("description", "").strip()
    if not description:
        return jsonify({"ok": False, "error": "Description required"}), 400
    return jsonify({"ok": True})
