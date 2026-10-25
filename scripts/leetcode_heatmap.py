"""Draw my LeetCode submission calendar as a dark, GitHub-style heatmap.

    python scripts/leetcode_heatmap.py      # fetch and write assets/leetcode-heatmap.svg

Data comes from LeetCode's public GraphQL endpoint (no login). If it can't be
reached, nothing is written and the last good heatmap stays in place.
Standard library only; the same counts and date always give the same SVG.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import sys
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "leetcode-heatmap.svg"
CONFIG = ROOT / "scripts" / "card_config.json"

# GitHub's dark contribution-graph palette
BG, BORDER, TEXT, MUTED = "#0d1117", "#30363d", "#e6edf3", "#8b949e"
LEVELS = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
CELL, STEP, LEFT, TOP = 11, 14, 36, 46
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

QUERY = ("query($u:String!){matchedUser(username:$u){userCalendar{submissionCalendar}}}")


def fetch(username: str) -> dict[str, int]:
    """Return {"YYYY-MM-DD": submissions} for roughly the last year."""
    body = json.dumps({"query": QUERY, "variables": {"u": username}}).encode()
    req = urllib.request.Request("https://leetcode.com/graphql", data=body, headers={
        "Content-Type": "application/json", "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0 (profile-heatmap)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        user = json.load(resp)["data"]["matchedUser"]
    if not user:
        raise ValueError(f"LeetCode user {username!r} not found")
    return parse_calendar(user["userCalendar"]["submissionCalendar"])


def parse_calendar(raw: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ts, n in json.loads(raw or "{}").items():
        day = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()
        counts[day] = counts.get(day, 0) + int(n)
    return counts


def level(count: int, peak: int) -> int:
    if count <= 0 or peak <= 0:
        return 0
    return min(4, max(1, math.ceil(4 * count / peak)))


def render(counts: dict[str, int], today: dt.date, username: str) -> str:
    # 53 columns of Sunday..Saturday, ending with the week that contains today
    first = today - dt.timedelta(days=(today.weekday() + 1) % 7) - dt.timedelta(weeks=52)
    days = [first + dt.timedelta(days=i) for i in range((today - first).days + 1)]
    window = {d.isoformat(): counts.get(d.isoformat(), 0) for d in days}
    peak = max(window.values(), default=0)
    total, active = sum(window.values()), sum(1 for v in window.values() if v)
    cols = (len(days) + 6) // 7
    width = LEFT + cols * STEP + 16
    height = TOP + 7 * STEP + 34

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-label="LeetCode heatmap: {total} submissions '
           f'on {active} days in the last year">',
           f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
           f'<text x="{LEFT}" y="22" font-family="{SANS}" font-size="13" fill="{TEXT}">'
           f'<tspan font-weight="600">{total} LeetCode submissions</tspan> in the last year · {active} active days</text>',
           f'<text x="{width - 14}" y="22" text-anchor="end" font-family="{MONO}" font-size="10" fill="{MUTED}">'
           f'@{escape(username)}</text>']
    last_month = None
    for i, d in enumerate(days):
        col, row = i // 7, i % 7
        if row == 0 and d.month != last_month and d.day <= 7:
            out.append(f'<text x="{LEFT + col * STEP}" y="{TOP - 6}" font-family="{SANS}" font-size="10" '
                       f'fill="{MUTED}">{MONTHS[d.month - 1]}</text>')
            last_month = d.month
        n = window[d.isoformat()]
        out.append(f'<rect x="{LEFT + col * STEP}" y="{TOP + row * STEP}" width="{CELL}" height="{CELL}" rx="2" '
                   f'fill="{LEVELS[level(n, peak)]}"><title>{n} on {d.isoformat()}</title></rect>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="8" y="{TOP + row * STEP + 9}" font-family="{SANS}" font-size="10" '
                   f'fill="{MUTED}">{name}</text>')
    y = TOP + 7 * STEP + 18
    legend_x = width - 16 - 5 * STEP - 34
    out.append(f'<text x="{legend_x - 6}" y="{y + 9}" text-anchor="end" font-family="{SANS}" font-size="10" '
               f'fill="{MUTED}">Less</text>')
    for k, colour in enumerate(LEVELS):
        out.append(f'<rect x="{legend_x + k * STEP}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{colour}"/>')
    out.append(f'<text x="{legend_x + 5 * STEP + 3}" y="{y + 9}" font-family="{SANS}" font-size="10" '
               f'fill="{MUTED}">More</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    username = json.loads(CONFIG.read_text(encoding="utf-8"))["leetcode"]
    try:
        counts = fetch(username)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        print(f"LeetCode unavailable, keeping the existing heatmap: {type(exc).__name__}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(counts, dt.datetime.now(dt.timezone.utc).date(), username), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
