"""Generate the profile header and the system card as SVG files.

Three layers, kept apart so each can be tested on its own:

    fetch_github()  network: reads public data from the GitHub REST API
    summarize()     pure: turns API responses into a small card-data dict
    render_*()      pure: turns card data into SVG text (deterministic)

Standard library only. Run locally:

    python scripts/generate_svgs.py                  # fetch live data, write assets/
    python scripts/generate_svgs.py --data card.json # render from a saved data file
    python scripts/generate_svgs.py --header         # also rewrite the static header

If the API cannot be reached, nothing is written and the previously committed
SVGs stay in place, so the README never shows a broken or half-written card.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

THEMES = {
    "dark": {
        "bg": "#0d1117", "panel": "#161b22", "border": "#30363d",
        "grid": "#1b222c", "text": "#e6edf3", "muted": "#8b949e",
        "accent": "#58a6ff", "accent2": "#a371f7",
        "ok": "#3fb950", "bad": "#f85149",
    },
    "light": {
        "bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de",
        "grid": "#eef1f4", "text": "#1f2328", "muted": "#59636e",
        "accent": "#0969da", "accent2": "#8250df",
        "ok": "#1a7f37", "bad": "#cf222e",
    },
}
PILLAR_COLOURS = {"Vision": "accent2", "Retrieval": "accent", "Reliability": "ok"}

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


# ---------------------------------------------------------------- helpers

def esc(text: object) -> str:
    """Escape text for use inside SVG elements and double-quoted attributes."""
    return _xml_escape(str(text), {'"': "&quot;", "'": "&apos;"})


def truncate(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def month_year(iso: str | None) -> str | None:
    """'2026-10-23T05:21:26Z' -> 'Oct 2026'. Returns None for missing/invalid input."""
    if not iso or len(iso) < 7:
        return None
    try:
        year, month = int(iso[:4]), int(iso[5:7])
    except ValueError:
        return None
    if not 1 <= month <= 12:
        return None
    return f"{MONTHS[month - 1]} {year}"


def iso_date(iso: str | None) -> str | None:
    if not iso or len(iso) < 10 or iso[4] != "-" or iso[7] != "-":
        return None
    return iso[:10]


# ---------------------------------------------------------------- fetch (I/O)

def _get(path: str, token: str | None) -> object:
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "profile-system-card",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def is_repo_workflow(run: dict) -> bool:
    """True for workflows the repo defines. Excludes GitHub's built-in runs such as
    'pages build and deployment' (path 'dynamic/...'), which are not tests."""
    return str(run.get("path", "")).startswith(".github/workflows/")


def fetch_github(owner: str, featured: list[dict], token: str | None) -> tuple[list, dict]:
    """Return (repos, latest completed repo-defined workflow run per featured repo or None)."""
    repos = _get(f"/users/{owner}/repos?type=owner&per_page=100", token)
    by_name = {r["name"]: r for r in repos}
    runs: dict[str, dict | None] = {}
    for item in featured:
        repo = by_name.get(item["repo"])
        if repo is None:
            runs[item["repo"]] = None
            continue
        branch = repo.get("default_branch", "main")
        try:
            data = _get(f"/repos/{owner}/{item['repo']}/actions/runs"
                        f"?branch={branch}&status=completed&per_page=20", token)
            workflow_runs = [r for r in data.get("workflow_runs") or [] if is_repo_workflow(r)]
            runs[item["repo"]] = workflow_runs[0] if workflow_runs else None
        except urllib.error.HTTPError:
            # Actions disabled or not visible: report "no CI" rather than failing the card.
            runs[item["repo"]] = None
    return repos, runs


# ---------------------------------------------------------------- summarize (pure)

def summarize(repos: list[dict], runs: dict, config: dict) -> dict:
    owner = config["owner"]
    by_name = {r.get("name"): r for r in repos}
    originals = [r for r in repos
                 if not r.get("fork") and not r.get("archived") and r.get("name") != owner]
    pushes = sorted(p for p in (iso_date(r.get("pushed_at")) for r in originals) if p)

    projects = []
    for item in config["featured"]:
        repo = by_name.get(item["repo"])
        run = runs.get(item["repo"])
        ci = None
        if run:
            ci = "passing" if run.get("conclusion") == "success" else "failing"
        projects.append({
            "label": item["label"],
            "pillar": item["pillar"],
            "available": repo is not None and not repo.get("fork", False),
            "updated": month_year(repo.get("pushed_at")) if repo else None,
            "ci": ci,
        })
    return {
        "owner": owner,
        "thesis": config.get("thesis", ""),
        "latest_activity": pushes[-1] if pushes else None,
        "projects": projects,
    }


# ---------------------------------------------------------------- render (pure)

def _grid(width: int, height: int, colour: str, step: int = 24) -> str:
    lines = [f'<path d="M{x} 0V{height}" />' for x in range(step, width, step)]
    lines += [f'<path d="M0 {y}H{width}" />' for y in range(step, height, step)]
    return f'<g stroke="{colour}" stroke-width="1">' + "".join(lines) + "</g>"


def render_card(data: dict, theme: str) -> str:
    t = THEMES[theme]
    projects = data.get("projects") or []
    width, row_h, top = 840, 34, 132
    height = top + row_h * max(len(projects), 1) + 52

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="card-title card-desc">',
        f'<title id="card-title">{esc(data.get("owner", ""))} system card</title>',
        '<desc id="card-desc">Featured projects with their engineering area, '
        'last update and continuous-integration status, generated from the GitHub API.</desc>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" '
        f'fill="{t["bg"]}" stroke="{t["border"]}" />',
        # title bar
        f'<path d="M0.5 12.5a12 12 0 0 1 12-12h{width - 25}a12 12 0 0 1 12 12V36H0.5z" '
        f'fill="{t["panel"]}" />',
        f'<path d="M0 36H{width}" stroke="{t["border"]}" />',
    ]
    for i, colour in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{22 + i * 18}" cy="18" r="5.5" fill="{colour}" />')
    out.append(f'<text x="{width / 2:g}" y="23" text-anchor="middle" font-family="{MONO}" '
               f'font-size="12" fill="{t["muted"]}">{esc(data.get("owner", ""))} — system card</text>')

    thesis = truncate(data.get("thesis", ""), 78)
    out += [
        f'<text x="28" y="70" font-family="{MONO}" font-size="13" fill="{t["accent"]}">'
        f'$ status --featured</text>',
        f'<text x="28" y="96" font-family="{SANS}" font-size="16" font-weight="600" '
        f'fill="{t["text"]}">{esc(thesis)}</text>',
        # column headings
        f'<g font-family="{MONO}" font-size="11" fill="{t["muted"]}" letter-spacing="1">'
        f'<text x="28" y="{top - 8}">AREA</text>'
        f'<text x="170" y="{top - 8}">PROJECT</text>'
        f'<text x="520" y="{top - 8}">UPDATED</text>'
        f'<text x="660" y="{top - 8}">CI</text></g>',
        f'<path d="M28 {top - 0.5}H{width - 28}" stroke="{t["border"]}" />',
    ]

    if not projects:
        out.append(f'<text x="28" y="{top + 22}" font-family="{SANS}" font-size="14" '
                   f'fill="{t["muted"]}">No project data available.</text>')

    for i, p in enumerate(projects):
        y = top + i * row_h + 22
        colour = t[PILLAR_COLOURS.get(p.get("pillar"), "accent")]
        available = p.get("available", False)
        updated = p.get("updated") or "—"
        ci = p.get("ci")
        if not available:
            ci_text, ci_colour, updated = "unavailable", t["muted"], "—"
        elif ci == "passing":
            ci_text, ci_colour = "✓ passing", t["ok"]
        elif ci == "failing":
            ci_text, ci_colour = "✗ failing", t["bad"]
        else:
            ci_text, ci_colour = "—", t["muted"]
        out += [
            f'<circle cx="33" cy="{y - 4}" r="4" fill="{colour}" />',
            f'<text x="46" y="{y}" font-family="{MONO}" font-size="12" fill="{t["muted"]}">'
            f'{esc(truncate(p.get("pillar", ""), 14))}</text>',
            f'<text x="170" y="{y}" font-family="{SANS}" font-size="14" font-weight="600" '
            f'fill="{t["text"]}">{esc(truncate(p.get("label", ""), 40))}</text>',
            f'<text x="520" y="{y}" font-family="{MONO}" font-size="12" fill="{t["muted"]}">'
            f'{esc(updated)}</text>',
            f'<text x="660" y="{y}" font-family="{MONO}" font-size="12" fill="{ci_colour}">'
            f'{esc(ci_text)}</text>',
        ]
        if i < len(projects) - 1:
            out.append(f'<path d="M28 {y + 12.5}H{width - 28}" stroke="{t["grid"]}" />')

    latest = data.get("latest_activity") or "unavailable"
    out += [
        f'<path d="M0 {height - 36}H{width}" stroke="{t["border"]}" />',
        f'<text x="28" y="{height - 14}" font-family="{MONO}" font-size="11" fill="{t["muted"]}">'
        f'latest public activity: {esc(latest)}</text>',
        f'<text x="{width - 28}" y="{height - 14}" text-anchor="end" font-family="{MONO}" '
        f'font-size="11" fill="{t["muted"]}">generated daily from the GitHub API</text>',
        "</svg>",
    ]
    return "\n".join(out) + "\n"


def _window(start: float, end: float, cycle: float) -> tuple[str, str]:
    """keyTimes/values for something that is visible only between start and end (seconds)."""
    e = 0.001
    # keyTimes must stay inside [0, 1], so a window that reaches the end of the loop is clipped
    a, b = start / cycle, min(end / cycle, 1 - 2 * e)
    return f"0;{a:.3f};{a + e:.3f};{b:.3f};{b + e:.3f};1", "0;0;1;1;0;0"


def _live_network(t: dict) -> list[str]:
    """A small animated network: a signal fires through it and lights up one of the
    four areas of work at a time, while a terminal types the matching command."""
    cycle = 8.0
    inputs = [(556, 62 + i * 30) for i in range(4)]
    hidden = [(636, 52 + i * 28) for i in range(5)]
    outputs = [(716, 62 + i * 30) for i in range(4)]
    areas = (("VISION", t["accent2"], "$ train --split=by-driver"),
             ("RETRIEVAL", t["accent"], "$ search --hybrid --offline"),
             ("REASONING", "#d29922", "$ verify --nli --sources"),
             ("RELIABILITY", t["ok"], "$ replay --chaos webhooks"))
    out = [
        f'<circle cx="553" cy="32" r="4" fill="{t["ok"]}"><animate attributeName="opacity" '
        f'values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/></circle>',
        f'<text x="563" y="36" font-family="{MONO}" font-size="11" fill="{t["muted"]}" '
        f'letter-spacing="1">LIVE · WHAT I BUILD</text>',
    ]
    for ax, ay in inputs + outputs:
        for hx, hy in hidden:
            x1, y1, x2, y2 = (ax, ay, hx, hy) if ax < hx else (hx, hy, ax, ay)
            out.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{t["border"]}" stroke-width="1"/>')
    # faint background traffic so the network always looks alive
    for i, (ix, iy) in enumerate(inputs):
        hx, hy = hidden[(i * 2 + 1) % 5]
        ox, oy = outputs[(i + 2) % 4]
        out.append(f'<circle r="2" fill="{t["muted"]}" opacity="0.5"><animateMotion dur="{2.2 + i * 0.4:.1f}s" '
                   f'begin="{i * 0.6:.1f}s" repeatCount="indefinite" path="M{ix} {iy}L{hx} {hy}L{ox} {oy}"/></circle>')
    for x, y in inputs + hidden:
        out.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{t["panel"]}" stroke="{t["muted"]}" stroke-width="1.5"/>')
    # one bright signal per area, two seconds apart
    for k, (label, colour, command) in enumerate(areas):
        start, end = k * 2.0, k * 2.0 + 1.2
        (ix, iy), (hx, hy), (ox, oy) = inputs[k], hidden[k + 1], outputs[k]
        kt, vals = _window(start, end, cycle)
        out.append(f'<circle r="4" fill="{colour}" opacity="0">'
                   f'<animateMotion dur="{cycle:g}s" repeatCount="indefinite" calcMode="linear" '
                   f'keyPoints="0;0;1;1" keyTimes="0;{start / cycle:.3f};{end / cycle:.3f};1" '
                   f'path="M{ix} {iy}L{hx} {hy}L{ox} {oy}"/>'
                   f'<animate attributeName="opacity" dur="{cycle:g}s" repeatCount="indefinite" '
                   f'keyTimes="{kt}" values="{vals}"/></circle>')
        lit_kt, lit_vals = _window(end, end + 0.8, cycle)
        out.append(f'<circle cx="{ox}" cy="{oy}" r="7" fill="{t["panel"]}" stroke="{colour}" stroke-width="2"/>')
        out.append(f'<circle cx="{ox}" cy="{oy}" r="7" fill="{colour}" opacity="0">'
                   f'<animate attributeName="opacity" dur="{cycle:g}s" repeatCount="indefinite" '
                   f'keyTimes="{lit_kt}" values="0;0;1;1;0;0"/></circle>')
        out.append(f'<text x="730" y="{oy + 4}" font-family="{MONO}" font-size="10.5" '
                   f'fill="{colour}" letter-spacing="0.5">{label}</text>')
        # the matching command types itself out in the terminal line
        cmd_kt, cmd_vals = _window(start, start + 2.0, cycle)
        out.append(f'<clipPath id="type{k}"><rect x="560" y="186" height="20" width="0">'
                   f'<animate attributeName="width" dur="{cycle:g}s" repeatCount="indefinite" '
                   f'keyTimes="0;{start / cycle:.3f};{(start + 1.1) / cycle:.3f};1" values="0;0;250;250"/>'
                   f'</rect></clipPath>')
        out.append(f'<text x="560" y="200" font-family="{MONO}" font-size="11" fill="{colour}" '
                   f'clip-path="url(#type{k})" opacity="0">{esc(command)}'
                   f'<animate attributeName="opacity" dur="{cycle:g}s" repeatCount="indefinite" '
                   f'keyTimes="{cmd_kt}" values="{cmd_vals}"/></text>')
    out.insert(2, f'<rect x="548" y="182" width="270" height="26" rx="6" fill="{t["panel"]}" stroke="{t["border"]}"/>')
    return out


def render_header(theme: str) -> str:
    """Static header. Edit the text here and re-run with --header."""
    t = THEMES[theme]
    width, height = 840, 240
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="hdr-title hdr-desc">',
        '<title id="hdr-title">Lokaraj R — AI/ML engineering</title>',
        '<desc id="hdr-desc">AI systems should do more than produce outputs. They should '
        'earn trust. An animated network lights up vision, retrieval, reasoning and '
        'reliability in turn while a terminal types the matching command.</desc>',
        f'<rect width="{width}" height="{height}" rx="14" fill="{t["bg"]}" />',
        _grid(width, height, t["grid"]),
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" '
        f'fill="none" stroke="{t["border"]}" />',
        # identity
        f'<text x="40" y="58" font-family="{MONO}" font-size="13" fill="{t["accent"]}">'
        f'~/lokaraj $ whoami</text>',
        f'<text x="40" y="104" font-family="{SANS}" font-size="40" font-weight="700" '
        f'fill="{t["text"]}">Lokaraj R</text>',
        f'<text x="40" y="134" font-family="{SANS}" font-size="16" fill="{t["muted"]}">'
        f'AI/ML engineering · B.Tech CSE (AI &amp; ML), SRMIST</text>',
        f'<text x="40" y="184" font-family="{SANS}" font-size="17" font-weight="600" '
        f'fill="{t["text"]}">AI systems should do more than produce outputs.</text>',
        f'<text x="40" y="208" font-family="{SANS}" font-size="17" font-weight="600" '
        f'fill="{t["accent"]}">They should earn trust.</text>',
    ]
    out += _live_network(t)
    out.append("</svg>")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- write

def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def main(argv: list[str] | None = None, fetch=fetch_github) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=ROOT / "scripts" / "card_config.json")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "assets")
    parser.add_argument("--data", type=Path, help="render from a saved card-data JSON file")
    parser.add_argument("--dump-data", type=Path, help="also save the card data as JSON")
    parser.add_argument("--header", action="store_true", help="also write the static header")
    args = parser.parse_args(argv)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.data:
        data = json.loads(args.data.read_text(encoding="utf-8"))
    else:
        try:
            repos, runs = fetch(config["owner"], config["featured"], os.environ.get("GITHUB_TOKEN"))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            print(f"GitHub API unavailable, keeping existing SVGs: {type(exc).__name__}",
                  file=sys.stderr)
            return 1
        data = summarize(repos, runs, config)

    # Render everything first, then write, so a failure cannot leave a partial set.
    files = {f"system-card-{theme}.svg": render_card(data, theme) for theme in THEMES}
    if args.header:
        files.update({f"header-{theme}.svg": render_header(theme) for theme in THEMES})
    for name, text in files.items():
        write_atomic(args.out_dir / name, text)
    if args.dump_data:
        write_atomic(args.dump_data, json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("wrote " + ", ".join(sorted(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
