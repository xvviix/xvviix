#!/usr/bin/env python3
"""Make the What-I-Build + Social cards clickable and inline them in README.md.

GitHub renders <img src="*.svg"> as a flat picture — nothing inside it can be
clicked. So the two cards are inlined straight into README.md (real DOM) and
every chip is wrapped in an <a href> pointing at the right place:

  * what-i-build chips  -> https://github.com/xvviix/<repo>   (the site's repo)
  * social GitHub chip  -> https://github.com/xvviix
  * social Email chip   -> mailto:matinhabibi688@gmail.com
  * social Telegram chip-> https://t.me/xvviix

The gitskins/*.svg files are kept in sync (same content, XML decl kept) so the
raw URLs stay valid. README blocks live between GITSKINS:WIB / GITSKINS:SOCIAL
markers — re-running this script regenerates them idempotently.
"""
import html
import json
import os
import re
import sys
import urllib.request

USER = "xvviix"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GITSKINS = os.path.join(ROOT, "gitskins")
README = os.path.join(ROOT, "README.md")

SOCIAL_LINKS = [
    "https://github.com/xvviix",
    "mailto:matinhabibi688@gmail.com",
    "https://t.me/xvviix",
]

WIB_MARK = "<!-- GITSKINS:WIB:BEGIN (inline SVG — managed by scripts/make_clickable.py) -->"
WIB_END = "<!-- GITSKINS:WIB:END -->"
SOC_MARK = "<!-- GITSKINS:SOCIAL:BEGIN (inline SVG — managed by scripts/make_clickable.py) -->"
SOC_END = "<!-- GITSKINS:SOCIAL:END -->"


def fetch_repos():
    url = f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"
    req = urllib.request.Request(
        url, headers={"User-Agent": "gitskins-kit", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return [r["name"] for r in json.loads(resp.read())]


def resolve(label, repos):
    """chip label (possibly truncated with …) -> exact repo name."""
    import difflib

    lab = label.rstrip("…").strip()
    for r in repos:
        if r == lab:
            return r
    for r in repos:
        if r.lower() == lab.lower():
            return r
    cands = [r for r in repos if r.lower().startswith(lab.lower())]
    if len(cands) == 1:
        return cands[0]
    near = difflib.get_close_matches(lab, repos, n=2, cutoff=0.6)
    if near:
        return near[0]
    sys.exit(f"could not resolve chip {label!r} (candidates: {cands or near})")


CHIP_RE = re.compile(
    r'(<rect x="(\d+)" y="(\d+)" width="(\d+)" height="20" rx="9" '
    r'fill="rgba\(45,212,191,0\.08\)" stroke="#2dd4bf" stroke-opacity="0\.3"/>)\s*'
    r'(<text x="[\d.]+" y="[\d.]+" text-anchor="middle" '
    r'font-family="ui-monospace,[^"]*" font-size="9\.5" fill="#5eead4">)([^<]+)(</text>)'
)


def make_wib_clickable(svg, repos):
    mapping = {}

    def repl(m):
        label = html.unescape(m.group(6))
        repo = resolve(label, repos)
        mapping[label] = repo
        return (
            f'<a href="https://github.com/{USER}/{repo}"><title>{label}</title>'
            f'{m.group(1)}{m.group(5)}{m.group(6)}{m.group(7)}</a>'
        )

    svg, n = CHIP_RE.subn(repl, svg)
    if n != 52:
        print(f"WARNING: expected 52 chips, wrapped {n}")
    # "view all repos ↗" footer text -> repos tab
    svg = svg.replace(
        '<text x="814" y="684" text-anchor="end"',
        '<a href="https://github.com/xvviix?tab=repositories">'
        '<text x="814" y="684" text-anchor="end"',
        1,
    )
    svg = svg.replace("view all repos ↗</text>", "view all repos ↗</text></a>", 1)
    print(f"what-i-build: {n} chips linked")
    for k, v in mapping.items():
        print(f"   {k:22s} -> {v}")
    return svg


SOCIAL_CHIP_RE = re.compile(r'<g class="aura-chip"[^>]*>.*?</g>', re.S)


def make_social_clickable(svg):
    groups = SOCIAL_CHIP_RE.findall(svg)
    if len(groups) != len(SOCIAL_LINKS):
        sys.exit(f"expected {len(SOCIAL_LINKS)} social chips, found {len(groups)}")
    for g, link in zip(groups, SOCIAL_LINKS):
        svg = svg.replace(g, f'<a href="{link}">{g}</a>', 1)
    print(f"social: {len(groups)} chips linked")
    return svg


def no_xml_decl(svg):
    return re.sub(r"<\?xml[^>]*\?>\s*", "", svg, count=1).strip()


def install_readme(mark, end, block, img_fallback):
    """Replace marker block (idempotent) or, on first run, the old <img> block."""
    cur = open(README, encoding="utf-8").read()
    pat = re.compile(re.escape(mark) + r".*?" + re.escape(end), re.S)
    if pat.search(cur):
        cur = pat.sub(lambda _m: block, cur, count=1)
        print(f"README: marker block refreshed ({mark[:24]}…)")
    else:
        if not img_fallback.search(cur):
            sys.exit(f"README: neither marker block nor <img> fallback found for {mark!r}")
        cur = img_fallback.sub(lambda _m: block, cur, count=1)
        print(f"README: <img> block replaced with inline SVG ({mark[:24]}…)")
    open(README, "w", encoding="utf-8").write(cur)


def main():
    repos = fetch_repos()
    print(f"fetched {len(repos)} repos")

    # ---- what i build ----
    wib = open(os.path.join(GITSKINS, "what-i-build.svg"), encoding="utf-8").read()
    wib = make_wib_clickable(wib, repos)
    open(os.path.join(GITSKINS, "what-i-build.svg"), "w", encoding="utf-8").write(wib)
    wib_block = (
        f"{WIB_MARK}\n<div align=\"center\">\n{no_xml_decl(wib)}\n</div>\n{WIB_END}"
    )
    wib_img = re.compile(
        r'<p align="center">\s*'
        r'(?:<a href="https://github\.com/xvviix\?tab=repositories">\s*)?'
        r'<img src="https://raw\.githubusercontent\.com/xvviix/xvviix/main/gitskins/what-i-build\.svg"[^>]*/>\s*'
        r'(?:</a>\s*)?</p>'
    )
    install_readme(WIB_MARK, WIB_END, wib_block, wib_img)

    # ---- social ----
    soc = open(os.path.join(GITSKINS, "social.svg"), encoding="utf-8").read()
    soc = make_social_clickable(soc)
    open(os.path.join(GITSKINS, "social.svg"), "w", encoding="utf-8").write(soc)
    soc_block = (
        f"{SOC_MARK}\n<div align=\"center\">\n{no_xml_decl(soc)}\n</div>\n{SOC_END}"
    )
    soc_img = re.compile(
        r'<p align="center">\s*'
        r'<img src="https://raw\.githubusercontent\.com/xvviix/xvviix/main/gitskins/social\.svg"[^>]*/>\s*'
        r'</p>'
    )
    install_readme(SOC_MARK, SOC_END, soc_block, soc_img)
    print("done.")


if __name__ == "__main__":
    main()
