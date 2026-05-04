#!/usr/bin/env python3
"""EvoNexus Log Viewer — porta 8082. Sem dependências externas."""

import json
import os
import re
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

LOGS_DIR = Path(os.environ.get("LOG_VIEWER_LOGS_DIR", "/home/evonexus/evo-nexus/ADWs/logs"))
HEARTBEATS_DIR = LOGS_DIR / "heartbeats"
DETAIL_DIR = LOGS_DIR / "detail"
PORT = int(os.environ.get("LOG_VIEWER_PORT", "8082"))
LISTEN_HOST = os.environ.get("LOG_VIEWER_HOST", "127.0.0.1")
BASE_PATH = os.environ.get("BASE_PATH", "/logs")

# ─── HTML helpers ─────────────────────────────────────────────────────────────

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.5}
a{color:#00FFA7;text-decoration:none}
a:hover{text-decoration:underline}
.container{max-width:1200px;margin:0 auto;padding:20px}
header{display:flex;align-items:center;gap:16px;margin-bottom:24px;flex-wrap:wrap}
header h1{font-size:20px;font-weight:600;color:#00FFA7}
.nav-date{display:flex;align-items:center;gap:8px}
.btn{display:inline-flex;align-items:center;padding:5px 12px;border-radius:6px;border:1px solid #30363d;background:#161b22;color:#e6edf3;cursor:pointer;font-size:13px;text-decoration:none}
.btn:hover{background:#21262d;border-color:#8b949e;text-decoration:none}
.btn-accent{background:#00FFA7;color:#0d1117;border-color:#00FFA7;font-weight:600}
.btn-accent:hover{background:#00e599;border-color:#00e599;color:#0d1117}
.date-label{font-size:15px;font-weight:600;color:#e6edf3;padding:5px 10px;background:#161b22;border:1px solid #30363d;border-radius:6px}
.filters{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}
select{background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:5px 10px;font-size:13px}
select:focus{outline:2px solid #00FFA7;outline-offset:1px}
.badge-errors{background:#da3633;color:#fff;border-radius:20px;padding:3px 10px;font-size:12px;font-weight:600}
.badge-ok{background:#1a4731;color:#00FFA7;border-radius:20px;padding:3px 10px;font-size:12px;font-weight:600}
table{width:100%;border-collapse:collapse;background:#161b22;border-radius:8px;overflow:hidden}
thead tr{background:#21262d}
th{padding:10px 14px;text-align:left;font-weight:600;color:#8b949e;font-size:12px;text-transform:uppercase;letter-spacing:.5px}
tbody tr{border-top:1px solid #21262d}
tbody tr:hover{background:#1c2128}
td{padding:10px 14px;vertical-align:middle}
.status-ok{color:#3fb950;font-weight:600}
.status-err{color:#f85149;font-weight:600}
.routine-name{font-family:monospace;font-size:13px;color:#79c0ff}
.mono{font-family:monospace;font-size:13px}
.empty{text-align:center;padding:48px;color:#8b949e}
.detail-box{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}
.detail-box h2{font-size:16px;margin-bottom:12px;color:#00FFA7}
.detail-meta{display:flex;gap:24px;flex-wrap:wrap;margin-bottom:16px}
.meta-item{display:flex;flex-direction:column;gap:2px}
.meta-label{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px}
.meta-value{font-size:14px;font-weight:600}
pre{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:16px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;font-family:monospace;font-size:13px;line-height:1.6;color:#e6edf3;max-height:600px;overflow-y:auto}
.section-title{font-size:12px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;margin:16px 0 8px}
mark{background:#3d2b00;color:#f0a500;border-radius:3px;padding:0 2px}
footer{margin-top:32px;text-align:center;color:#484f58;font-size:12px}
.heatmap-table{border-collapse:collapse;width:auto}
.heatmap-table th,.heatmap-table td{padding:4px 6px;font-size:11px;white-space:nowrap}
.heatmap-table td{border-radius:4px;min-width:28px;text-align:center}
.hm-ok{background:#1a4731;color:#00FFA7}
.hm-err{background:#2d1b1b;border:1px solid #da3633;color:#f85149}
.hm-empty{background:#21262d;color:#484f58}
.alert-banner{background:#2d1b1b;border:1px solid #da3633;border-radius:6px;padding:10px 16px;margin-bottom:16px;font-size:13px}
@media(max-width:600px){header{flex-direction:column;align-items:flex-start}td,th{padding:8px 10px}}
"""

def page(title: str, body: str) -> str:
    nav_links = f"""
<nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
  <a class="btn" href="{BASE_PATH}/">Logs</a>
  <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
  <a class="btn" href="{BASE_PATH}/costs">Custos</a>
  <a class="btn" href="{BASE_PATH}/search">Busca</a>
</nav>"""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — EvoNexus Logs</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
{body}
<footer>EvoNexus Log Viewer · {LOGS_DIR}</footer>
</div>
</body>
</html>"""

# Injeta nav_links no header — helper para views que já têm o <header> montado.
# Recebe o html do body e insere o nav antes de fechar o </header>.
def inject_nav(body: str) -> str:
    nav = f"""
<nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
  <a class="btn" href="{BASE_PATH}/">Logs</a>
  <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
  <a class="btn" href="{BASE_PATH}/costs">Custos</a>
  <a class="btn" href="{BASE_PATH}/search">Busca</a>
</nav>"""
    return body.replace("</header>", nav + "\n</header>", 1)


def escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


# ─── Business logic ───────────────────────────────────────────────────────────

def load_jsonl(target_date: date) -> list[dict]:
    path = LOGS_DIR / f"{target_date.isoformat()}.jsonl"
    if not path.exists():
        return []
    runs = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return runs


def detail_filename(timestamp: str, routine: str) -> str:
    """Converte '2026-04-17T14:54:47.060238' + 'end-of-day' → '20260417-145447-end-of-day.log'"""
    ts = timestamp[:19]  # '2026-04-17T14:54:47'
    compact = ts.replace("-", "").replace("T", "-").replace(":", "")
    return f"{compact}-{routine}.log"


def find_detail_file(timestamp: str, routine: str) -> Path | None:
    fname = detail_filename(timestamp, routine)
    candidate = DETAIL_DIR / fname
    if candidate.exists():
        return candidate
    prefix = fname[:15]  # '20260417-145447'
    if DETAIL_DIR.exists():
        for f in sorted(DETAIL_DIR.iterdir()):
            if f.name.startswith(prefix):
                return f
    return None


def list_routines(runs: list[dict]) -> list[str]:
    seen = []
    for r in runs:
        name = r.get("run", "")
        if name and name not in seen:
            seen.append(name)
    return sorted(seen)


def load_heartbeats(target_date: date) -> list[dict]:
    if not HEARTBEATS_DIR.exists():
        return []
    date_suffix = f"-{target_date.isoformat()}.jsonl"
    entries = []
    for fpath in sorted(HEARTBEATS_DIR.iterdir()):
        if not fpath.name.endswith(date_suffix):
            continue
        with fpath.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    entries.append({
                        "run_id": raw.get("run_id", ""),
                        "heartbeat_id": raw.get("heartbeat_id", fpath.stem.replace(date_suffix[1:], "").rstrip("-")),
                        "agent": raw.get("agent", "—"),
                        "status": raw.get("status", "—"),
                        "duration_ms": raw.get("duration_ms"),
                        "cost_usd": raw.get("cost_usd"),
                        "triggered_by": raw.get("triggered_by", "—"),
                        "ts": raw.get("ts", ""),
                        "error": raw.get("error"),
                    })
                except json.JSONDecodeError:
                    pass
    return entries


def find_most_recent_date_with_data() -> date | None:
    """Retorna a data mais recente que possui JSONL de rotinas."""
    if not LOGS_DIR.exists():
        return None
    candidates = []
    for f in LOGS_DIR.iterdir():
        m = re.match(r'^(\d{4}-\d{2}-\d{2})\.jsonl$', f.name)
        if m:
            try:
                candidates.append(date.fromisoformat(m.group(1)))
            except ValueError:
                pass
    return max(candidates) if candidates else None


def _dt_naive_utc(dt: datetime) -> datetime:
    """Comparações seguras entre timestamps de rotinas (ISO com TZ) e heartbeats (naive)."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def find_last_failure(days: int = 7) -> dict | None:
    """Varre os últimos N dias e retorna a falha mais recente (rotina ou heartbeat)."""
    today = date.today()
    last = None
    for i in range(days):
        d = today - timedelta(days=i)
        runs = load_jsonl(d)
        for r in runs:
            if r.get("returncode", 0) != 0:
                ts = r.get("timestamp", "")
                try:
                    dt = _dt_naive_utc(datetime.fromisoformat(ts))
                except Exception:
                    dt = datetime.min
                entry = {
                    "type": "routine",
                    "name": r.get("run", "?"),
                    "dt": dt,
                    "returncode": r.get("returncode"),
                    "date": d,
                }
                if last is None or dt > last["dt"]:
                    last = entry
        hbs = load_heartbeats(d)
        for h in hbs:
            if h.get("status") == "fail":
                ts = h.get("ts", "")
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    dt = dt.replace(tzinfo=None)  # normaliza para naive
                except Exception:
                    dt = datetime.min
                entry = {
                    "type": "heartbeat",
                    "name": h.get("heartbeat_id", "?"),
                    "dt": dt,
                    "returncode": None,
                    "date": d,
                }
                if last is None or dt > last["dt"]:
                    last = entry
    return last


# ─── Views ────────────────────────────────────────────────────────────────────

def view_index(target_date: date, routine_filter: str, status_filter: str) -> str:
    runs = load_jsonl(target_date)
    all_routines = list_routines(runs)
    heartbeats = load_heartbeats(target_date)

    if routine_filter and routine_filter != "all":
        runs = [r for r in runs if r.get("run") == routine_filter]

    # Filtro por status (rotinas)
    if status_filter == "error":
        runs = [r for r in runs if r.get("returncode", 0) != 0]
        heartbeats = [h for h in heartbeats if h.get("status") == "fail"]
    elif status_filter == "ok":
        runs = [r for r in runs if r.get("returncode", 0) == 0]
        heartbeats = [h for h in heartbeats if h.get("status") != "fail"]

    errors = sum(1 for r in runs if r.get("returncode", 0) != 0)
    hb_errors = sum(1 for h in heartbeats if h.get("status") == "fail")
    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    today = date.today()

    def nav_url(d: date) -> str:
        url = f"{BASE_PATH}/?date={d}"
        if routine_filter and routine_filter != "all":
            url += f"&routine={routine_filter}"
        if status_filter and status_filter != "all":
            url += f"&status={status_filter}"
        return url

    nav = f"""
<div class="nav-date">
  <a class="btn" href="{nav_url(prev_date)}">&#8592;</a>
  <span class="date-label">{target_date.strftime('%d/%m/%Y')}</span>
  {'<a class="btn btn-accent" href="' + nav_url(next_date) + '">&#8594;</a>' if next_date <= today else '<span class="btn" style="opacity:.3;cursor:default">&#8594;</span>'}
</div>"""

    badge = ""
    all_runs_unfiltered = load_jsonl(target_date)
    if all_runs_unfiltered:
        err_count = sum(1 for r in all_runs_unfiltered if r.get("returncode", 0) != 0)
        if err_count:
            badge = f'<span class="badge-errors">&#9888; {err_count} erro{"s" if err_count > 1 else ""}</span>'
        else:
            badge = f'<span class="badge-ok">&#10003; Rotinas OK</span>'

    hb_badge = ""
    all_hbs_unfiltered = load_heartbeats(target_date)
    if all_hbs_unfiltered:
        hb_err_count = sum(1 for h in all_hbs_unfiltered if h.get("status") == "fail")
        if hb_err_count:
            hb_badge = f'<span class="badge-errors">&#9888; {hb_err_count} heartbeat{"s" if hb_err_count > 1 else ""} com falha</span>'
        else:
            hb_badge = f'<span class="badge-ok">&#10003; Heartbeats OK</span>'

    # Dropdown de rotinas
    options = '<option value="all">Todas as rotinas</option>'
    for r in all_routines:
        sel = 'selected' if r == routine_filter else ''
        options += f'<option value="{r}" {sel}>{r}</option>'

    # Dropdown de status
    status_options = ""
    for val, label in [("all", "Todos os status"), ("error", "Só erros"), ("ok", "Só OK")]:
        sel = 'selected' if val == status_filter else ''
        status_options += f'<option value="{val}" {sel}>{label}</option>'

    filter_bar = f"""
<div class="filters">
  <select onchange="window.location='{BASE_PATH}/?date={target_date}&status={status_filter}&routine='+this.value">
    {options}
  </select>
  <select onchange="window.location='{BASE_PATH}/?date={target_date}&routine={routine_filter}&status='+this.value">
    {status_options}
  </select>
  {badge}
  {hb_badge}
</div>"""

    # Tabela de rotinas
    if not runs:
        table_body = '<tr><td colspan="7" class="empty">Nenhuma execução encontrada para este dia.</td></tr>'
    else:
        rows = []
        for r in runs:
            ts = r.get("timestamp", "")
            routine = r.get("run", "-")
            rc = r.get("returncode", 0)
            duration = r.get("duration_seconds", 0)
            tokens_in = r.get("input_tokens", 0)
            tokens_out = r.get("output_tokens", 0)
            cost = r.get("cost_usd", 0)

            try:
                dt = datetime.fromisoformat(ts)
                hora = dt.strftime("%H:%M:%S")
            except Exception:
                hora = ts[:19] if ts else "-"

            status_cls = "status-ok" if rc == 0 else "status-err"
            status_txt = "&#10003; OK" if rc == 0 else f"&#10007; {rc}"

            detail_file = find_detail_file(ts, routine)
            if detail_file:
                action = f'<a class="btn" href="{BASE_PATH}/detail/{detail_file.name}">Ver log</a>'
            else:
                action = '<span style="color:#484f58;font-size:12px">—</span>'

            tokens_total = tokens_in + tokens_out
            cost_str = f"${cost:.4f}" if cost else "—"

            rows.append(f"""<tr>
  <td class="mono">{hora}</td>
  <td><span class="routine-name">{escape(routine)}</span></td>
  <td class="{status_cls}">{status_txt}</td>
  <td class="mono">{duration:.1f}s</td>
  <td class="mono">{tokens_total:,}</td>
  <td class="mono">{cost_str}</td>
  <td>{action}</td>
</tr>""")
        table_body = "\n".join(rows)

    table = f"""
<div class="section-title" style="margin-top:0">Rotinas</div>
<table>
  <thead>
    <tr>
      <th>Horário</th>
      <th>Rotina</th>
      <th>Status</th>
      <th>Duração</th>
      <th>Tokens</th>
      <th>Custo</th>
      <th>Ação</th>
    </tr>
  </thead>
  <tbody>
    {table_body}
  </tbody>
</table>"""

    # Tabela de heartbeats
    if not heartbeats:
        hb_body = '<tr><td colspan="9" class="empty">Nenhum heartbeat encontrado para este dia.</td></tr>'
    else:
        hb_rows = []
        for h in heartbeats:
            ts = h.get("ts", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hora = dt.strftime("%H:%M:%S")
            except Exception:
                hora = ts[:19] if ts else "-"

            hb_id = escape(h.get("heartbeat_id", "—"))
            agent = escape(h.get("agent", "—"))
            status = h.get("status", "—")
            status_cls = "status-ok" if status == "success" else "status-err"
            status_txt = "&#10003; success" if status == "success" else f"&#10007; {escape(status)}"

            dur_ms = h.get("duration_ms")
            dur_str = f"{dur_ms / 1000:.1f}s" if dur_ms is not None else "—"

            cost = h.get("cost_usd")
            cost_str = f"${cost:.4f}" if cost else "—"

            trigger = escape(str(h.get("triggered_by", "—")))
            error = h.get("error")
            error_str = (f'<span style="color:#f85149;font-size:12px">{escape(str(error)[:80])}'
                         f'{"…" if error and len(str(error)) > 80 else ""}</span>'
                         if error else '<span style="color:#484f58;font-size:12px">—</span>')

            run_id = h.get("run_id", "")
            action = (f'<a class="btn" href="{BASE_PATH}/heartbeat/{target_date}/{run_id}">Ver detalhe</a>'
                      if run_id else '<span style="color:#484f58;font-size:12px">—</span>')

            hb_rows.append(f"""<tr>
  <td class="mono">{hora}</td>
  <td><span class="routine-name">{hb_id}</span></td>
  <td class="mono">{agent}</td>
  <td class="{status_cls}">{status_txt}</td>
  <td class="mono">{dur_str}</td>
  <td class="mono">{cost_str}</td>
  <td class="mono">{trigger}</td>
  <td>{error_str}</td>
  <td>{action}</td>
</tr>""")
        hb_body = "\n".join(hb_rows)

    hb_table = f"""
<div class="section-title">Heartbeats</div>
<table>
  <thead>
    <tr>
      <th>Horário</th>
      <th>Heartbeat ID</th>
      <th>Agente</th>
      <th>Status</th>
      <th>Duração</th>
      <th>Custo</th>
      <th>Trigger</th>
      <th>Erro</th>
      <th>Ação</th>
    </tr>
  </thead>
  <tbody>
    {hb_body}
  </tbody>
</table>"""

    # Resumo com totalizadores de rotinas + heartbeats (#5)
    total_cost_runs = sum(r.get("cost_usd", 0) or 0 for r in all_runs_unfiltered)
    total_cost_hbs = sum(h.get("cost_usd", 0) or 0 for h in all_hbs_unfiltered)
    total_cost = total_cost_runs + total_cost_hbs
    summary = ""
    if all_runs_unfiltered or all_hbs_unfiltered:
        summary = (f'<span style="color:#8b949e;font-size:13px">'
                   f'{len(all_runs_unfiltered)} execuções · {len(all_hbs_unfiltered)} heartbeats · '
                   f'custo total: ${total_cost:.4f}</span>')

    # Banner de última falha (#1)
    failure = find_last_failure(7)
    alert_banner = ""
    if failure:
        f_dt = failure["dt"]
        try:
            hora_str = f_dt.strftime("%H:%M")
            data_str = failure["date"].strftime("%d/%m/%Y")
        except Exception:
            hora_str = "?"
            data_str = str(failure["date"])
        rc_info = f" (rc={failure['returncode']})" if failure["returncode"] is not None else ""
        alert_banner = (
            f'<div class="alert-banner">'
            f'&#9888; Última falha: <strong>{escape(failure["name"])}</strong> '
            f'em {data_str} às {hora_str}{escape(rc_info)}'
            f'</div>'
        )

    body = f"""
<header>
  <h1>EvoNexus Logs</h1>
  {nav}
  {summary}
  <nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
    <a class="btn" href="{BASE_PATH}/">Logs</a>
    <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
    <a class="btn" href="{BASE_PATH}/costs">Custos</a>
    <a class="btn" href="{BASE_PATH}/search">Busca</a>
  </nav>
</header>
{alert_banner}
{filter_bar}
{table}
{hb_table}"""

    return page(f"Logs {target_date}", body)


def view_heartbeat(target_date: date, run_id: str) -> str:
    # Sanitize run_id: UUID chars only
    if not re.match(r'^[a-f0-9\-]{8,64}$', run_id):
        return page("Erro", '<div class="empty">ID inválido.</div>')

    date_suffix = f"-{target_date.isoformat()}.jsonl"
    entry = None
    if HEARTBEATS_DIR.exists():
        for fpath in sorted(HEARTBEATS_DIR.iterdir()):
            if not fpath.name.endswith(date_suffix):
                continue
            with fpath.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        if raw.get("run_id") == run_id:
                            entry = raw
                            break
                    except json.JSONDecodeError:
                        pass
            if entry:
                break

    if not entry:
        return page("Não encontrado", f'<div class="empty">Heartbeat run_id={escape(run_id)} não encontrado para {target_date}.</div>')

    status = entry.get("status", "—")
    status_cls = "status-ok" if status == "success" else "status-err"
    dur_ms = entry.get("duration_ms")
    dur_str = f"{dur_ms / 1000:.1f}s" if dur_ms is not None else "—"
    cost = entry.get("cost_usd")
    cost_str = f"${cost:.4f}" if cost else "—"
    error = entry.get("error") or ""

    meta_html = f"""
<div class="detail-meta">
  <div class="meta-item"><span class="meta-label">Run ID</span><span class="meta-value mono">{escape(run_id)}</span></div>
  <div class="meta-item"><span class="meta-label">Heartbeat</span><span class="meta-value routine-name">{escape(entry.get("heartbeat_id", "—"))}</span></div>
  <div class="meta-item"><span class="meta-label">Agente</span><span class="meta-value">{escape(entry.get("agent", "—"))}</span></div>
  <div class="meta-item"><span class="meta-label">Status</span><span class="meta-value {status_cls}">{escape(status)}</span></div>
  <div class="meta-item"><span class="meta-label">Duração</span><span class="meta-value">{dur_str}</span></div>
  <div class="meta-item"><span class="meta-label">Custo</span><span class="meta-value">{cost_str}</span></div>
  <div class="meta-item"><span class="meta-label">Trigger</span><span class="meta-value">{escape(str(entry.get("triggered_by", "—")))}</span></div>
  <div class="meta-item"><span class="meta-label">Timestamp</span><span class="meta-value">{escape(entry.get("ts", "—"))}</span></div>
</div>"""

    if error:
        error_block = f'<div class="section-title">Erro (stderr)</div><pre style="color:#f85149">{escape(error)}</pre>'
    else:
        error_block = '<div class="section-title">Erro (stderr)</div><pre style="color:#484f58">— sem erros —</pre>'

    body = f"""
<header>
  <h1>EvoNexus Logs</h1>
  <a class="btn" href="javascript:history.back()">&#8592; Voltar</a>
  <nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
    <a class="btn" href="{BASE_PATH}/">Logs</a>
    <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
    <a class="btn" href="{BASE_PATH}/costs">Custos</a>
    <a class="btn" href="{BASE_PATH}/search">Busca</a>
  </nav>
</header>
<div class="detail-box">
  <h2>Detalhe do Heartbeat</h2>
  {meta_html}
  {error_block}
</div>"""

    return page(f"Heartbeat {entry.get('heartbeat_id', run_id)}", body)


def view_detail(filename: str) -> str:
    # R3: whitelist de nome de arquivo — só letras, dígitos, ponto, hífen, underscore
    if not re.match(r'^[\w.\-]+\.log$', filename):
        return page("Erro", '<div class="empty">Arquivo inválido.</div>')

    path = DETAIL_DIR / filename
    if not path.exists():
        return page("Não encontrado", f'<div class="empty">Arquivo não encontrado: {escape(filename)}</div>')

    content = path.read_text(errors="replace")

    meta_section = ""
    prompt_section = ""
    stdout_section = ""
    stderr_section = ""

    lines = content.splitlines()
    current = None
    buffers: dict[str, list[str]] = {"meta": [], "prompt": [], "stdout": [], "stderr": []}

    for line in lines:
        if line.startswith("TIMESTAMP:") or line.startswith("DURATION:") or line.startswith("RETURNCODE:"):
            buffers["meta"].append(line)
        elif line == "PROMPT:":
            current = "prompt"
        elif line == "STDOUT:":
            current = "stdout"
        elif line == "STDERR:":
            current = "stderr"
        elif line.startswith("=" * 20) and "STDOUT" in line:
            current = "stdout"
        elif line.startswith("=" * 20) and "STDERR" in line:
            current = "stderr"
        elif line.startswith("=" * 20) and current not in ("stdout", "stderr"):
            current = None
        elif current:
            buffers[current].append(line)

    meta_vals: dict[str, str] = {}
    for mline in buffers["meta"]:
        if ":" in mline:
            k, _, v = mline.partition(":")
            meta_vals[k.strip()] = v.strip()

    rc = meta_vals.get("RETURNCODE", "?")
    rc_cls = "status-ok" if rc == "0" else "status-err"

    meta_html = f"""
<div class="detail-meta">
  <div class="meta-item"><span class="meta-label">Arquivo</span><span class="meta-value mono">{escape(filename)}</span></div>
  <div class="meta-item"><span class="meta-label">Timestamp</span><span class="meta-value">{escape(meta_vals.get("TIMESTAMP","—"))}</span></div>
  <div class="meta-item"><span class="meta-label">Duração</span><span class="meta-value">{escape(meta_vals.get("DURATION","—"))}</span></div>
  <div class="meta-item"><span class="meta-label">Returncode</span><span class="meta-value {rc_cls}">{escape(rc)}</span></div>
</div>"""

    def section_html(title: str, lines_list: list[str]) -> str:
        content_str = "\n".join(lines_list).strip()
        if not content_str:
            return f'<div class="section-title">{title}</div><pre style="color:#484f58">— vazio —</pre>'
        return f'<div class="section-title">{title}</div><pre>{escape(content_str)}</pre>'

    body = f"""
<header>
  <h1>EvoNexus Logs</h1>
  <a class="btn" href="javascript:history.back()">&#8592; Voltar</a>
  <nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
    <a class="btn" href="{BASE_PATH}/">Logs</a>
    <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
    <a class="btn" href="{BASE_PATH}/costs">Custos</a>
    <a class="btn" href="{BASE_PATH}/search">Busca</a>
  </nav>
</header>
<div class="detail-box">
  <h2>Detalhe da Execução</h2>
  {meta_html}
  {section_html("Prompt", buffers["prompt"])}
  {section_html("Stdout", buffers["stdout"])}
  {section_html("Stderr", buffers["stderr"])}
</div>"""

    return page(filename, body)


# ─── Nova rota: /costs ────────────────────────────────────────────────────────

def view_costs(month_str: str | None) -> str:
    today = date.today()
    if month_str:
        try:
            year, mon = (int(x) for x in month_str.split("-"))
        except Exception:
            year, mon = today.year, today.month
    else:
        year, mon = today.year, today.month

    # Navegação entre meses
    if mon == 1:
        prev_year, prev_mon = year - 1, 12
    else:
        prev_year, prev_mon = year, mon - 1
    if mon == 12:
        next_year, next_mon = year + 1, 1
    else:
        next_year, next_mon = year, mon + 1

    prev_month = f"{prev_year:04d}-{prev_mon:02d}"
    next_month = f"{next_year:04d}-{next_mon:02d}"
    curr_month = f"{year:04d}-{mon:02d}"

    # Agregar: chave → {type, runs, errors, cost, tokens}
    agg: dict[str, dict] = {}

    _, last_day = monthrange(year, mon)
    for day in range(1, last_day + 1):
        d = date(year, mon, day)
        runs = load_jsonl(d)
        for r in runs:
            key = r.get("run", "?")
            if key not in agg:
                agg[key] = {"type": "routine", "runs": 0, "errors": 0, "cost": 0.0, "tokens": 0}
            agg[key]["runs"] += 1
            if r.get("returncode", 0) != 0:
                agg[key]["errors"] += 1
            agg[key]["cost"] += r.get("cost_usd", 0) or 0
            agg[key]["tokens"] += (r.get("input_tokens", 0) or 0) + (r.get("output_tokens", 0) or 0)

        hbs = load_heartbeats(d)
        for h in hbs:
            key = h.get("heartbeat_id", "?")
            if key not in agg:
                agg[key] = {"type": "heartbeat", "runs": 0, "errors": 0, "cost": 0.0, "tokens": 0}
            agg[key]["runs"] += 1
            if h.get("status") == "fail":
                agg[key]["errors"] += 1
            agg[key]["cost"] += h.get("cost_usd", 0) or 0
            # heartbeats podem não ter tokens — tolerar ausência
            agg[key]["tokens"] += (h.get("input_tokens", 0) or 0) + (h.get("output_tokens", 0) or 0)

    # Ordenar por custo desc
    sorted_keys = sorted(agg.keys(), key=lambda k: agg[k]["cost"], reverse=True)

    total_runs = sum(v["runs"] for v in agg.values())
    total_errors = sum(v["errors"] for v in agg.values())
    total_cost = sum(v["cost"] for v in agg.values())
    total_tokens = sum(v["tokens"] for v in agg.values())

    if not agg:
        rows_html = '<tr><td colspan="7" class="empty">Nenhum dado para este mês.</td></tr>'
    else:
        rows = []
        for key in sorted_keys:
            v = agg[key]
            avg = v["cost"] / v["runs"] if v["runs"] else 0
            type_badge = ('<span style="color:#79c0ff;font-size:12px">rotina</span>'
                          if v["type"] == "routine"
                          else '<span style="color:#d2a8ff;font-size:12px">heartbeat</span>')
            rows.append(f"""<tr>
  <td><span class="routine-name">{escape(key)}</span></td>
  <td>{type_badge}</td>
  <td class="mono">{v['runs']}</td>
  <td class="mono" style="color:{'#f85149' if v['errors'] else '#484f58'}">{v['errors']}</td>
  <td class="mono">${v['cost']:.4f}</td>
  <td class="mono">{v['tokens']:,}</td>
  <td class="mono">${avg:.4f}</td>
</tr>""")
        rows.append(f"""<tr style="background:#21262d;font-weight:600">
  <td colspan="2">Total</td>
  <td class="mono">{total_runs}</td>
  <td class="mono" style="color:{'#f85149' if total_errors else '#484f58'}">{total_errors}</td>
  <td class="mono">${total_cost:.4f}</td>
  <td class="mono">{total_tokens:,}</td>
  <td class="mono">—</td>
</tr>""")
        rows_html = "\n".join(rows)

    nav_months = f"""
<div class="nav-date" style="margin-bottom:16px">
  <a class="btn" href="{BASE_PATH}/costs?month={prev_month}">&#8592;</a>
  <span class="date-label">{year:04d}-{mon:02d}</span>
  <a class="btn" href="{BASE_PATH}/costs?month={next_month}">&#8594;</a>
  <a class="btn btn-accent" href="{BASE_PATH}/costs">Mês atual</a>
</div>"""

    body = f"""
<header>
  <h1>EvoNexus Logs — Custos {curr_month}</h1>
  <nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
    <a class="btn" href="{BASE_PATH}/">Logs</a>
    <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
    <a class="btn" href="{BASE_PATH}/costs">Custos</a>
    <a class="btn" href="{BASE_PATH}/search">Busca</a>
  </nav>
</header>
{nav_months}
<table>
  <thead>
    <tr>
      <th>Nome</th>
      <th>Tipo</th>
      <th>Runs</th>
      <th>Erros</th>
      <th>Custo Total</th>
      <th>Tokens Total</th>
      <th>Custo Médio</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>"""

    return page(f"Custos {curr_month}", body)


# ─── Nova rota: /timeline ─────────────────────────────────────────────────────

def view_timeline(days: int, routine_filter: str) -> str:
    today = date.today()
    days = max(1, min(days, 30))

    date_range = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    # Coletar todos os nomes de rotinas/heartbeats no período
    all_names: dict[str, str] = {}  # name → type
    # data → name → {runs, errors}
    grid: dict[date, dict[str, dict]] = {d: {} for d in date_range}

    for d in date_range:
        runs = load_jsonl(d)
        for r in runs:
            name = r.get("run", "?")
            all_names.setdefault(name, "routine")
            if name not in grid[d]:
                grid[d][name] = {"runs": 0, "errors": 0}
            grid[d][name]["runs"] += 1
            if r.get("returncode", 0) != 0:
                grid[d][name]["errors"] += 1

        hbs = load_heartbeats(d)
        for h in hbs:
            name = h.get("heartbeat_id", "?")
            all_names.setdefault(name, "heartbeat")
            if name not in grid[d]:
                grid[d][name] = {"runs": 0, "errors": 0}
            grid[d][name]["runs"] += 1
            if h.get("status") == "fail":
                grid[d][name]["errors"] += 1

    # Aplicar filtro de rotina
    if routine_filter and routine_filter != "all":
        all_names = {k: v for k, v in all_names.items() if k == routine_filter}

    sorted_names = sorted(all_names.keys())

    # Cabeçalho de datas
    header_cells = "".join(
        f'<th style="font-size:10px;padding:4px 6px">{d.strftime("%d/%m")}</th>'
        for d in date_range
    )
    header_row = f"<tr><th>Nome</th>{header_cells}</tr>"

    # Linhas do heatmap
    hm_rows = []
    for name in sorted_names:
        cells = ""
        for d in date_range:
            cell = grid[d].get(name)
            if cell is None or cell["runs"] == 0:
                cells += f'<td class="hm-empty" title="sem execuções">·</td>'
            elif cell["errors"] > 0:
                cells += f'<td class="hm-err" title="{cell["runs"]} runs, {cell["errors"]} erros">&#10007;</td>'
            else:
                cells += f'<td class="hm-ok" title="{cell["runs"]} runs, 0 erros">&#10003;</td>'
        type_color = "#79c0ff" if all_names[name] == "routine" else "#d2a8ff"
        hm_rows.append(f'<tr><td style="color:{type_color};font-family:monospace;font-size:12px;white-space:nowrap">{escape(name)}</td>{cells}</tr>')

    hm_html = ""
    if hm_rows:
        hm_html = f"""
<div style="overflow-x:auto;margin-bottom:24px">
<table class="heatmap-table">
  <thead>{header_row}</thead>
  <tbody>{"".join(hm_rows)}</tbody>
</table>
</div>"""
    else:
        hm_html = '<div class="empty">Sem dados no período.</div>'

    # Tabela de falhas
    failures = []
    for d in reversed(date_range):
        runs = load_jsonl(d)
        for r in runs:
            if r.get("returncode", 0) != 0:
                if routine_filter and routine_filter != "all" and r.get("run") != routine_filter:
                    continue
                ts = r.get("timestamp", "")
                try:
                    hora = datetime.fromisoformat(ts).strftime("%H:%M")
                except Exception:
                    hora = "?"
                failures.append({
                    "date": d, "hora": hora,
                    "name": r.get("run", "?"), "type": "rotina",
                    "info": f'rc={r.get("returncode")}',
                })
        hbs = load_heartbeats(d)
        for h in hbs:
            if h.get("status") == "fail":
                if routine_filter and routine_filter != "all" and h.get("heartbeat_id") != routine_filter:
                    continue
                ts = h.get("ts", "")
                try:
                    hora = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M")
                except Exception:
                    hora = "?"
                failures.append({
                    "date": d, "hora": hora,
                    "name": h.get("heartbeat_id", "?"), "type": "heartbeat",
                    "info": h.get("error", "")[:60] if h.get("error") else "fail",
                })

    if failures:
        fail_rows = "".join(
            f'<tr><td class="mono">{f["date"].strftime("%d/%m/%Y")}</td>'
            f'<td class="mono">{f["hora"]}</td>'
            f'<td><span class="routine-name">{escape(f["name"])}</span></td>'
            f'<td style="color:#8b949e;font-size:12px">{f["type"]}</td>'
            f'<td class="mono status-err">{escape(f["info"])}</td></tr>'
            for f in failures
        )
        fail_table = f"""
<div class="section-title">Falhas nos últimos {days} dias</div>
<table>
  <thead>
    <tr><th>Data</th><th>Horário</th><th>Nome</th><th>Tipo</th><th>Info</th></tr>
  </thead>
  <tbody>{fail_rows}</tbody>
</table>"""
    else:
        fail_table = f'<div class="empty" style="padding:24px">Nenhuma falha nos últimos {days} dias.</div>'

    # Dropdown de rotinas para filtro
    all_name_keys = sorted(all_names.keys()) if routine_filter == "all" else sorted(
        set(n for d in date_range for n in grid[d].keys())
    )
    # Reconstruir lista completa sem filtro para o dropdown
    all_names_full: dict[str, str] = {}
    for d in date_range:
        for r in load_jsonl(d):
            all_names_full.setdefault(r.get("run", "?"), "routine")
        for h in load_heartbeats(d):
            all_names_full.setdefault(h.get("heartbeat_id", "?"), "heartbeat")
    opts = '<option value="all">Todos</option>'
    for n in sorted(all_names_full.keys()):
        sel = 'selected' if n == routine_filter else ''
        opts += f'<option value="{n}" {sel}>{n}</option>'

    filter_bar = f"""
<div class="filters">
  <select onchange="window.location='{BASE_PATH}/timeline?days={days}&routine='+this.value">
    {opts}
  </select>
  <select onchange="window.location='{BASE_PATH}/timeline?routine={routine_filter}&days='+this.value">
    <option value="7" {'selected' if days==7 else ''}>7 dias</option>
    <option value="14" {'selected' if days==14 else ''}>14 dias</option>
    <option value="30" {'selected' if days==30 else ''}>30 dias</option>
  </select>
</div>"""

    body = f"""
<header>
  <h1>EvoNexus Logs — Timeline</h1>
  <nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
    <a class="btn" href="{BASE_PATH}/">Logs</a>
    <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
    <a class="btn" href="{BASE_PATH}/costs">Custos</a>
    <a class="btn" href="{BASE_PATH}/search">Busca</a>
  </nav>
</header>
{filter_bar}
{hm_html}
{fail_table}"""

    return page("Timeline", body)


# ─── Nova rota: /search ───────────────────────────────────────────────────────

def view_search(query: str, days: int) -> str:
    days = max(1, min(days, 30))

    if not query:
        form = f"""
<div class="detail-box" style="max-width:600px">
  <h2>Busca em logs de detalhe</h2>
  <form method="get" action="{BASE_PATH}/search" style="display:flex;gap:8px;margin-top:12px">
    <input name="q" placeholder="Texto a buscar..." autofocus
           style="flex:1;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:6px 12px;color:#e6edf3;font-size:14px">
    <select name="days" style="background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:5px 10px;font-size:13px">
      <option value="7">7 dias</option>
      <option value="14">14 dias</option>
      <option value="30">30 dias</option>
    </select>
    <button type="submit" class="btn btn-accent">Buscar</button>
  </form>
</div>"""
        body = f"""
<header>
  <h1>EvoNexus Logs — Busca</h1>
  <nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
    <a class="btn" href="{BASE_PATH}/">Logs</a>
    <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
    <a class="btn" href="{BASE_PATH}/costs">Custos</a>
    <a class="btn" href="{BASE_PATH}/search">Busca</a>
  </nav>
</header>
{form}"""
        return page("Busca", body)

    today = date.today()
    results = []
    limit = 50
    query_lower = query.lower()

    if DETAIL_DIR.exists():
        # Ordenar por mtime desc para pegar mais recentes primeiro
        detail_files = sorted(DETAIL_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        for fpath in detail_files:
            if len(results) >= limit:
                break
            if not fpath.name.endswith(".log"):
                continue
            # Verificar se o arquivo é dos últimos N dias pelo nome (prefixo YYYYMMDD)
            m = re.match(r'^(\d{8})-', fpath.name)
            if m:
                try:
                    file_date = datetime.strptime(m.group(1), "%Y%m%d").date()
                    if (today - file_date).days > days:
                        continue
                except ValueError:
                    pass

            try:
                text = fpath.read_text(errors="replace")
            except Exception:
                continue

            if query_lower not in text.lower():
                continue

            # Encontrar trecho com contexto
            idx = text.lower().find(query_lower)
            start = max(0, idx - 80)
            end = min(len(text), idx + len(query) + 80)
            snippet = text[start:end]
            # Destacar match na substring
            snippet_lower = snippet.lower()
            match_start = snippet_lower.find(query_lower)
            if match_start >= 0:
                before = escape(snippet[:match_start])
                matched = escape(snippet[match_start:match_start + len(query)])
                after = escape(snippet[match_start + len(query):])
                highlighted = f"{before}<mark>{matched}</mark>{after}"
            else:
                highlighted = escape(snippet)

            # Extrair nome da rotina e data do filename
            parts = fpath.stem.split("-", 2)
            routine_name = parts[2] if len(parts) > 2 else fpath.stem
            date_str = "?"
            if m:
                try:
                    date_str = datetime.strptime(m.group(1), "%Y%m%d").strftime("%d/%m/%Y")
                except Exception:
                    pass

            results.append({
                "filename": fpath.name,
                "routine": routine_name,
                "date": date_str,
                "snippet": highlighted,
            })

    if results:
        rows = "".join(
            f'<tr>'
            f'<td class="mono">{r["date"]}</td>'
            f'<td><span class="routine-name">{escape(r["routine"])}</span></td>'
            f'<td><a class="btn" href="{BASE_PATH}/detail/{escape(r["filename"])}">Ver log</a></td>'
            f'<td style="font-family:monospace;font-size:12px;color:#8b949e">…{r["snippet"]}…</td>'
            f'</tr>'
            for r in results
        )
        result_html = f"""
<div class="section-title">{len(results)} resultado(s) para "{escape(query)}" (últimos {days} dias)</div>
<table>
  <thead><tr><th>Data</th><th>Rotina</th><th>Ação</th><th>Trecho</th></tr></thead>
  <tbody>{rows}</tbody>
</table>"""
    else:
        result_html = f'<div class="empty">Nenhum resultado para "{escape(query)}" nos últimos {days} dias.</div>'

    body = f"""
<header>
  <h1>EvoNexus Logs — Busca</h1>
  <nav style="display:flex;gap:8px;margin-left:auto;flex-wrap:wrap">
    <a class="btn" href="{BASE_PATH}/">Logs</a>
    <a class="btn" href="{BASE_PATH}/timeline">Timeline</a>
    <a class="btn" href="{BASE_PATH}/costs">Custos</a>
    <a class="btn" href="{BASE_PATH}/search">Busca</a>
  </nav>
</header>
<div class="filters" style="margin-bottom:16px">
  <form method="get" action="{BASE_PATH}/search" style="display:flex;gap:8px">
    <input name="q" value="{escape(query)}"
           style="flex:1;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:6px 12px;color:#e6edf3;font-size:14px">
    <select name="days" style="background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:5px 10px;font-size:13px">
      <option value="7" {'selected' if days==7 else ''}>7 dias</option>
      <option value="14" {'selected' if days==14 else ''}>14 dias</option>
      <option value="30" {'selected' if days==30 else ''}>30 dias</option>
    </select>
    <button type="submit" class="btn btn-accent">Buscar</button>
  </form>
</div>
{result_html}"""

    return page(f"Busca: {query}", body)


# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_html(self, html: str, status: int = 200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_redirect(self, location: str):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        raw_path = parsed.path
        if BASE_PATH and raw_path.startswith(BASE_PATH):
            path = raw_path[len(BASE_PATH):]
        else:
            path = raw_path
        path = path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/health":
            self.send_json({"status": "ok"})
            return

        if path == "/":
            date_str = qs.get("date", [None])[0]
            try:
                target_date = date.fromisoformat(date_str) if date_str else None
            except ValueError:
                target_date = None

            today = date.today()

            # Landing inteligente (#1): se sem data ou hoje sem dados, redirecionar para última data com dados
            if target_date is None:
                most_recent = find_most_recent_date_with_data()
                if most_recent and most_recent < today:
                    # Hoje ainda não tem runs — ir para a data mais recente
                    today_runs = load_jsonl(today)
                    if not today_runs:
                        self.send_redirect(f"{BASE_PATH}/?date={most_recent.isoformat()}")
                        return
                target_date = today

            routine_filter = qs.get("routine", ["all"])[0]
            status_filter = qs.get("status", ["all"])[0]
            if status_filter not in ("all", "error", "ok"):
                status_filter = "all"
            html = view_index(target_date, routine_filter, status_filter)
            self.send_html(html)
            return

        # /detail/<filename>
        m = re.match(r"^/detail/([^/]+)$", path)
        if m:
            filename = m.group(1)
            html = view_detail(filename)
            self.send_html(html)
            return

        # /heartbeat/<YYYY-MM-DD>/<run_id>
        m = re.match(r"^/heartbeat/(\d{4}-\d{2}-\d{2})/([^/]+)$", path)
        if m:
            try:
                hb_date = date.fromisoformat(m.group(1))
            except ValueError:
                hb_date = date.today()
            html = view_heartbeat(hb_date, m.group(2))
            self.send_html(html)
            return

        # /costs
        if path == "/costs":
            month_str = qs.get("month", [None])[0]
            html = view_costs(month_str)
            self.send_html(html)
            return

        # /timeline
        if path == "/timeline":
            try:
                days = int(qs.get("days", ["7"])[0])
            except ValueError:
                days = 7
            routine_filter = qs.get("routine", ["all"])[0]
            html = view_timeline(days, routine_filter)
            self.send_html(html)
            return

        # /search
        if path == "/search":
            query = qs.get("q", [""])[0].strip()
            try:
                days = int(qs.get("days", ["7"])[0])
            except ValueError:
                days = 7
            html = view_search(query, days)
            self.send_html(html)
            return

        self.send_html(page("404", '<div class="empty">Página não encontrada.</div>'), status=404)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = ThreadingHTTPServer((LISTEN_HOST, PORT), Handler)
    print(f"EvoNexus Log Viewer rodando em http://{LISTEN_HOST}:{PORT}")
    print(f"Logs dir: {LOGS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
