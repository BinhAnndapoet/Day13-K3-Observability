"""Dung dashboard 6 panel tu data/logs.jsonl theo contract config/dashboard.yaml.

Nguon du lieu duy nhat la file log JSONL do app sinh ra; nguong va don vi doc
tu dashboard.yaml de dashboard khong bao gio lech contract. Ket qua la mot file
HTML standalone (khong can server) dung lam evidence.

Vi du:
    python scripts/build_dashboard.py --out submission/evidence/dashboard_baseline.html
    python scripts/build_dashboard.py --label "Sau khi bat rag_slow" --out ...
"""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

DEFAULT_LOGS = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_CONFIG = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_OUT = REPO_ROOT / "submission" / "evidence" / "dashboard.html"

PANEL_ORDER = ("latency", "traffic", "errors", "cost", "tokens", "quality")


# --------------------------------------------------------------------------
# Doc log va tinh so lieu
# --------------------------------------------------------------------------
def read_records(log_path: Path) -> list[dict]:
    if not log_path.exists():
        raise SystemExit(f"Khong tim thay {log_path}. Chay API va scripts/load_test.py truoc.")
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not records:
        raise SystemExit(f"{log_path} khong co ban ghi JSON hop le.")
    return records


def parse_ts(value: str | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def minute_bucket(moment: datetime) -> str:
    return moment.strftime("%H:%M")


def percentile(values: list[float], p: int) -> float:
    """Nearest-rank, giong app/metrics.py de dashboard va /metrics khong lech nhau."""
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, math.ceil((p / 100) * len(items)) - 1))
    return float(items[idx])


def compute_metrics(records: list[dict], window_minutes: int) -> dict:
    received = [r for r in records if r.get("event") == "request_received"]
    sent = [r for r in records if r.get("event") == "response_sent"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    stamps = [ts for ts in (parse_ts(r.get("ts")) for r in records) if ts is not None]
    window_end = max(stamps) if stamps else datetime.now(timezone.utc)
    window_start = min(stamps) if stamps else window_end

    latencies = [float(r["latency_ms"]) for r in sent if isinstance(r.get("latency_ms"), (int, float))]
    costs = [float(r["cost_usd"]) for r in sent if isinstance(r.get("cost_usd"), (int, float))]
    quality = [float(r["quality_score"]) for r in sent if isinstance(r.get("quality_score"), (int, float))]

    traffic_by_minute: Counter[str] = Counter()
    for record in received:
        moment = parse_ts(record.get("ts"))
        if moment:
            traffic_by_minute[minute_bucket(moment)] += 1

    cost_by_minute: dict[str, float] = defaultdict(float)
    for record in sent:
        moment = parse_ts(record.get("ts"))
        if moment and isinstance(record.get("cost_usd"), (int, float)):
            cost_by_minute[minute_bucket(moment)] += float(record["cost_usd"])

    latency_by_minute: dict[str, list[float]] = defaultdict(list)
    for record in sent:
        moment = parse_ts(record.get("ts"))
        if moment and isinstance(record.get("latency_ms"), (int, float)):
            latency_by_minute[minute_bucket(moment)].append(float(record["latency_ms"]))

    error_breakdown = Counter(
        r.get("error_type") or "Unknown" for r in failed
    )
    total_requests = len(received)
    error_rate = (len(failed) / total_requests * 100) if total_requests else 0.0

    active_minutes = max(1, len(traffic_by_minute))

    return {
        "window_start": window_start,
        "window_end": window_end,
        "window_minutes": window_minutes,
        "records_total": len(records),
        "requests": total_requests,
        "responses": len(sent),
        "failures": len(failed),
        "latency": {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "by_minute_p95": {k: percentile(v, 95) for k, v in sorted(latency_by_minute.items())},
        },
        "traffic": {
            "count": total_requests,
            "rate_per_minute": total_requests / active_minutes,
            "by_minute": dict(sorted(traffic_by_minute.items())),
        },
        "errors": {
            "error_rate_pct": error_rate,
            "count_by_value": dict(error_breakdown.most_common()),
        },
        "cost": {
            "total": sum(costs),
            "by_minute": dict(sorted(cost_by_minute.items())),
        },
        "tokens": {
            "tokens_in": sum(int(r.get("tokens_in") or 0) for r in sent),
            "tokens_out": sum(int(r.get("tokens_out") or 0) for r in sent),
        },
        "quality": {
            "mean": (sum(quality) / len(quality)) if quality else 0.0,
            "samples": len(quality),
        },
    }


def panel_values(metrics: dict) -> dict[str, float]:
    """Gia tri duoc doi chieu voi threshold cua tung panel trong contract."""
    return {
        "latency": metrics["latency"]["p95"],
        "traffic": metrics["traffic"]["rate_per_minute"],
        "errors": metrics["errors"]["error_rate_pct"],
        "cost": metrics["cost"]["total"],
        "tokens": max(metrics["tokens"]["tokens_in"], metrics["tokens"]["tokens_out"]),
        "quality": metrics["quality"]["mean"],
    }


def threshold_ok(value: float, operator: str, limit: float) -> bool:
    return value <= limit if operator == "lte" else value >= limit


# --------------------------------------------------------------------------
# Ve SVG
# --------------------------------------------------------------------------
def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def relative_source(path: Path) -> str:
    """Hien duong dan theo repo, khong lo duong dan tuyet doi cua may ca nhan."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def bar_path(x: float, y: float, w: float, h: float, r: float = 4.0) -> str:
    """Cot bo tron 4px o dau du lieu, chan cot cam vao baseline."""
    if h <= 0:
        return ""
    r = min(r, w / 2, h)
    return (
        f"M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
        f"H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
        f"V{y + h:.1f} Z"
    )


def nice_max(value: float, threshold: float | None = None) -> tuple[float, bool]:
    """Tra ve (dinh truc, threshold co nam trong thang khong).

    Neu threshold cao gap >3 lan du lieu (vi du P95 152ms so voi SLO 3000ms) thi
    ep no vao thang se lam cot bep dí den muc khong doc duoc. Khi do ve theo du
    lieu va ghi chu threshold nam ngoai thang.
    """
    if value <= 0 and not threshold:
        return 1.0, False
    if threshold is not None and value > 0 and threshold <= value * 3:
        return max(value, threshold) * 1.25, True
    if threshold is not None and value <= 0:
        return threshold * 1.25, True
    return value * 1.25, False


def column_chart(
    items: list[tuple[str, float]],
    *,
    fmt,
    colors: list[str] | None = None,
    threshold: float | None = None,
    threshold_label: str = "",
    label_every: int = 1,
) -> str:
    """Column chart mot truc, direct label tren dau cot, threshold la duong lien net."""
    if not items:
        return '<p class="empty">Khong co du lieu trong cua so nay.</p>'

    width, height = 660.0, 240.0
    pad_l, pad_r, pad_t, pad_b = 8.0, 64.0, 28.0, 34.0
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    top, threshold_in_scale = nice_max(max(v for _, v in items), threshold)
    slot = plot_w / len(items)
    bar_w = max(6.0, min(46.0, slot - 10.0))

    parts = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
        f'preserveAspectRatio="xMidYMid meet" class="chart">'
    ]
    for frac in (0.0, 0.5, 1.0):
        y = pad_t + plot_h * frac
        cls = "axis-line" if frac == 1.0 else "grid-line"
        parts.append(f'<line class="{cls}" x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w:.1f}" y2="{y:.1f}"/>')
        parts.append(
            f'<text class="tick" x="{pad_l + plot_w + 8:.1f}" y="{y + 4:.1f}">{esc(fmt(top * (1 - frac)))}</text>'
        )

    for index, (label, value) in enumerate(items):
        h = 0.0 if top <= 0 else max(0.0, value / top * plot_h)
        x = pad_l + slot * index + (slot - bar_w) / 2
        y = pad_t + plot_h - h
        color = (colors[index] if colors and index < len(colors) else "var(--series-1)")
        parts.append(
            f'<path class="bar" d="{bar_path(x, y, bar_w, h)}" fill="{color}">'
            f"<title>{esc(label)}: {esc(fmt(value))}</title></path>"
        )
        if index % label_every == 0 or index == len(items) - 1:
            parts.append(
                f'<text class="bar-label" x="{x + bar_w / 2:.1f}" y="{max(pad_t - 8, y - 8):.1f}">'
                f"{esc(fmt(value))}</text>"
            )
            parts.append(
                f'<text class="cat-label" x="{x + bar_w / 2:.1f}" y="{pad_t + plot_h + 20:.1f}">'
                f"{esc(label)}</text>"
            )

    if threshold is not None and top > 0:
        if threshold_in_scale:
            y = pad_t + plot_h * (1 - threshold / top)
            parts.append(
                f'<line class="threshold" x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w:.1f}" y2="{y:.1f}"/>'
            )
            parts.append(
                f'<text class="threshold-label" x="{pad_l + plot_w + 8:.1f}" y="{y - 6:.1f}">'
                f"{esc(threshold_label)}</text>"
            )
        else:
            parts.append(
                f'<text class="threshold-label" x="{pad_l}" y="14">'
                f"{esc(threshold_label)} — con cach xa nguong, nam ngoai thang</text>"
            )
    parts.append("</svg>")
    return "".join(parts)


def meter(value: float, limit: float, operator: str, *, fmt, ok: bool) -> str:
    """Mot ti le doi chieu mot gioi han -> meter, khong phai pie 2 lat."""
    width, height = 660.0, 96.0
    pad_l, pad_r = 8.0, 8.0
    track_w = width - pad_l - pad_r
    track_y, track_h = 46.0, 18.0
    top = (max(value, limit) * 1.35) or 1.0
    fill_w = max(2.0, min(track_w, value / top * track_w))
    mark_x = pad_l + limit / top * track_w
    color = "var(--status-good)" if ok else "var(--status-critical)"

    return "".join(
        [
            f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
            f'preserveAspectRatio="xMidYMid meet" class="chart chart-meter">',
            f'<text class="hero" x="{pad_l}" y="30">{esc(fmt(value))}</text>',
            f'<rect class="meter-track" x="{pad_l}" y="{track_y}" width="{track_w:.1f}" '
            f'height="{track_h}" rx="4"/>',
            f'<path class="bar" d="{bar_path(pad_l, track_y, fill_w, track_h)}" fill="{color}">'
            f"<title>Gia tri hien tai: {esc(fmt(value))}</title></path>",
            f'<line class="threshold" x1="{mark_x:.1f}" y1="{track_y - 8:.1f}" '
            f'x2="{mark_x:.1f}" y2="{track_y + track_h + 8:.1f}"/>',
            f'<text class="threshold-label" x="{mark_x:.1f}" y="{track_y + track_h + 24:.1f}" '
            f'text-anchor="middle">{esc(("toi da " if operator == "lte" else "toi thieu ") + fmt(limit))}</text>',
            "</svg>",
        ]
    )


def table_view(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (
        '<details class="table-view"><summary>Xem dang bang</summary>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></details>"
    )


def status_chip(ok: bool, operator: str, limit: float, fmt) -> str:
    icon, word = ("✓", "Dat nguong") if ok else ("!", "Vuot nguong")
    cls = "chip-good" if ok else "chip-critical"
    rule = ("<= " if operator == "lte" else ">= ") + fmt(limit)
    return f'<span class="chip {cls}"><span aria-hidden="true">{icon}</span> {esc(word)} ({esc(rule)})</span>'


# --------------------------------------------------------------------------
# Panel
# --------------------------------------------------------------------------
def fmt_ms(v: float) -> str:
    return f"{v:,.0f} ms"


def fmt_int(v: float) -> str:
    return f"{v:,.0f}"


def fmt_rpm(v: float) -> str:
    return f"{v:,.1f}/ph"


def fmt_pct(v: float) -> str:
    return f"{v:,.2f}%"


def fmt_usd(v: float) -> str:
    return f"${v:,.4f}"


def fmt_score(v: float) -> str:
    return f"{v:,.2f}"


FORMATTERS = {
    "latency": fmt_ms,
    "traffic": fmt_rpm,
    "errors": fmt_pct,
    "cost": fmt_usd,
    "tokens": fmt_int,
    "quality": fmt_score,
}


def render_panel(panel: dict, metrics: dict, ok: bool) -> str:
    panel_id = panel["id"]
    fmt = FORMATTERS[panel_id]
    threshold = panel["threshold"]
    limit = float(threshold["value"])
    operator = threshold["operator"]

    if panel_id == "latency":
        data = metrics["latency"]
        chart = column_chart(
            [("P50", data["p50"]), ("P95", data["p95"]), ("P99", data["p99"])],
            fmt=fmt_ms,
            colors=["var(--ordinal-1)", "var(--ordinal-2)", "var(--ordinal-3)"],
            threshold=limit,
            threshold_label=f"SLO {limit:,.0f} ms",
        )
        table = table_view(
            ["Phut", "P95 latency (ms)"],
            [[k, f"{v:,.0f}"] for k, v in data["by_minute_p95"].items()],
        )
    elif panel_id == "traffic":
        data = metrics["traffic"]
        items = list(data["by_minute"].items())
        chart = column_chart(
            items,
            fmt=fmt_int,
            threshold=None,
            label_every=max(1, len(items) // 12),
        )
        table = table_view(["Phut", "So request"], [[k, str(v)] for k, v in items])
    elif panel_id == "errors":
        data = metrics["errors"]
        chart = meter(data["error_rate_pct"], limit, operator, fmt=fmt_pct, ok=ok)
        breakdown = list(data["count_by_value"].items())
        if breakdown:
            chart += column_chart(breakdown, fmt=fmt_int)
        table = table_view(
            ["Loai loi", "So lan"],
            [[k, str(v)] for k, v in breakdown] or [["(khong co loi)", "0"]],
        )
    elif panel_id == "cost":
        data = metrics["cost"]
        items = list(data["by_minute"].items())
        chart = column_chart(items, fmt=fmt_usd, label_every=max(1, len(items) // 8))
        table = table_view(["Phut", "Cost (USD)"], [[k, f"{v:.6f}"] for k, v in items])
        table = f'<p class="note">Tong cua so: <strong>{esc(fmt_usd(data["total"]))}</strong></p>' + table
    elif panel_id == "tokens":
        data = metrics["tokens"]
        chart = column_chart(
            [("tokens_in", data["tokens_in"]), ("tokens_out", data["tokens_out"])],
            fmt=fmt_int,
            colors=["var(--series-1)", "var(--series-2)"],
        )
        chart = (
            '<p class="legend">'
            '<span class="key"><span class="swatch" style="background:var(--series-1)"></span>tokens_in</span>'
            '<span class="key"><span class="swatch" style="background:var(--series-2)"></span>tokens_out</span>'
            "</p>" + chart
        )
        table = table_view(
            ["Field", "Tong token"],
            [["tokens_in", f"{data['tokens_in']:,}"], ["tokens_out", f"{data['tokens_out']:,}"]],
        )
    else:  # quality
        data = metrics["quality"]
        chart = meter(data["mean"], limit, operator, fmt=fmt_score, ok=ok)
        table = table_view(
            ["Chi so", "Gia tri"],
            [["quality_score trung binh", f"{data['mean']:.4f}"], ["So mau", str(data["samples"])]],
        )

    return (
        '<section class="panel">'
        f'<header class="panel-head"><h2>{esc(panel["title"])}</h2>'
        f'<p class="meta">Don vi: {esc(panel["unit"])} &middot; nguon: {esc(panel["source"])} &middot; '
        f'event: {esc(", ".join(panel["events"]))}</p>'
        f'{status_chip(ok, operator, limit, fmt)}</header>'
        f'<div class="viz-root">{chart}</div>{table}</section>'
    )


CSS = """
:root { color-scheme: light dark; }
.viz-root, body {
  --surface-1:#fcfcfb; --plane:#f9f9f7;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10);
  --series-1:#2a78d6; --series-2:#eb6834;
  --ordinal-1:#86b6ef; --ordinal-2:#2a78d6; --ordinal-3:#104281;
  --status-good:#0ca30c; --status-critical:#d03b3b;
}
@media (prefers-color-scheme: dark) {
  .viz-root, body {
    --surface-1:#1a1a19; --plane:#0d0d0d;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
    --series-1:#3987e5; --series-2:#d95926;
    --ordinal-1:#9ec5f4; --ordinal-2:#3987e5; --ordinal-3:#184f95;
  }
}
* { box-sizing: border-box; }
body {
  margin:0; padding:28px; background:var(--plane); color:var(--text-primary);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}
h1 { font-size:22px; margin:0 0 6px; }
h2 { font-size:15px; margin:0; }
.meta, .note, .empty { color:var(--text-secondary); font-size:12px; margin:4px 0 0; }
.page-head { margin-bottom:20px; }
.page-head .meta { font-size:13px; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin-bottom:20px; }
.kpi, .panel {
  background:var(--surface-1); border:1px solid var(--border); border-radius:10px; padding:16px;
}
.kpi .kpi-label { color:var(--text-secondary); font-size:12px; }
.kpi .kpi-value { font-size:30px; margin:6px 0 8px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:16px; }
.panel-head { margin-bottom:10px; }
.chart { width:100%; height:auto; display:block; margin-top:6px; }
.chart-meter { max-height:110px; }
.grid-line { stroke:var(--grid); stroke-width:1; }
.axis-line { stroke:var(--axis); stroke-width:1; }
.threshold { stroke:var(--status-critical); stroke-width:2; }
.threshold-label { fill:var(--status-critical); font-size:11px; }
.tick, .cat-label { fill:var(--muted); font-size:11px; font-variant-numeric:tabular-nums; }
.cat-label { text-anchor:middle; }
.bar-label { fill:var(--text-secondary); font-size:11px; text-anchor:middle; }
.hero { fill:var(--text-primary); font-size:26px; font-weight:600; }
.meter-track { fill:var(--grid); }
.bar { stroke:var(--surface-1); stroke-width:2; paint-order:stroke; }
.chip { display:inline-block; margin-top:8px; padding:3px 9px; border-radius:999px;
  font-size:12px; border:1px solid var(--border); color:var(--text-primary); }
.chip-good { background:color-mix(in srgb, var(--status-good) 14%, transparent); }
.chip-critical { background:color-mix(in srgb, var(--status-critical) 14%, transparent); }
.legend { display:flex; gap:14px; font-size:12px; color:var(--text-secondary); margin:0; }
.key { display:inline-flex; align-items:center; gap:6px; }
.swatch { width:10px; height:10px; border-radius:2px; display:inline-block; }
.table-view { margin-top:10px; font-size:12px; color:var(--text-secondary); }
.table-view summary { cursor:pointer; }
table { border-collapse:collapse; margin-top:8px; width:100%; font-variant-numeric:tabular-nums; }
th, td { text-align:left; padding:4px 8px; border-bottom:1px solid var(--grid); }
"""


def render_html(config: dict, metrics: dict, label: str, log_path: Path) -> str:
    dashboard = config["dashboard"]
    panels = {p["id"]: p for p in dashboard["panels"]}
    values = panel_values(metrics)

    kpi_ids = ("latency", "errors", "cost", "quality")
    kpis = []
    for panel_id in kpi_ids:
        panel = panels[panel_id]
        fmt = FORMATTERS[panel_id]
        limit = float(panel["threshold"]["value"])
        operator = panel["threshold"]["operator"]
        ok = threshold_ok(values[panel_id], operator, limit)
        kpis.append(
            '<article class="kpi">'
            f'<p class="kpi-label">{esc(panel["title"])}</p>'
            f'<p class="kpi-value">{esc(fmt(values[panel_id]))}</p>'
            f"{status_chip(ok, operator, limit, fmt)}</article>"
        )

    body_panels = []
    for panel_id in PANEL_ORDER:
        panel = panels[panel_id]
        limit = float(panel["threshold"]["value"])
        ok = threshold_ok(values[panel_id], panel["threshold"]["operator"], limit)
        body_panels.append(render_panel(panel, metrics, ok))

    start = metrics["window_start"].strftime("%Y-%m-%d %H:%M:%SZ")
    end = metrics["window_end"].strftime("%Y-%m-%d %H:%M:%SZ")
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(dashboard["title"])} — {esc(label)}</title>
<style>{CSS}</style></head>
<body>
<header class="page-head">
  <h1>{esc(dashboard["title"])} — {esc(label)}</h1>
  <p class="meta">Time range: <strong>{esc(start)} → {esc(end)}</strong> (contract:
  {esc(dashboard["time_range_minutes"])} phut, refresh {esc(dashboard["refresh_seconds"])}s) &middot;
  nguon: <strong>{esc(relative_source(log_path))}</strong> &middot;
  {esc(metrics["records_total"])} log records / {esc(metrics["requests"])} request /
  {esc(metrics["failures"])} loi &middot; dung theo contract config/dashboard.yaml</p>
</header>
<div class="kpis">{''.join(kpis)}</div>
<div class="grid">{''.join(body_panels)}</div>
</body></html>
"""


def print_summary(config: dict, metrics: dict) -> None:
    panels = {p["id"]: p for p in config["dashboard"]["panels"]}
    values = panel_values(metrics)
    print("--- Dashboard summary (nguon: data/logs.jsonl) ---")
    print(
        f"Cua so: {metrics['window_start']:%Y-%m-%d %H:%M:%SZ} -> {metrics['window_end']:%H:%M:%SZ} | "
        f"{metrics['requests']} request | {metrics['failures']} loi"
    )
    for panel_id in PANEL_ORDER:
        panel = panels[panel_id]
        limit = float(panel["threshold"]["value"])
        operator = panel["threshold"]["operator"]
        ok = threshold_ok(values[panel_id], operator, limit)
        rule = "<=" if operator == "lte" else ">="
        flag = "OK " if ok else "VI PHAM"
        print(
            f"[{flag}] {panel_id:<8} {panel['threshold']['aggregation']:<14} "
            f"= {FORMATTERS[panel_id](values[panel_id]):>12}  (nguong {rule} {limit})"
        )


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--label", default="baseline")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    records = read_records(args.logs)
    metrics = compute_metrics(records, config["dashboard"]["time_range_minutes"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_html(config, metrics, args.label, args.logs), encoding="utf-8")

    print_summary(config, metrics)
    print(f"\nDashboard: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
