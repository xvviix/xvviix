#!/usr/bin/env python3
"""
Gitskins-kit contribution snake for the xvviix profile.

Rebuilds gitskins/snake.svg — an aurora-dark "contribution snake" card:
the year's calendar grid with a glowing snake crawling through every
active day, from the first contribution to today (apple at the head).

Usage:  python3 gen_snake.py

Data sources:
    * https://github.com/users/xvviix/contributions (server-rendered)
    * GitHub REST for the token (optional, public page scrape)

Committed back to main by the snake.yml workflow (daily).
"""
import os
import re
import time
import urllib.error
import urllib.request
import xml.dom.minidom
import xml.sax.saxutils

USER = "xvviix"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gitskins", "snake.svg")

LEVEL_FILL = {
    0: ("#ccfbf1", 0.05),
    1: ("#41d8c5", 0.30),
    2: ("#41d8c5", 0.52),
    3: ("#41d8c5", 0.74),
    4: ("#41d8c5", 1.00),
}


def e(t):
    return xml.sax.saxutils.escape(str(t), {'"': "&quot;"})


def fetch_calendar():
    """Return (total, cells) where cells = [(row, col, date, level), ...]."""
    req = urllib.request.Request(
        f"https://github.com/users/{USER}/contributions",
        headers={"User-Agent": "xvviix-profile-gen/1.0", "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            html = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f"contributions page HTTP {ex.code}") from ex
    tm = re.search(r'id="js-contribution-activity-description"[^>]*>\s*(\d+)\s*contributions', html)
    total = int(tm.group(1)) if tm else 0
    cells = []
    for m in re.finditer(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', html):
        tag = m.group(0)
        i = re.search(r'contribution-day-component-(\d+)-(\d+)"', tag)
        d = re.search(r'data-date="([^"]+)"', tag)
        l = re.search(r'data-level="(\d+)"', tag)
        if i and d and l:
            cells.append((int(i.group(1)), int(i.group(2)), d.group(1), int(l.group(1))))
    if not cells:
        raise RuntimeError("no calendar cells found — page layout changed?")
    return total, cells


def serpentine(cells):
    """All grid cells in snake order: row 0 L->R, row 1 R->L, ..."""
    rows = sorted({c[0] for c in cells})
    cols = sorted({c[1] for c in cells})
    cmin, cmax = cols[0], cols[-1]
    by_rc = {(r, c): d for r, c, d, _ in cells}
    path = []
    for r in rows:
        rng = range(cmin, cmax + 1) if r % 2 == 0 else range(cmax, cmin - 1, -1)
        for c in rng:
            if (r, c) in by_rc:
                path.append((r, c, by_rc[(r, c)]))
    return path


def render(total, cells):
    path = serpentine(cells)
    by_rc = {(r, c): (d, l) for r, c, d, l in cells}
    active_idx = [i for i, (r, c, d) in enumerate(path) if by_rc[(r, c)][1] >= 1]
    if not active_idx:
        raise RuntimeError("no active days — refusing to render an empty snake")
    i0, i1 = active_idx[0], active_idx[-1]

    # geometry
    P, S, RX = 14, 11, 2.5
    GX, GY = 58, 106
    ncol = max(c for _, c, _ in path) - min(c for _, c, _ in path) + 1

    def cx(c): return GX + c * P + P / 2 - 0.5
    def cy(r): return GY + r * P + P / 2 - 0.5

    # month labels: first column of each month
    months = []
    seen = set()
    for r, c, dt in path:
        mk = dt[:7]
        if mk not in seen:
            seen.add(mk)
            months.append((c, mk[8:]))
    month_lbl = " ".join(
        f'<text x="{cx(c):.0f}" y="{GY + 7 * P + 14}" text-anchor="middle" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="8" '
        f'fill="#5eead4" opacity="0.6">{e(m.upper())}</text>' for c, m in months)

    # grid cells
    cell_els = []
    for r, c, dt, lvl in sorted(cells, key=lambda x: (x[0], x[1])):
        fill, op = LEVEL_FILL.get(lvl, LEVEL_FILL[0])
        cell_els.append(f'<rect x="{GX + c * P}" y="{GY + r * P}" width="{S}" height="{S}" '
                        f'rx="{RX}" fill="{fill}" opacity="{op}"/>')
    grid = "".join(cell_els)

    n_active = len(active_idx)
    n_max = sum(1 for _, _, _, l in cells if l == 4)
    # classic snake: body is the full serpentine route from the first
    # active day to today; the crawl animation makes it visibly move
    body = path[i0:i1 + 1]
    d_attr = "M " + " L ".join(f"{cx(c):.1f} {cy(r):.1f}" for r, c, _ in body)
    hr, hc, _ = body[-1]
    head_x, head_y = cx(hc), cy(hr)
    # head direction from the last two body cells
    dx = cx(body[-1][1]) - cx(body[-2][1]) if len(body) > 1 else 1
    tr, tc, _ = body[0]
    tail_x, tail_y = cx(tc), cy(tr)

    # eaten dots (active cells on the body)
    dots = []
    for r, c, dt in body:
        if by_rc[(r, c)][1] >= 1:
            dots.append(f'<circle cx="{cx(c):.1f}" cy="{cy(r):.1f}" r="2.4" fill="#ecfdf5" opacity="0.95"/>')
    dots_s = "".join(dots)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="860" height="330" viewBox="0 0 860 330" role="img" aria-label="GitSkins gs-snake-xvviix-aurora-dark — contribution snake">
  <defs>
    <linearGradient id="gs-snake-bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#042f2e"/>
      <stop offset="54%" stop-color="#134e4a"/>
      <stop offset="100%" stop-color="#042f2e"/>
    </linearGradient>
    <radialGradient id="gs-snake-orb-0" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#4ade80" stop-opacity="0.4"/>
      <stop offset="58%" stop-color="#4ade80" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#4ade80" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gs-snake-orb-1" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2dd4bf" stop-opacity="0.5"/>
      <stop offset="58%" stop-color="#2dd4bf" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="#2dd4bf" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gs-snake-orb-2" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#d4af37" stop-opacity="0.4"/>
      <stop offset="58%" stop-color="#d4af37" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#d4af37" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="gs-snake-body" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#2dd4bf"/>
      <stop offset="60%" stop-color="#4ade80"/>
      <stop offset="100%" stop-color="#86efac"/>
    </linearGradient>
  </defs>
  <g id="gs-snake-aurora-dark">
    <rect width="860" height="330" rx="20" fill="url(#gs-snake-bg)"/>
    <ellipse cx="150" cy="60" rx="220" ry="115" fill="url(#gs-snake-orb-1)"/>
    <ellipse cx="700" cy="290" rx="240" ry="100" fill="url(#gs-snake-orb-0)"/>
    <ellipse cx="810" cy="70" rx="180" ry="95" fill="url(#gs-snake-orb-2)"/>
    <rect x="28" y="26" width="804" height="278" rx="20" fill="rgba(8,8,12,0.5)" stroke="#4ade80" stroke-opacity="0.42"/>
    <text x="46" y="61" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" font-size="28" font-weight="850" letter-spacing="-0.5" fill="#ccfbf1">Contribution Snake</text>
    <text x="48" y="84" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" font-size="13" font-weight="650" letter-spacing="1.2" fill="#5eead4">{total} contributions in the last year — one hungry snake</text>

    {grid}

    <!-- snake -->
    <path d="{d_attr}" fill="none" stroke="#4ade80" stroke-opacity="0.14" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="{d_attr}" fill="none" stroke="url(#gs-snake-body)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="{d_attr}" fill="none" stroke="#d1fae5" stroke-opacity="0.85" stroke-width="4.5" stroke-linecap="round" stroke-dasharray="12 16">
      <animate attributeName="stroke-dashoffset" from="0" to="-280" dur="5s" repeatCount="indefinite"/>
    </path>
    <circle r="3.2" fill="#ffffff" opacity="0.9">
      <animateMotion dur="24s" repeatCount="indefinite" path="{d_attr}"/>
    </circle>
    {dots_s}
    <circle cx="{tail_x:.1f}" cy="{tail_y:.1f}" r="3" fill="#2dd4bf" opacity="0.85"/>
    <g>
      <circle cx="{head_x:.1f}" cy="{head_y:.1f}" r="6.5" fill="#4ade80" stroke="#052e16" stroke-width="1.4">
        <animate attributeName="r" values="6.5;7.6;6.5" dur="1.8s" repeatCount="indefinite"/>
      </circle>
      <circle cx="{head_x + (1.8 if dx >= 0 else -1.8):.1f}" cy="{head_y - 1.6:.1f}" r="1" fill="#052e16"/>
      <circle cx="{head_x + (-2.2 if dx >= 0 else 2.2):.1f}" cy="{head_y - 1.6:.1f}" r="1" fill="#052e16"/>
      <!-- apple -->
      <circle cx="{head_x + 8:.1f}" cy="{head_y - 8:.1f}" r="4" fill="#f59e0b" stroke="#78350f" stroke-width="0.8">
        <animate attributeName="opacity" values="1;0.55;1" dur="1.8s" repeatCount="indefinite"/>
      </circle>
      <path d="M {head_x + 8:.1f} {head_y - 12:.1f} q 2.5 -2.5 4 -0.5" fill="none" stroke="#4ade80" stroke-width="1.2"/>
    </g>
    {month_lbl}

    <rect x="46" y="{GY + 7 * P + 30}" width="182" height="34" rx="17" fill="rgba(45,212,191,0.1)" stroke="#2dd4bf" stroke-opacity="0.5"/>
    <text x="137" y="{GY + 7 * P + 51}" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="10.5" font-weight="800" letter-spacing="1" fill="#5eead4">{total} CONTRIBUTIONS</text>
    <rect x="240" y="{GY + 7 * P + 30}" width="164" height="34" rx="17" fill="rgba(74,222,128,0.1)" stroke="#4ade80" stroke-opacity="0.5"/>
    <text x="322" y="{GY + 7 * P + 51}" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="10.5" font-weight="800" letter-spacing="1" fill="#86efac">{n_active} ACTIVE DAYS</text>
    <rect x="416" y="{GY + 7 * P + 30}" width="150" height="34" rx="17" fill="rgba(212,175,55,0.1)" stroke="#d4af37" stroke-opacity="0.5"/>
    <text x="491" y="{GY + 7 * P + 51}" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="10.5" font-weight="800" letter-spacing="1" fill="#f5d061">{n_max} MAX-LEVEL DAYS</text>
    <text x="814" y="{GY + 7 * P + 51}" text-anchor="end" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="10" font-weight="700" letter-spacing="0.5" fill="#5eead4" opacity="0.65">auto-updated daily 🐍</text>
    <rect x="0.5" y="0.5" width="859" height="329" rx="19.5" fill="none" stroke="#4ade80" stroke-opacity="0.5"/>
  </g>
</svg>
'''
    return svg


def main():
    total, cells = fetch_calendar()
    svg = render(total, cells)
    xml.dom.minidom.parseString(svg)
    out = os.path.normpath(OUT)
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else None
    if old != svg:
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {out} ({len(svg)} bytes)")
    else:
        print("snake unchanged")
    print(f"total={total} cells={len(cells)} active={sum(1 for c in cells if c[3] >= 1)}")


if __name__ == "__main__":
    main()
