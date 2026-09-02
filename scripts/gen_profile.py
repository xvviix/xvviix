#!/usr/bin/env python3
"""
Gitskins-kit section generator for the xvviix profile.

Rebuilds the data-driven sections of the aurora-dark Gitskins kit from live
GitHub data:

    stats        -> gitskins/stats.svg        (stars / contributions / repos / followers)
    activity     -> gitskins/activity.svg     (53-week contribution heatmap)
    projects     -> gitskins/projects.svg     (pinned repo cards)
    stack        -> gitskins/stack.svg        (repository-weighted languages)
    sysinfo      -> gitskins/system-scan.svg  (terminal scan card)

Usage:  python3 gen_profile.py <section|all>

Data sources:
    * GitHub REST  (token from $GITHUB_TOKEN, optional for public data)
    * GitHub GraphQL (pinned repos)
    * https://github.com/users/xvviix/contributions  (live calendar, server-rendered)
"""
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.sax.saxutils

USER = "xvviix"
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "templates")
OUT = os.path.join(os.path.dirname(HERE), "gitskins")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

UA = {"User-Agent": "xvviix-profile-gen/1.0"}


def e(text) -> str:
    return xml.sax.saxutils.escape(str(text), {'"': "&quot;"})


def _http(url: str, data: bytes = None, headers: dict = None, timeout: int = 30, retries: int = 3) -> bytes:
    hdrs = dict(UA)
    if TOKEN:
        hdrs["Authorization"] = "Bearer " + TOKEN
    if headers:
        hdrs.update(headers)
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as ex:
            last = ex
            if ex.code in (403, 429) and i < retries - 1:
                ra = ex.headers.get("Retry-After")
                time.sleep(int(ra) if (ra or "").isdigit() else 8 * (i + 1))
                continue
            if ex.code >= 500 and i < retries - 1:
                time.sleep(4 * (i + 1))
                continue
            raise
        except Exception as ex:  # noqa
            last = ex
            if i < retries - 1:
                time.sleep(4 * (i + 1))
                continue
            raise
    raise RuntimeError(f"HTTP fail for {url}: {last}")


def rest(path: str):
    return json.loads(_http("https://api.github.com" + path))


def graphql(query: str):
    return json.loads(_http(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"},
    ))


# ---------------------------------------------------------------- data

def fetch_user():
    hdrs = {"User-Agent": UA["User-Agent"]}
    if TOKEN:
        hdrs["Authorization"] = "Bearer " + TOKEN
    url = f"/users/{USER}/repos?per_page=100&type=owner"
    repos = []
    while url:
        req = urllib.request.Request("https://api.github.com" + url, headers=hdrs)
        resp = urllib.request.urlopen(req, timeout=30)
        repos.extend(json.loads(resp.read()))
        link = resp.headers.get("Link", "")
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    user = rest(f"/users/{USER}")
    return user, repos


def fetch_languages(repos):
    """byte-weighted languages across non-fork repos"""
    weights = {}
    for r in repos:
        if r.get("fork") or r.get("archived"):
            continue
        try:
            langs = rest(f"/repos/{USER}/{r['name']}/languages")
        except Exception:
            continue
        for name, nbytes in langs.items():
            weights[name] = weights.get(name, 0) + nbytes
    return weights


def fetch_pinned():
    q = """{
      viewer {
        pinnedItems(first: 6) {
          nodes {
            ... on Repository {
              name
              description
              stargazerCount
              updatedAt
              isArchived
            }
          }
        }
      }
    }"""
    data = graphql(q)["data"]["viewer"]["pinnedItems"]["nodes"]
    pins = []
    for n in data:
        if not n:
            continue
        n = dict(n)
        try:
            n["languages"] = rest(f"/repos/{USER}/{n['name']}/languages")
        except Exception:
            n["languages"] = {}
        try:
            n["topics"] = rest(f"/repos/{USER}/{n['name']}/topics")["names"]
        except Exception:
            n["topics"] = []
        pins.append(n)
    return pins


def fetch_contrib_graph():
    """Live contribution calendar from the profile page (server-rendered)."""
    html = _http(
        f"https://github.com/users/{USER}/contributions",
        headers={"Accept": "text/html"},
        timeout=40,
    ).decode("utf-8", "replace")
    total_m = re.search(
        r'id="js-contribution-activity-description"[^>]*>\s*(\d+)\s*contributions', html)
    total = int(total_m.group(1)) if total_m else 0
    cells = []
    for m in re.finditer(
            r'<td[^>]*class="ContributionCalendar-day"[^>]*>', html):
        tag = m.group(0)
        d = re.search(r'data-date="([^"]+)"', tag)
        l = re.search(r'data-level="([^"]+)"', tag)
        if d and l:
            cells.append((d.group(1), int(l.group(1))))
    return total, cells


LANG_COLORS = {
    "HTML": "#e55b38", "CSS": "#8f57c7", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Python": "#5594c8", "Batchfile": "#c1f12e",
    "C": "#555555", "C++": "#f34b7d", "C#": "#178600", "Go": "#00add8",
    "Rust": "#dea584", "Java": "#b07219", "PHP": "#4f5d95", "Ruby": "#701516",
    "Shell": "#89e051", "Bash": "#89e051", "Swift": "#f05138", "Kotlin": "#a97bff",
    "Dart": "#00b4ab", "Lua": "#000080", "Jupyter Notebook": "#da5b0b",
    "SCSS": "#c6538c", "Vue": "#41b883", "Svelte": "#ff3e00", "MDX": "#fcb32c",
    "Markdown": "#083fa1", "SVG": "#ff9900", "PowerShell": "#012456",
}


def lang_color(name: str) -> str:
    return LANG_COLORS.get(name, LANG_COLORS.get(name.lower(), "#5eead4"))


def pct_list(weights: dict, top: int):
    total = sum(weights.values()) or 1
    items = sorted(weights.items(), key=lambda kv: -kv[1])[:top]
    out = [(n, round(100.0 * b / total)) for n, b in items]
    # fix rounding so it sums to 100 within the top slice
    return out


# ---------------------------------------------------------------- builders

def build_stats(d):
    tpl = open(os.path.join(TEMPLATES, "stats.svg"), encoding="utf-8").read()
    vals = {
        "STARS": d["stars"], "CONTRIBS": d["contribs"],
        "REPOS": d["repos"], "FOLLOWERS": d["followers"],
    }
    mx = max(vals.values()) or 1
    for k, v in vals.items():
        tpl = tpl.replace("{{%s}}" % k, str(v))
        bar = max(2, round(136 * v / mx)) if v else 2
        tpl = tpl.replace("{{%s_BAR}}" % k, str(bar))
    return tpl


LEVELS = {
    0: ("#ccfbf1", "0;0.07;0.07"),
    1: ("#41d8c5", "0;0.56;0.34"),
    2: ("#41d8c5", "0;0.77;0.55"),
    3: ("#41d8c5", "0;1.00;0.78"),
    4: ("#41d8c5", "0;1.00;1"),
}


def build_activity(d):
    head = open(os.path.join(TEMPLATES, "activity-head.svg"), encoding="utf-8").read()
    tail = open(os.path.join(TEMPLATES, "activity-tail.svg"), encoding="utf-8").read()
    head = head.replace("{{TOTAL}}", str(d["contribs"]))

    cells = d["cells"]
    if not cells:
        return head + tail
    start = min(dt.date.fromisoformat(c[0]) for c in cells)
    parts = []
    idx = 0
    for col in range(53):
        for row in range(7):
            day = start + dt.timedelta(days=col * 7 + row)
            iso = day.isoformat()
            lv = d["cellmap"].get(iso)
            if lv is None:
                continue  # outside the window (future / before window start)
            color, anim = LEVELS[min(lv, 4)]
            x = 51.5 + col * 14
            y = 105.5 + row * 14
            begin = 0.2 + 0.01 * idx
            dur = 2.2 - 0.01 * idx
            parts.append(
                f'<g transform="translate({x},{y})">\n'
                f'  <rect x="-5.5" y="-5.5" width="11" height="11" rx="2.5" '
                f'fill="{color}" fill-opacity="0" transform="scale(0.15)">\n'
                f'    <animate attributeName="fill-opacity" values="{anim}" keyTimes="0;0.55;1" '
                f'begin="{begin:.3f}s" dur="{dur:.3f}s" fill="freeze" calcMode="spline" '
                f'keySplines="0.2 0.8 0.2 1;0.4 0 0.2 1"/>\n'
                f'    <animateTransform attributeName="transform" type="scale" values="0.15;1.12;1" '
                f'keyTimes="0;0.55;1" begin="{begin:.3f}s" dur="{dur:.3f}s" fill="freeze" '
                f'calcMode="spline" keySplines="0.2 0.8 0.2 1;0.4 0 0.2 1"/>\n'
                f'  </rect>\n'
                f'</g>'
            )
            idx += 1
    return head + "".join(parts) + tail


def split_desc(desc: str, width: int = 38, lines: int = 2):
    desc = (desc or "").replace("\u2014", "-").strip()
    out = []
    cur = ""
    for word in desc.split():
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            out.append(cur)
            cur = word
        if len(out) == lines:
            break
    if cur and len(out) < lines:
        out.append(cur)
    if len(out) == lines and len(desc) > sum(len(o) for o in out) + lines - 1:
        out[-1] = out[-1][: width - 1].rstrip() + "\u2026"
    return out


def chip_w(text: str):
    return min(150, round(len(text) * 5.7 + 24, 1))


def card_svg(card: dict, x: int, delay: float):
    name = card["name"]
    desc_lines = split_desc(card.get("description"))
    while len(desc_lines) < 2:
        desc_lines.append("")
    l1, l2 = e(desc_lines[0]), e(desc_lines[1])

    # topic chips
    chips = []
    cx = 18
    for t in card.get("topics", [])[:3]:
        t2 = t if len(t) <= 22 else t[:21] + "\u2026"
        w = chip_w(t2)
        cx2 = round(cx, 1)
        chips.append(
            f'<rect x="{cx2}" y="112" width="{w}" height="18" rx="9" fill="#2dd4bf" fill-opacity="0.14" '
            f'stroke="#2dd4bf" stroke-opacity="0.4"/>'
            f'<text x="{round(cx2 + w / 2)}" y="124.5" text-anchor="middle" '
            f"font-family=\"ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace\" "
            f'font-size="9.5" fill="#2dd4bf">{e(t2)}</text>'
        )
        cx += w + 14
    chips = "".join(chips)

    # status dot
    upd = dt.datetime.fromisoformat(card["updatedAt"].replace("Z", "+00:00"))
    age_h = max(0.0, (dt.datetime.now(dt.timezone.utc) - upd).total_seconds() / 3600)
    if age_h <= 72:
        dot = ('<circle cx="378" cy="15" r="4" fill="#3fb950">'
               '<animate attributeName="opacity" values="1;0.25;1" dur="1.8s" '
               'repeatCount="indefinite"/></circle>')
    else:
        dot = '<circle cx="378" cy="15" r="4" fill="#5eead4" fill-opacity="0.5"/>'

    # language donut
    langs = sorted((card.get("languages") or {}).items(), key=lambda kv: -kv[1])[:3]
    tot = sum(b for _, b in langs) or 1
    C = 157.08
    arcs = []
    center = "0%"
    acc = 0.0
    for i, (ln, lb) in enumerate(langs):
        frac = lb / tot
        if i == 0:
            center = f"{round(frac * 100)}%"
        arc = C * frac
        if arc < 0.4:
            continue
        start = acc
        acc += arc
        arcs.append(
            f'<circle cx="348" cy="92" r="25" fill="none" stroke="{lang_color(ln)}" stroke-width="8" '
            f'stroke-dasharray="{arc:.2f} {C - arc:.2f}" stroke-dashoffset="{-start:.2f}" '
            f'transform="rotate(-90 348 92)" opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.01s" begin="{delay + 0.35:.2f}s" fill="freeze"/>'
            f'<animate attributeName="stroke-dasharray" from="0 {C:.2f}" to="{arc:.2f} {C - arc:.2f}" '
            f'dur="0.6s" begin="{delay + 0.35:.2f}s" fill="freeze" calcMode="spline" '
            f'keyTimes="0;1" keySplines="0.3 0 0.2 1"/></circle>'
        )
    donut = (
        '<circle cx="348" cy="92" r="25" fill="none" stroke="#5eead4" stroke-opacity="0.18" stroke-width="8"/>'
        + "".join(arcs) +
        '<text x="348" y="96" text-anchor="middle" '
        "font-family=\"ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace\" "
        f'font-size="11" font-weight="700" fill="#ccfbf1">{e(center)}</text>'
    )

    # updated label
    if age_h < 1:
        updl = "updated just now"
    elif age_h < 48:
        updl = f"updated {round(age_h)}h ago"
    elif age_h < 48 * 14:
        updl = f"updated {round(age_h / 24)}d ago"
    else:
        updl = f"updated {round(age_h / 168)}w ago"

    mono = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace"
    return (
        f'<a href="https://github.com/{USER}/{name}" target="_blank">\n'
        f'    <g opacity="0" transform="translate({x},88)">\n'
        f'    <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{delay:.2f}s" fill="freeze"/>\n'
        f'    <rect width="394" height="162" rx="13" fill="rgba(8,8,12,0.5)" stroke="#2dd4bf">\n'
        f'      <animate attributeName="stroke-opacity" values="0.45;0.85;0.45" dur="4.5s" '
        f'begin="{delay:.2f}s" repeatCount="indefinite"/>\n'
        f'    </rect>\n'
        f'    <path d="M0 13 a13 13 0 0 1 13 -13 h368 a13 13 0 0 1 13 13 v17 h-394 z" fill="#2dd4bf" fill-opacity="0.06"/>\n'
        f'    <line x1="0" y1="30" x2="394" y2="30" stroke="#2dd4bf" stroke-opacity="0.5"/>\n'
        f'    <text x="16" y="19.5" font-family="{mono}" font-size="10.5" fill="#5eead4">'
        f'<tspan fill="#2dd4bf">&#8226;</tspan> {e(name)}</text>\n'
        f'    {dot}\n'
        f'    <text x="18" y="58" font-family="{mono}" font-size="16.5" font-weight="700" fill="#ccfbf1">{e(name)}'
        f'<tspan fill="#2dd4bf"> _<animate attributeName="opacity" values="1;0;1" dur="1.2s" '
        f'begin="{delay + 0.35:.2f}s" repeatCount="indefinite"/></tspan></text>\n'
        f'    <text x="18" y="79" font-family="{mono}" font-size="11.5" fill="#5eead4">{l1}</text>\n'
        f'    <text x="18" y="95" font-family="{mono}" font-size="11.5" fill="#5eead4">{l2}</text>\n'
        f'    {chips}\n'
        f'    <text x="18" y="150" font-family="{mono}" font-size="11" fill="#5eead4">'
        f'<tspan fill="#f1e05a">&#9733;</tspan> {card.get("stargazerCount", 0)}'
        f'<tspan fill="#5eead4" fill-opacity="0.7" dx="12">{e(updl)}</tspan></text>\n'
        f'    {donut}\n'
        f'    </g>\n'
        f'  </a>'
    )


def build_projects(d):
    tpl = open(os.path.join(TEMPLATES, "projects.svg"), encoding="utf-8").read()
    pins = d["pinned"][:4]
    cards = []
    for i, p in enumerate(pins):
        x = 28 if i % 2 == 0 else 438
        cards.append(card_svg(p, x, 0.25 + 0.15 * i))
    tpl = tpl.replace("{{CARDS}}", "".join(cards))
    tpl = tpl.replace("{{PIN_COUNT}}", str(len(pins)))
    rows = (len(pins) + 1) // 2
    if rows > 1:
        h = 88 + rows * 162 + 24
        tpl = re.sub(r'(<svg[^>]*height=")274(")', r'\g<1>%d\g<2>' % h, tpl, count=1)
        tpl = re.sub(r'(<svg[^>]*viewBox="0 0 860 ")274(")', r'\g<1>%d\g<2>' % h, tpl, count=1)
        tpl = re.sub(r'(<rect width="860" height=")274(")', r'\g<1>%d\g<2>' % h, tpl, count=1)
    return tpl


def build_stack(d):
    tpl = open(os.path.join(TEMPLATES, "stack.svg"), encoding="utf-8").read()
    items = pct_list(d["lang_weights"], 5)
    rows = []
    for i, (name, pct) in enumerate(items):
        y = 107 + i * 32
        color = lang_color(name)
        bar = max(4, round(466 * pct / 100))
        rows.append(
            f'<g class="aura-chip" style="animation-delay:{i * 95}ms">\n'
            f'      <circle cx="54" cy="{y}" r="5" fill="{color}"/>\n'
            f'      <text x="72" y="{y + 5}" font-family="-apple-system,BlinkMacSystemFont,&#39;Segoe UI&#39;,sans-serif" '
            f'font-size="14" font-weight="800" fill="#ccfbf1">{e(name)}</text>\n'
            f'      <text x="306" y="{y + 5}" font-family="-apple-system,BlinkMacSystemFont,&#39;Segoe UI&#39;,sans-serif" '
            f'font-size="13" font-weight="850" fill="{color}" text-anchor="end">{pct}%</text>\n'
            f'      <rect x="330" y="{y - 9}" width="466" height="9" rx="4.5" fill="rgba(255,255,255,0.12)"/>\n'
            f'      <rect class="aura-bar" x="330" y="{y - 9}" width="{bar}" height="9" rx="4.5" '
            f'fill="{color}" opacity="0.95"/>\n'
            f'    </g>'
        )
    return tpl.replace("{{ROWS}}", "".join(rows))


INFO_ROWS = [
    ("Subject", lambda d: "Matin"),
    ("Handle", lambda d: "@" + USER),
    ("Role", lambda d: "Software engineer | Vibe coder"),
    ("Status", lambda d: "Building | Learning | Shipping"),
    ("Languages", lambda d: ", ".join(n for n, _ in pct_list(d["lang_weights"], 4)) or "n/a"),
    ("Repositories", lambda d: str(d["repos"])),
    ("Contributions", lambda d: str(d["contribs"])),
    ("Stars", lambda d: str(d["stars"])),
    ("Followers", lambda d: str(d["followers"])),
    ("Active Days", lambda d: str(d["active_days"])),
    ("Contact", lambda d: "github.com/" + USER),
]


def build_sysinfo(d):
    tpl = open(os.path.join(TEMPLATES, "system-scan.svg"), encoding="utf-8").read()
    mono = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace"
    rows = []
    for i, (label, fn) in enumerate(INFO_ROWS):
        y = 144 + i * 39
        begin = 0.55 + 0.105 * i
        val = fn(d)
        if len(val) > 34:
            val = val[:33] + "\u2026"
        rows.append(
            f'<clipPath id="scan-xvviix-aurora-dark-info-{i}"><rect x="548" y="{y - 19}" width="0" height="27">'
            f'<animate attributeName="width" from="0" to="580" begin="{begin:.3f}s" dur="0.32s" fill="freeze"/>'
            f'</rect></clipPath>\n'
            f'    <g clip-path="url(#scan-xvviix-aurora-dark-info-{i})">\n'
            f'      <text x="548" y="{y}" font-family="{mono}" font-size="14" font-weight="750" fill="#2dd4bf">{e(label)}</text>\n'
            f'      <line x1="660" y1="{y - 4}" x2="824" y2="{y - 4}" stroke="#5eead4" stroke-opacity="0.3" stroke-dasharray="2 5"/>\n'
            f'      <text x="842" y="{y}" font-family="{mono}" font-size="14" fill="#ccfbf1">{e(val)}</text>\n'
            f'    </g>'
        )
    return tpl.replace("{{INFO_ROWS}}", "\n".join(rows))


# ---------------------------------------------------------------- main

BUILDERS = {
    "stats": ("stats.svg", build_stats),
    "activity": ("activity.svg", build_activity),
    "projects": ("projects.svg", build_projects),
    "stack": ("stack.svg", build_stack),
    "sysinfo": ("system-scan.svg", build_sysinfo),
}


def collect_data(sections):
    need_langs = {"stack", "sysinfo", "projects"} & sections
    need_pins = "projects" in sections
    need_graph = {"activity", "stats", "sysinfo"} & sections

    d = {}
    print(f"fetching user + repos ({USER}) ...")
    user, repos = fetch_user()
    d["repos"] = user.get("public_repos") or len(repos)
    d["followers"] = user.get("followers") or 0
    d["stars"] = sum(r.get("stargazers_count") or 0 for r in repos)

    if need_langs:
        print("fetching repo languages ...")
        d["lang_weights"] = fetch_languages(repos)
    else:
        d["lang_weights"] = {}

    if need_pins:
        print("fetching pinned repos ...")
        d["pinned"] = fetch_pinned()
    else:
        d["pinned"] = []

    if need_graph:
        print("fetching contribution calendar ...")
        total, cells = fetch_contrib_graph()
        d["contribs"] = total
        d["cells"] = cells
        d["cellmap"] = dict(cells)
        d["active_days"] = sum(1 for _, lv in cells if lv > 0)
    else:
        d["contribs"] = 0
        d["cells"] = []
        d["cellmap"] = {}
        d["active_days"] = 0
    return d


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: gen_profile.py <stats|activity|projects|stack|sysinfo|all>")
    what = sys.argv[1]
    sections = set(BUILDERS) if what == "all" else {what}
    if not sections <= set(BUILDERS):
        sys.exit(f"unknown section: {what}")

    d = collect_data(sections)
    os.makedirs(OUT, exist_ok=True)
    for s in sorted(sections):
        fname, builder = BUILDERS[s]
        out = builder(d)
        path = os.path.join(OUT, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {path} ({len(out)} bytes)")

    # sanity: every generated file must parse as XML
    import xml.dom.minidom
    for s in sorted(sections):
        fname, _ = BUILDERS[s]
        xml.dom.minidom.parse(os.path.join(OUT, fname))
    print("all sections OK")


if __name__ == "__main__":
    main()
