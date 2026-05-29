#!/usr/bin/env python3
"""Fizzy CLI for Massive Dynamic tasks and activity tracking (CSV mode)."""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
CURATED_DIR = DATA_DIR / "curated"


DEFAULT_COLUMNS = (
    ("Propuesto", 0, "#64748b"),
    ("Asignado", 1, "#2563eb"),
    ("In Process", 2, "#d97706"),
    ("Bloqueado", 3, "#dc2626"),
    ("Done", 4, "#16a34a"),
)

ACTIVITY_TYPES = (
    "task_created",
    "task_updated",
    "task_moved",
    "task_completed",
    "comment_added",
    "fixture_maintenance",
    "fixture_status_change",
    "project_created",
    "project_updated",
    "login",
    "other",
)


def read_csv(filename: str) -> list[dict[str, Any]]:
    path = CURATED_DIR / filename
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_csv_data(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_user(username: str = "fizzy") -> int:
    return 1


def ensure_board(name: str = "Produccion y Mantenimiento") -> int:
    return 1


def find_column(status: str, board_id: int | None = None) -> tuple[int, str, int]:
    return 1, status, 1


def log_activity(
    activity_type: str,
    description: str,
    *,
    username: str = "fizzy",
    task_id: int | None = None,
    fixture_id: int | None = None,
    minutes: int | None = None,
) -> int:
    print(f"[CSV mode] Actividad registrada: {description}")
    return 0


def render_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], empty: str) -> None:
    if not rows:
        print(empty)
        return
    widths = []
    for key, title in columns:
        values = ["" if row.get(key) is None else str(row.get(key)) for row in rows]
        widths.append(min(max([len(title), *[len(v) for v in values]]), 42))
    print("  ".join(title.ljust(widths[i]) for i, (_, title) in enumerate(columns)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        cells = []
        for i, (key, _) in enumerate(columns):
            value = "" if row.get(key) is None else str(row.get(key))
            if len(value) > widths[i]:
                value = value[: widths[i] - 3] + "..."
            cells.append(value.ljust(widths[i]))
        print("  ".join(cells))


def cmd_tasks(args: argparse.Namespace) -> None:
    tasks = read_csv("kanban_tasks.csv")
    if args.status:
        tasks = [t for t in tasks if t.get("column_name", "").lower() == args.status.lower()]
    elif not args.all:
        tasks = [t for t in tasks if t.get("column_name", "") != "Done"]
    if args.assignee:
        tasks = [t for t in tasks if args.assignee.lower() in t.get("assigned_name", "").lower()]
    tasks = sorted(
        tasks,
        key=lambda t: (
            0 if t.get("priority") == "critical" else 1 if t.get("priority") == "high" else 2,
            t.get("due_date", "") or "9999-12-31",
        ),
    )[:args.limit]
    render_table(
        tasks,
        [
            ("id", "ID"),
            ("column_name", "Status"),
            ("priority", "Prioridad"),
            ("assigned_name", "Responsable"),
            ("due_date", "Vence"),
            ("title", "Task"),
        ],
        "Sin tasks para el filtro.",
    )


def cmd_task_create(args: argparse.Namespace) -> None:
    print(f"[CSV mode] Task creada: {args.title} en {args.status}.")


def cmd_task_move(args: argparse.Namespace) -> None:
    print(f"[CSV mode] Task #{args.task_id} movida a {args.status}.")


def cmd_activity_list(args: argparse.Namespace) -> None:
    activities = read_csv("activities.csv")
    today = date.today()
    cutoff = today.isoformat()
    if args.days:
        from datetime import timedelta
        cutoff = (today - timedelta(days=args.days)).isoformat()
    activities = [a for a in activities if a.get("created_at", "") >= cutoff][:args.limit]
    render_table(
        activities,
        [
            ("created_at", "Fecha"),
            ("activity_type", "Tipo"),
            ("user_name", "Usuario"),
            ("related_task_id", "Task"),
            ("duration_minutes", "Min"),
            ("description", "Actividad"),
        ],
        "Sin actividades registradas.",
    )


def cmd_activity_add(args: argparse.Namespace) -> None:
    log_activity(args.type, args.description, username=args.user, task_id=args.task_id, fixture_id=args.fixture_id, minutes=args.minutes)
    print(f"[CSV mode] Actividad registrada: {args.description}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fizzy",
        description="CLI para ver tasks y trackear actividades de Massive Dynamic (CSV mode).",
    )
    parser.add_argument("--user", default=os.getenv("FIZZY_USER", "fizzy"), help="Usuario Fizzy para auditoria.")
    sub = parser.add_subparsers(dest="command", required=True)

    tasks = sub.add_parser("tasks", help="Lista tasks del tablero.")
    tasks.add_argument("--status", help="Filtra por status/columna, ej. 'In Process'.")
    tasks.add_argument("--assignee", help="Filtra por responsable.")
    tasks.add_argument("--all", action="store_true", help="Incluye Done.")
    tasks.add_argument("--limit", type=int, default=50)
    tasks.set_defaults(func=cmd_tasks)

    task_create = sub.add_parser("task-create", help="Crea una task.")
    task_create.add_argument("--title", required=True)
    task_create.add_argument("--description", default="")
    task_create.add_argument("--status", default="Propuesto")
    task_create.add_argument("--priority", choices=("low", "medium", "high", "critical"), default="medium")
    task_create.add_argument("--assignee")
    task_create.add_argument("--due")
    task_create.add_argument("--board", default="Produccion y Mantenimiento")
    task_create.set_defaults(func=cmd_task_create)

    task_move = sub.add_parser("task-move", help="Mueve una task a otro status.")
    task_move.add_argument("task_id", type=int)
    task_move.add_argument("--status", required=True)
    task_move.set_defaults(func=cmd_task_move)

    activity = sub.add_parser("activity", help="Lista actividades.")
    activity.add_argument("--days", type=int, default=7)
    activity.add_argument("--limit", type=int, default=50)
    activity.set_defaults(func=cmd_activity_list)

    activity_add = sub.add_parser("activity-add", help="Registra actividad.")
    activity_add.add_argument("description")
    activity_add.add_argument("--type", choices=ACTIVITY_TYPES, default="other")
    activity_add.add_argument("--minutes", type=int)
    activity_add.add_argument("--task-id", type=int)
    activity_add.add_argument("--fixture-id", type=int)
    activity_add.set_defaults(func=cmd_activity_add)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"Error Fizzy CLI: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
