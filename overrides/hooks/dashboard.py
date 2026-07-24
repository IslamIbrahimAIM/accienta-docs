"""MkDocs build hook: render the delivery dashboard from status.yml.

The portal is a static site. This hook reads a single version-controlled
status.yml and substitutes HTML for comment tokens found in page markdown:

    <!--gf:snapshot-->   30-second project status header
    <!--gf:timeline-->   interactive implementation journey
    <!--gf:tracker-->    module delivery cards
    <!--gf:updates-->    latest updates feed
    <!--gf:actions-->    client action checklist

Design rules honoured here:
  - Never invent client data. Any field left TBD renders as a neutral
    "being finalized" placeholder, never a fake number.
  - "Live in production" is derived truth (module is on the production
    branch) and is shown independently of the delivery-status judgement.
  - The hook only touches pages that contain a token, and fails soft: on any
    error the page markdown is returned unchanged rather than breaking build.
"""

from __future__ import annotations

import html
from pathlib import Path

import yaml

_STATUS: dict | None = None

STATUS_META = {
    "delivered": ("Delivered", "delivered"),
    "in_progress": ("In progress", "progress"),
    "under_review": ("Under review", "review"),
    "pending_client_approval": ("Pending your approval", "approval"),
    "blocked": ("Blocked", "blocked"),
    "not_started": ("Not started", "idle"),
}

HEALTH_META = {
    "on_track": ("On track", "ok"),
    "at_risk": ("At risk", "warn"),
    "blocked": ("Needs attention", "bad"),
}

PHASE_META = {
    "completed": ("Completed", "done"),
    "in_progress": ("In progress", "active"),
    "upcoming": ("Upcoming", "next"),
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _tbd(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip().upper() == "TBD"
    if isinstance(value, (list, tuple)):
        return len([v for v in value if not _tbd(v)]) == 0
    return False


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _pending(label: str = "Being finalized") -> str:
    return f'<span class="gf-pending">{_esc(label)}</span>'


def _int(value):
    try:
        n = int(round(float(value)))
        return max(0, min(100, n))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Fragment renderers
# --------------------------------------------------------------------------- #

def _ring(value) -> str:
    n = _int(value)
    if n is None:
        return (
            '<div class="gf-ring gf-ring--tbd" role="img" '
            'aria-label="Overall completion being finalized">'
            '<div class="gf-ring__hole"><b class="gf-ring__num">--</b>'
            '<span class="gf-ring__pct">being finalized</span></div></div>'
        )
    return (
        f'<div class="gf-ring" style="--v:{n}" role="img" '
        f'aria-label="Overall completion {n} percent">'
        f'<div class="gf-ring__hole">'
        f'<b class="gf-ring__num" data-count="{n}">{n}</b>'
        f'<span class="gf-ring__pct">%</span></div></div>'
    )


def _meter(value) -> str:
    n = _int(value)
    if n is None:
        return f'<div class="gf-mod__meterwrap">{_pending()}</div>'
    return (
        '<div class="gf-mod__meterwrap">'
        f'<div class="gf-meter" role="progressbar" aria-valuenow="{n}" '
        f'aria-valuemin="0" aria-valuemax="100">'
        f'<i class="gf-meter__fill" style="width:{n}%" data-target="{n}"></i></div>'
        f'<b class="gf-meter__num" data-count="{n}">{n}</b><span>%</span>'
        "</div>"
    )


def _chip(status) -> str:
    label, cls = STATUS_META.get(str(status), ("Being finalized", "tbd"))
    if _tbd(status):
        label, cls = "Being finalized", "tbd"
    return f'<span class="gf-chip gf-chip--{cls}">{_esc(label)}</span>'


def _live_pill(deployed) -> str:
    if deployed is True:
        return '<span class="gf-pill gf-pill--live">Live in production</span>'
    return ""


def _feature_list(items, kind) -> str:
    if _tbd(items):
        return ""
    cls = "gf-check" if kind == "delivered" else "gf-arrow"
    lis = "".join(f"<li>{_esc(x)}</li>" for x in items if not _tbd(x))
    return f'<ul class="{cls}">{lis}</ul>'


def _doc_href(prefix: str, doc) -> str:
    if _tbd(doc):
        return ""
    slug = str(doc).strip()
    if slug.endswith(".md"):
        slug = slug[:-3] + "/"
    return prefix + slug


# --------------------------------------------------------------------------- #
# Token renderers
# --------------------------------------------------------------------------- #

def render_snapshot(status: dict) -> str:
    project = status.get("project", {}) or {}
    modules = status.get("modules", []) or []
    phases = status.get("phases", []) or []

    client = project.get("client") or "the project"
    headline = project.get("headline")
    headline_html = (
        _esc(headline) if not _tbd(headline)
        else "A live view of what has been delivered, what is in progress, and what needs your input."
    )

    # Current phase label
    phase_id = project.get("current_phase")
    phase_title = None
    for p in phases:
        if p.get("id") == phase_id:
            phase_title = p.get("title")
            break
    if _tbd(phase_id) and not phase_title:
        for p in phases:
            if p.get("status") == "in_progress":
                phase_title = p.get("title")
                break
    phase_html = _esc(phase_title) if phase_title else _pending()

    # Health
    health = project.get("health")
    if _tbd(health):
        health_html = f'<span class="gf-beacon gf-beacon--tbd"></span>{_pending()}'
    else:
        hlabel, hcls = HEALTH_META.get(str(health), ("Being finalized", "tbd"))
        health_html = (
            f'<span class="gf-beacon gf-beacon--{hcls}"></span>'
            f'<span class="gf-beacon__label">{_esc(hlabel)}</span>'
        )

    live_count = sum(1 for m in modules if m.get("deployed") is True)
    delivered_count = sum(1 for m in modules if m.get("status") == "delivered")

    return f"""<section class="gf-cockpit gf-reveal">
  <div class="gf-cockpit__intro">
    <p class="gf-eyebrow">Implementation status</p>
    <h1 class="gf-cockpit__title">{_esc(client)} delivery</h1>
    <p class="gf-cockpit__headline">{headline_html}</p>
  </div>
  <div class="gf-cockpit__panel">
    <div class="gf-cockpit__ring">
      {_ring(project.get("overall_completion"))}
      <p class="gf-cockpit__ringcap">Overall completion</p>
    </div>
    <dl class="gf-cockpit__stats">
      <div class="gf-kpi">
        <dt>Current phase</dt>
        <dd>{phase_html}</dd>
      </div>
      <div class="gf-kpi">
        <dt>Project health</dt>
        <dd class="gf-kpi__health">{health_html}</dd>
      </div>
      <div class="gf-kpi">
        <dt>Live in production</dt>
        <dd><b class="gf-kpi__big" data-count="{live_count}">{live_count}</b> capabilities</dd>
      </div>
      <div class="gf-kpi">
        <dt>Marked delivered</dt>
        <dd><b class="gf-kpi__big" data-count="{delivered_count}">{delivered_count}</b> capabilities</dd>
      </div>
    </dl>
  </div>
</section>"""


def render_timeline(status: dict) -> str:
    phases = status.get("phases", []) or []
    if not phases:
        return ""
    nodes = []
    panels = []
    active_idx = 0
    for i, p in enumerate(phases):
        st = p.get("status")
        plabel, pcls = PHASE_META.get(str(st), ("Being finalized", "tbd"))
        if st == "in_progress":
            active_idx = i
        title = _esc(p.get("title") or f"Phase {i + 1}")
        detail = p.get("detail")
        detail_html = _esc(detail) if not _tbd(detail) else "Details being finalized."
        nodes.append(
            f'<button class="gf-phase gf-phase--{pcls}" role="tab" '
            f'id="gf-tab-{i}" aria-controls="gf-panel-{i}" '
            f'data-index="{i}" aria-selected="{"true" if i == active_idx else "false"}">'
            f'<span class="gf-phase__dot"></span>'
            f'<span class="gf-phase__title">{title}</span>'
            f'<span class="gf-phase__state">{_esc(plabel)}</span>'
            f"</button>"
        )
        panels.append(
            f'<div class="gf-phase-panel" role="tabpanel" id="gf-panel-{i}" '
            f'aria-labelledby="gf-tab-{i}"{"" if i == active_idx else " hidden"}>'
            f"<p>{detail_html}</p></div>"
        )
    return f"""<section class="gf-timeline gf-reveal">
  <h2 class="gf-h2">Implementation journey</h2>
  <div class="gf-spine" role="tablist" aria-label="Implementation phases">
    {''.join(nodes)}
  </div>
  <div class="gf-phase-panels">
    {''.join(panels)}
  </div>
</section>"""


def render_tracker(status: dict, prefix: str, compact: bool = False) -> str:
    modules = status.get("modules", []) or []
    if not modules:
        return ""
    cards = []
    for m in modules:
        title = _esc(m.get("title") or m.get("key") or "Capability")
        summary = _esc(m.get("summary") or "")
        chip = _chip(m.get("status"))
        live = _live_pill(m.get("deployed"))
        meter = _meter(m.get("completion"))
        delivered = _feature_list(m.get("delivered"), "delivered")
        pending = _feature_list(m.get("pending"), "pending")
        href = _doc_href(prefix, m.get("doc"))
        doc_link = (
            f'<a class="gf-mod__doc" href="{_esc(href)}">View documentation'
            '<span aria-hidden="true"> &rarr;</span></a>' if href else ""
        )
        more = ""
        if not compact and (delivered or pending):
            cols = ""
            if delivered:
                cols += f'<div class="gf-col"><p class="gf-col__h">Delivered</p>{delivered}</div>'
            if pending:
                cols += f'<div class="gf-col"><p class="gf-col__h">Pending</p>{pending}</div>'
            more = (
                '<details class="gf-mod__more"><summary>Feature breakdown</summary>'
                f'<div class="gf-cols">{cols}</div></details>'
            )
        cards.append(f"""<article class="gf-mod gf-reveal">
    <div class="gf-mod__head">
      <h3 class="gf-mod__title">{title}</h3>
      {chip}
    </div>
    <p class="gf-mod__summary">{summary}</p>
    {meter}
    <div class="gf-mod__foot">{live}{doc_link}</div>
    {more}
  </article>""")
    heading = "" if compact else '<h2 class="gf-h2">Delivered modules</h2>'
    return f'{heading}<div class="gf-modgrid">{"".join(cards)}</div>'


def render_updates(status: dict) -> str:
    updates = status.get("recent_updates", []) or []
    real = [u for u in updates if not (_tbd(u.get("text")) and _tbd(u.get("date")))]
    if not real:
        body = f'<li class="gf-feed__empty">{_pending("The latest updates will appear here")}</li>'
    else:
        items = []
        for u in real:
            date = _esc(u.get("date")) if not _tbd(u.get("date")) else ""
            kind = str(u.get("type") or "").strip().lower()
            kcls = kind if kind in ("completed", "started", "changed") else "changed"
            text = _esc(u.get("text")) if not _tbd(u.get("text")) else "Update being finalized"
            items.append(
                f'<li class="gf-feed__item gf-feed__item--{kcls}">'
                f'<time class="gf-feed__date">{date}</time>'
                f'<span class="gf-feed__text">{text}</span></li>'
            )
        body = "".join(items)
    return f"""<section class="gf-updates gf-reveal">
  <h2 class="gf-h2">Latest updates</h2>
  <ul class="gf-feed">{body}</ul>
</section>"""


def render_actions(status: dict) -> str:
    actions = status.get("client_actions", []) or []
    real = [a for a in actions if not _tbd(a.get("text"))]
    if not real:
        body = f'<li class="gf-actions__empty">{_pending("No actions needed from you right now")}</li>'
    else:
        items = []
        for a in real:
            done = a.get("done") is True
            cls = "is-done" if done else ""
            mark = "&#10003;" if done else ""
            items.append(
                f'<li class="gf-action {cls}">'
                f'<span class="gf-action__box" aria-hidden="true">{mark}</span>'
                f'<span class="gf-action__text">{_esc(a.get("text"))}</span></li>'
            )
        body = "".join(items)
    return f"""<section class="gf-your-actions gf-reveal">
  <h2 class="gf-h2">Your actions</h2>
  <p class="gf-your-actions__lead">Items that need your input to keep the project moving.</p>
  <ul class="gf-actions">{body}</ul>
</section>"""


# --------------------------------------------------------------------------- #
# MkDocs events
# --------------------------------------------------------------------------- #

def on_config(config):
    global _STATUS
    try:
        status_path = Path(config["config_file_path"]).parent / "status.yml"
        _STATUS = yaml.safe_load(status_path.read_text()) or {}
    except Exception:
        _STATUS = {}
    return config


def on_page_markdown(markdown, *, page, config, files):
    if "<!--gf:" not in markdown:
        return markdown
    status = _STATUS if isinstance(_STATUS, dict) else {}
    try:
        depth = page.file.src_uri.count("/")
        prefix = "../" * depth
        replacements = {
            "<!--gf:snapshot-->": render_snapshot(status),
            "<!--gf:timeline-->": render_timeline(status),
            "<!--gf:tracker-->": render_tracker(status, prefix, compact=False),
            "<!--gf:tracker-compact-->": render_tracker(status, prefix, compact=True),
            "<!--gf:updates-->": render_updates(status),
            "<!--gf:actions-->": render_actions(status),
        }
        for token, value in replacements.items():
            if token in markdown:
                markdown = markdown.replace(token, value)
    except Exception:
        return markdown
    return markdown
