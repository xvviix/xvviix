#!/usr/bin/env python3
"""
Gitskins-kit stack catalog card for the xvviix profile.

Builds gitskins/stack-grid.svg — the "Stack" section as an aurora-dark
card: every tech from the old README table rendered as icon + label
cells (icons from stack-icons/, embedded as data URIs so the card is
fully self-contained).

Usage:  python3 gen_stack_grid.py       (needs Pillow for the .png icons)
"""
import base64
import io
import os
import xml.dom.minidom
import xml.sax.saxutils

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICONS = os.path.join(ROOT, "stack-icons")
OUT = os.path.join(ROOT, "gitskins", "stack-grid.svg")

# (icon file, label) in showcase order — 5 cols x 4 rows
ITEMS = [
    ("html5.svg", "HTML5"), ("css3.svg", "CSS3"), ("javascript.svg", "JavaScript"),
    ("react.svg", "React"), ("nextjs.svg", "Next.js"),
    ("threejs.svg", "Three.js / R3F"), ("nodejs.svg", "Node.js"), ("git.svg", "Git"),
    ("github.svg", "GitHub"), ("markdown.svg", "Markdown"),
    ("python.svg", "Python"), ("tkinter.svg", "Tkinter"), ("paddleocr.png", "PaddleOCR"),
    ("pymupdf.svg", "PyMuPDF"), ("pillow.png", "Pillow"),
    ("github-actions.svg", "GitHub Actions"), ("github-pages.svg", "GitHub Pages"),
    ("lenis.svg", "Lenis"), ("json.svg", "JSON-LD & SEO"),
]


def e(t):
    return xml.sax.saxutils.escape(str(t), {'"': "&quot;"})


def icon_data_uri(fname: str) -> str:
    path = os.path.join(ICONS, fname)
    if fname.endswith(".svg"):
        data = open(path, "rb").read()
        return "data:image/svg+xml;base64," + base64.b64encode(data).decode()
    # png: normalize to a 40px-wide box (keep aspect)
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    nh = max(1, round(40 * h / w))
    if nh > 40:
        nw = 40
        im = im.resize((nw, 40), Image.LANCZOS)
    else:
        im = im.resize((40, nh), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    from PIL import Image  # report actual icon dims for centering
    cells = []
    for idx, (fname, label) in enumerate(ITEMS):
        col, row = idx % 5, idx // 5
        x = 46 + col * 154.5
        y = 100 + row * 84
        uri = icon_data_uri(fname)
        if fname.endswith(".svg"):
            iw = ih = 40
        else:
            w, h = Image.open(os.path.join(ICONS, fname)).size
            nh = max(1, round(40 * h / w))
            if nh > 40:
                iw = ih = 40
            else:
                iw, ih = 40, nh
        icon_x = x + (150 - iw) / 2
        icon_y = y + (44 - ih) / 2 + 4
        cells.append(f'''    <g class="sg-cell" style="animation-delay:{idx * 40}ms">
      <rect x="{x:.1f}" y="{y:.0f}" width="150" height="74" rx="12" fill="rgba(8,8,12,0.5)" stroke="#2dd4bf" stroke-opacity="0.28"/>
      <image href="{uri}" x="{icon_x:.1f}" y="{icon_y:.1f}" width="{iw}" height="{ih}" preserveAspectRatio="xMidYMid meet"/>
      <text x="{x + 75:.1f}" y="{y + 64:.0f}" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="10" font-weight="700" fill="#ccfbf1">{e(label)}</text>
    </g>''')
    # 20th decorative cell
    x = 46 + 4 * 154.5
    y = 100 + 3 * 84
    cells.append(f'''    <g class="sg-cell" style="animation-delay:{len(ITEMS) * 40}ms">
      <rect x="{x:.1f}" y="{y:.0f}" width="150" height="74" rx="12" fill="rgba(8,8,12,0.3)" stroke="#d4af37" stroke-opacity="0.4" stroke-dasharray="5 6"/>
      <text x="{x + 75:.1f}" y="{y + 36:.0f}" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="13" fill="#f5d061">✦</text>
      <text x="{x + 75:.1f}" y="{y + 56:.0f}" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="9.5" font-weight="700" fill="#f5d061" opacity="0.85">more in repos ↗</text>
    </g>''')

    rows = max(i // 5 for i in range(len(ITEMS) + 1)) + 1
    card_h = (100 + rows * 84 - 10 + 26) - 26
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="860" height="{card_h + 52}" viewBox="0 0 860 {card_h + 52}" role="img" aria-label="GitSkins gs-stack-grid-xvviix-aurora-dark section">
  <defs>
    <linearGradient id="gs-sg-bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#042f2e"/>
      <stop offset="54%" stop-color="#134e4a"/>
      <stop offset="100%" stop-color="#042f2e"/>
    </linearGradient>
    <radialGradient id="gs-sg-orb-0" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2dd4bf" stop-opacity="0.55"/>
      <stop offset="58%" stop-color="#2dd4bf" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="#2dd4bf" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gs-sg-orb-1" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#a78bfa" stop-opacity="0.42"/>
      <stop offset="58%" stop-color="#a78bfa" stop-opacity="0.13"/>
      <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gs-sg-orb-2" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#d4af37" stop-opacity="0.38"/>
      <stop offset="58%" stop-color="#d4af37" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#d4af37" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <style>
    #gs-sg-aurora-dark .sg-orb-a {{ animation: gs-sg-float-a 9s ease-in-out infinite; }}
    #gs-sg-aurora-dark .sg-orb-b {{ animation: gs-sg-float-b 11s ease-in-out infinite 1.1s; }}
    #gs-sg-aurora-dark .sg-cell {{ animation: gs-sg-chip 600ms ease-out both; }}
    @keyframes gs-sg-float-a {{ 0%,100% {{ transform: translate(0,0); opacity: .55; }} 50% {{ transform: translate(26px,-18px); opacity: .82; }} }}
    @keyframes gs-sg-float-b {{ 0%,100% {{ transform: translate(0,0); opacity: .4; }} 50% {{ transform: translate(-22px,16px); opacity: .68; }} }}
    @keyframes gs-sg-chip {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  </style>
  <g id="gs-sg-aurora-dark">
    <rect width="860" height="{card_h + 52}" rx="20" fill="url(#gs-sg-bg)"/>
    <ellipse class="sg-orb-a" cx="140" cy="70" rx="215" ry="115" fill="url(#gs-sg-orb-0)"/>
    <ellipse class="sg-orb-b" cx="710" cy="60" rx="235" ry="105" fill="url(#gs-sg-orb-1)"/>
    <ellipse class="sg-orb-a" cx="500" cy="{card_h + 30}" rx="300" ry="95" fill="url(#gs-sg-orb-2)"/>
    <rect x="28" y="26" width="804" height="{card_h}" rx="20" fill="rgba(8,8,12,0.5)" stroke="#2dd4bf" stroke-opacity="0.48"/>
    <text x="46" y="61" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" font-size="28" font-weight="850" letter-spacing="-0.5" fill="#ccfbf1">Stack</text>
    <text x="48" y="84" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" font-size="13" font-weight="650" letter-spacing="1.2" fill="#5eead4">Everyday tools — the full kit behind every site</text>
{chr(10).join(cells)}
    <rect x="0.5" y="0.5" width="859" height="{card_h + 51}" rx="19.5" fill="none" stroke="#2dd4bf" stroke-opacity="0.62"/>
  </g>
</svg>
'''
    xml.dom.minidom.parseString(svg)
    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    if old != svg:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {OUT} ({len(svg)} bytes)")
    else:
        print("stack-grid unchanged")


if __name__ == "__main__":
    main()
