"""Massive Dynamic — Analytics & ROI Justification Engine."""
from flask import jsonify, render_template
from . import massive_bp
from .db import read_csv


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def _lines():
    return read_csv("lines.csv")


def _stations(line_id=None):
    stations = read_csv("stations_analytics.csv")
    if line_id:
        stations = [s for s in stations if s.get("line_id") == str(line_id)]
    return stations


def _baseline(line_id=None):
    baseline = read_csv("baseline_metrics.csv")
    if line_id:
        baseline = [b for b in baseline if b.get("line_id") == str(line_id)]
    return sorted(baseline, key=lambda x: float(x.get("value", 0) or 0), reverse=True)


def _improvements(line_id=None, status=None):
    improvements = read_csv("improvements.csv")
    if line_id:
        improvements = [i for i in improvements if i.get("line_id") == str(line_id)]
    if status:
        improvements = [i for i in improvements if i.get("status") == status]
    return improvements


def _budget_summary():
    improvements = _improvements()
    total_budget = 15000.00
    invested = sum(float(i.get("investment_usd", 0) or 0) for i in improvements)
    impl = sum(float(i.get("implementation_cost_usd", 0) or 0) for i in improvements)
    savings = sum(float(i.get("expected_savings_usd_annual", 0) or 0) for i in improvements)
    return {
        "total_budget": total_budget,
        "total_invested": invested,
        "total_impl": impl,
        "total_spent": invested + impl,
        "remaining_budget": total_budget - invested - impl,
        "total_savings_annual": savings,
        "roi_pct": round((savings / (invested + impl) * 100), 1) if (invested + impl) > 0 else 0,
        "payback_months": round(((invested + impl) / savings * 12), 1) if savings > 0 else 0,
        "total_projects": len(improvements),
    }


def _line_summary(line_id: int) -> dict:
    baseline = _baseline(line_id)
    improvements = _improvements(line_id)
    total_ct = sum(float(b.get("value") or 0) for b in baseline)
    takt_sec = 2821.0
    bottleneck = max(baseline, key=lambda x: float(x.get("value") or 0)) if baseline else None
    potential_savings = sum(
        float(i.get("expected_time_saved_sec") or 0) for i in improvements
    )
    return {
        "total_ct": total_ct,
        "takt_sec": takt_sec,
        "gap_sec": total_ct - takt_sec if total_ct > takt_sec else 0,
        "bottleneck_station": bottleneck.get("station_name") if bottleneck else None,
        "bottleneck_ct": float(bottleneck.get("value") or 0) if bottleneck else 0,
        "improvement_count": len(improvements),
        "potential_time_savings_sec": potential_savings,
        "new_ct_projected": max(total_ct - potential_savings, takt_sec),
    }


# ──────────────────────────────────────────────
#  Analytics Dashboard
# ──────────────────────────────────────────────
@massive_bp.route("/analytics")
def massive_analytics():
    lines = _lines()
    improvements = _improvements()
    budget = _budget_summary()
    baseline = _baseline()

    line_summaries = []
    for line in lines:
        line_summaries.append({
            "line": line,
            "summary": _line_summary(int(line.get("id", 0))),
        })

    top_improvements = sorted(
        improvements,
        key=lambda x: float(x.get("expected_savings_usd_annual") or 0),
        reverse=True,
    )[:5]

    return render_template(
        "massive/analytics.html",
        title="Massive Dynamic — Analitica & Justificacion ROI",
        nav_active="massive",
        lines=lines,
        line_summaries=line_summaries,
        improvements=improvements,
        budget=budget,
        baseline=baseline,
        top_improvements=top_improvements,
    )


# ──────────────────────────────────────────────
#  API endpoints for charts
# ──────────────────────────────────────────────
@massive_bp.route("/api/analytics/budget")
def massive_analytics_budget():
    return jsonify(_budget_summary())


@massive_bp.route("/api/analytics/line/<int:line_id>")
def massive_analytics_line(line_id: int):
    return jsonify(_line_summary(line_id))


@massive_bp.route("/api/analytics/improvements")
def massive_analytics_improvements():
    return jsonify(_improvements())
