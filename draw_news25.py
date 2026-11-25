"""News-image generator for 25 Nov 2026 (1024x1024 PNG, deterministic).

Fresh build for news-image-20261125, based on the reusable draw_news.py
layout, upgraded with the leaders' visual format: illustrated hero icons,
a schematic dot-map, a DAY IN NUMBERS strip, and a prominent DATE CHECK box.

Usage:
    python3 draw_news25.py stories.json [output.png]

stories.json: same schema as draw_news.py (1 main, 4 featured, 45 one-liners).
Deterministic: the same JSON always produces byte-identical output.
"""

import json
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
BG = (255, 255, 255)
NAVY = (13, 27, 62)
NAVY2 = (24, 48, 105)
GOLD = (201, 162, 39)
INK = (17, 24, 39)
MUTED = (90, 98, 115)
RULE = (214, 219, 228)
RED = (176, 32, 32)
LIGHT = (244, 246, 249)
TINT = (253, 240, 240)


def font(bold, size):
    p = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(p, size)


F_DATE = font(True, 44)
F_SUB = font(False, 18)
F_BADGE = font(True, 17)
F_MAIN = font(True, 29)
F_MAIN_SUB = font(False, 17)
F_FEAT = font(True, 17)
F_FEAT_SUB = font(False, 14)
F_ONE = font(False, 12)
F_ONE_B = font(True, 12)
F_FOOT = font(False, 12)
F_FOOT_B = font(True, 12)
F_NUM = font(True, 20)
F_NUM_L = font(True, 10)
F_SEC = font(True, 13)

# Schematic world map, 52 cols x 20 rows ('#' = land). Rough, dot-rendered.
WORLD_MAP = [
    "                                                    ",
    "   ###########      ###        ###############      ",
    "  ##############   ###   #######################   ",
    "   #############        #######################    ",
    "    ###########         ##################  ##     ",
    "     #########           ################  ##      ",
    "      #######             ##############           ",
    "       #####        ########  ##########            ",
    "        ####        #########  ########             ",
    "                  ##########   ######               ",
    "             ##### ##########    ####  ###           ",
    "            ####### #########     ##   ####          ",
    "            ####### ########      #    ###           ",
    "             ######  ######                         ",
    "             #####   #####                           ",
    "              ####    ###          ######            ",
    "              ###                ########           ",
    "               ##                 ######  #         ",
    "                                 ####              ",
    "                                                    ",
]
# Gold dots: (col, row) story locations on the map above.
MAP_DOTS = [
    (46, 5),   # Tokyo
    (44, 4),   # Seoul
    (45, 6),   # Taipei
    (42, 5),   # Shanghai
    (31, 8),   # Riyadh / Hodeidah region
    (25, 4),   # London / Europe
    (10, 5),   # New York
    (9, 10),   # Panama / Colombia
    (47, 15),  # Solomons / Fiji
    (46, 16),  # Sydney
]

NUMBERS = [
    ("-5.3%", "KOSPI"),
    ("-2.8%", "NIKKEI"),
    ("$90.97", "BRENT"),
    ("$59,258", "BITCOIN"),
]


def icon_ball(d, x, y, s):
    """Soccer ball: circle + pentagon + seams (white on navy square)."""
    cx, cy, r = x + s // 2, y + s // 2, s // 2 - 4
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=3)
    d.regular_polygon((cx, cy, 7), n_sides=5, fill=(255, 255, 255))
    for ang in (30, 150, 270):
        import math
        a = math.radians(ang)
        x2 = cx + int(r * 0.95 * math.cos(a))
        y2 = cy + int(r * 0.95 * math.sin(a))
        d.line([cx, cy, x2, y2], fill=(255, 255, 255), width=2)


def icon_building(d, x, y, s):
    """Government building: pediment + columns + base."""
    w = (255, 255, 255)
    d.polygon([(x + 6, y + 16), (x + s // 2, y + 6), (x + s - 6, y + 16)], fill=w)
    d.rectangle([x + 6, y + 18, x + s - 6, y + 21], fill=w)
    for i in range(3):
        cx = x + 12 + i * (s - 24) // 2
        d.rectangle([cx, y + 23, cx + 5, y + s - 14], fill=w)
    d.rectangle([x + 6, y + s - 12, x + s - 6, y + s - 8], fill=w)


def icon_ship(d, x, y, s):
    """Ship: hull + mast + flag."""
    w = (255, 255, 255)
    d.polygon([(x + 8, y + s - 16), (x + s - 8, y + s - 16),
               (x + s - 14, y + s - 8), (x + 14, y + s - 8)], fill=w)
    d.line([x + s // 2, y + 8, x + s // 2, y + s - 16], fill=w, width=3)
    d.polygon([(x + s // 2, y + 8), (x + s // 2 + 14, y + 12),
               (x + s // 2, y + 16)], fill=w)
    d.line([x + 8, y + s - 20, x + s - 8, y + s - 20], fill=w, width=2)


def icon_shield(d, x, y, s):
    """Shield + check mark (pact)."""
    w = (255, 255, 255)
    d.polygon([(x + 8, y + 6), (x + s - 8, y + 6), (x + s - 8, y + s // 2),
               (x + s // 2, y + s - 6), (x + 8, y + s // 2)], outline=w, width=3)
    d.line([x + s // 2 - 9, y + s // 2, x + s // 2 - 2, y + s // 2 + 8,
            x + s // 2 + 11, y + s // 2 - 8], fill=w, width=3)


ICONS = [icon_building, icon_ship, icon_shield, icon_ball]


def draw(data, out_path):
    n = len(data["one_liners"])
    assert n == 45, f"expected 45 one-liners, got {n}"
    assert len(data["featured"]) == 4, "expected 4 featured stories"

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ---- header band ----
    d.rectangle([0, 0, W, 112], fill=NAVY)
    d.text((28, 14), data["date_long"], font=F_DATE, fill=(255, 255, 255))
    d.text((28, 68), data["subtitle"], font=F_SUB, fill=(196, 205, 225))
    badge = f"{n + 5} STORIES"
    bw = d.textlength(badge, font=F_BADGE) + 28
    d.rounded_rectangle([W - bw - 28, 32, W - 28, 72], radius=20, fill=GOLD)
    d.text((W - bw - 14, 41), badge, font=F_BADGE, fill=NAVY)

    y = 112
    # ---- main story + plunging-chart pictogram ----
    d.rectangle([0, y, W, y + 7], fill=GOLD)
    y += 7
    d.text((28, y + 10), "THE DAY IN ONE LINE", font=F_BADGE, fill=RED)
    main_lines = textwrap.wrap(data["main"][0], width=38)
    yy = y + 36
    for ln in main_lines:
        d.text((28, yy), ln, font=F_MAIN, fill=INK)
        yy += 34
    d.text((28, yy + 2), data["main"][1], font=F_MAIN_SUB, fill=MUTED)
    # chart: falling line, right side of the main block
    cx0, cy0, cw, ch = 818, y + 34, 178, 84
    d.rectangle([cx0, cy0, cx0 + cw, cy0 + ch], fill=LIGHT, outline=RULE)
    pts = [(cx0 + 10 + i * 24, cy0 + 12 + i * 10 + (0 if i < 2 else 8))
           for i in range(7)]
    d.line(pts, fill=RED, width=3)
    for px, py in pts:
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=RED)
    d.text((cx0 + 10, cy0 + ch - 20), "-5.3% KOSPI", font=F_NUM_L, fill=RED)
    y = yy + 38
    d.line([28, y, W - 28, y], fill=RULE, width=2)

    # ---- featured 2x2 with icons ----
    y += 12
    d.text((28, y), "FEATURED", font=F_BADGE, fill=RED)
    y += 26
    col_w = (W - 56 - 24) // 2
    row_h = 98
    for i, (h, s) in enumerate(data["featured"]):
        cx = 28 + (i % 2) * (col_w + 24)
        cy = y + (i // 2) * row_h
        d.rectangle([cx, cy, cx + 56, cy + 56], fill=NAVY2)
        ICONS[i](d, cx, cy, 56)
        tx = cx + 68
        hl = textwrap.wrap(h, width=32)
        ty = cy
        for ln in hl:
            d.text((tx, ty), ln, font=F_FEAT, fill=INK)
            ty += 21
        sl = textwrap.wrap(s, width=40)
        for ln in sl[:2]:
            d.text((tx, ty + 2), ln, font=F_FEAT_SUB, fill=MUTED)
            ty += 18
    y += row_h * 2 + 4
    d.line([28, y, W - 28, y], fill=RULE, width=2)

    # ---- map + numbers band ----
    y += 10
    d.text((28, y), "WHERE IT HAPPENED", font=F_SEC, fill=RED)
    d.text((560, y), "THE DAY IN NUMBERS", font=F_SEC, fill=RED)
    y += 22
    band_h = 82
    # dot map (left)
    mx, my = 28, y
    cell = 9
    for r, row in enumerate(WORLD_MAP):
        for c, ch in enumerate(row):
            if ch == "#":
                px, py = mx + c * cell + cell // 2, my + r * 4 + 2
                d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=NAVY2)
    for c, r in MAP_DOTS:
        px, py = mx + c * cell + cell // 2, my + r * 4 + 2
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=GOLD,
                  outline=NAVY, width=1)
    # numbers (right): 4 stat boxes
    nx = 560
    sw = (W - 28 - nx - 3 * 8) // 4
    for i, (val, lab) in enumerate(NUMBERS):
        x0 = nx + i * (sw + 8)
        d.rectangle([x0, y, x0 + sw, y + band_h], fill=LIGHT, outline=RULE)
        vw = d.textlength(val, font=F_NUM)
        d.text((x0 + (sw - vw) / 2, y + 12), val, font=F_NUM,
               fill=RED if val.startswith("-") else INK)
        lw = d.textlength(lab, font=F_NUM_L)
        d.text((x0 + (sw - lw) / 2, y + 46), lab, font=F_NUM_L, fill=MUTED)
    y += band_h + 6
    d.line([28, y, W - 28, y], fill=RULE, width=2)

    # ---- one-liners, 3 columns x 15 rows ----
    y += 10
    d.text((28, y), "THE REST OF THE DAY", font=F_BADGE, fill=RED)
    y += 24
    cols = 3
    rows = 15
    cw = (W - 56 - 2 * 20) // cols
    rh = 20
    for idx, (tag, txt) in enumerate(data["one_liners"]):
        c = idx // rows
        r = idx % rows
        x = 28 + c * (cw + 20)
        yy = y + r * rh
        d.text((x, yy), tag, font=F_ONE_B, fill=NAVY2)
        tw = d.textlength(tag, font=F_ONE_B)
        avail = cw - tw - 8
        t = txt
        while d.textlength(t, font=F_ONE) > avail and len(t) > 4:
            t = t[:-1]
        if t != txt:
            t = t[:-3] + "..."
        d.text((x + tw + 8, yy), t, font=F_ONE, fill=INK)
    y += rows * rh + 6
    d.line([28, y, W - 28, y], fill=RULE, width=2)

    # ---- footer ----
    y += 8
    footer = f"{n + 5} STORIES  ·  {data['regions']} REGIONS  ·  {data['fields']} FIELDS"
    d.text((28, y), footer, font=F_FOOT_B, fill=NAVY)
    d.text((W - 28 - d.textlength(data["date_short"], font=F_FOOT_B), y),
           data["date_short"], font=F_FOOT_B, fill=RED)
    y += 22
    # date-check box
    box_h = 26
    d.rectangle([28, y, W - 28, y + box_h], fill=TINT, outline=RED, width=2)
    dc = "DATE CHECK  " + data["date_check"]
    d.text((36, y + 6), dc, font=F_FOOT_B, fill=RED)

    img.save(out_path, optimize=True)
    print("saved", out_path, img.size)


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        data = json.load(f)
    draw(data, sys.argv[2] if len(sys.argv) > 2 else "entry.png")
    import os
    print("bytes:", os.path.getsize(sys.argv[2] if len(sys.argv) > 2 else "entry.png"))
