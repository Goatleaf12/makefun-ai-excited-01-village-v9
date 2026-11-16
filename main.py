#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The Village That Sailed the Sky.

A pure-Python-stdlib poster renderer (no network, no input files).
Draws a 1024x1024 PNG: a luminous floating village on a rock island
adrift in clouds, a waterfall pouring off the island's edge into a sea
of clouds below, one large sailing ship in the foreground before a
rising sun, one small distant ship, birds, god-rays, and a two-line
caption inside the image.

Fully deterministic: fixed seed 20261117, no clock, no network.
Two runs write byte-identical files.

Usage: python3 main.py
Output: $OUTPUT_PATH, else $MAKEFUN_OUTPUT_DIR/entry.png, else /output/entry.png
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
SEED = 20261117


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def blend(self, x, y, color, alpha):
        if 0 <= x < self.w and 0 <= y < self.h and alpha > 0.0:
            i = (y * self.w + x) * 3
            a = alpha if alpha <= 1.0 else 1.0
            self.px[i] = clamp(int(self.px[i] * (1 - a) + color[0] * a))
            self.px[i + 1] = clamp(int(self.px[i + 1] * (1 - a) + color[1] * a))
            self.px[i + 2] = clamp(int(self.px[i + 2] * (1 - a) + color[2] * a))

    def fill_rect(self, x0, y0, x1, y1, color, alpha=1.0):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                if alpha >= 1.0:
                    self.set(x, y, color)
                else:
                    self.blend(x, y, color, alpha)

    def disc(self, cx, cy, r, color, alpha=1.0):
        for y in range(max(0, cy - r), min(self.h, cy + r + 1)):
            for x in range(max(0, cx - r), min(self.w, cx + r + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    if alpha >= 1.0:
                        self.set(x, y, color)
                    else:
                        self.blend(x, y, color, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0):
        for y in range(max(0, cy - ry), min(self.h, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(self.w, cx + rx + 1)):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d <= 1.0:
                    # soften the rim so cloud blobs look fluffy
                    a = alpha * (1.0 - 0.55 * d * d)
                    self.blend(x, y, color, a)

    def line(self, x0, y0, x1, y1, color, thick=1, alpha=1.0):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            t = s / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            r = thick // 2
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    self.blend(x + dx, y + dy, color, alpha)

    def polygon(self, pts, color, alpha=1.0):
        # scanline fill for a simple (convex-ish) polygon
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(max(0, int(math.ceil(xs[k]))),
                               min(self.w, int(math.floor(xs[k + 1])) + 1)):
                    if alpha >= 1.0:
                        self.set(x, y, color)
                    else:
                        self.blend(x, y, color, alpha)


# ---- tiny 5x7 bitmap font (uppercase + space + period) ----
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
}


def draw_text(cv, text, cx, y, scale, color, shadow=True):
    cw = 6 * scale  # 5 px glyph + 1 px gap, scaled
    total = len(text) * cw - scale
    x = cx - total // 2
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "1":
                    px0 = x + col * scale
                    py0 = y + row * scale
                    if shadow:
                        cv.fill_rect(px0 + scale, py0 + scale,
                                     px0 + 2 * scale, py0 + 2 * scale,
                                     (20, 16, 40), alpha=0.55)
                    cv.fill_rect(px0, py0, px0 + scale, py0 + scale, color)
        x += cw


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def draw_sky(cv):
    # dawn gradient: deep indigo at the top, warm amber at the horizon
    stops = [(0.0, (16, 22, 62)), (0.35, (74, 52, 108)),
             (0.58, (196, 96, 96)), (0.68, (252, 172, 92)),
             (1.0, (255, 214, 150))]
    for y in range(H):
        t = y / (H - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                cv.fill_rect(0, y, W, y + 1, lerp(c0, c1, (t - t0) / (t1 - t0)))
                break


def draw_stars(cv, rng):
    for _ in range(90):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, 300)
        b = rng.randint(140, 255)
        cv.blend(x, y, (b, b, 255), 0.7)


def draw_sun(cv):
    # glow rings, then the disc
    for r, a in ((190, 0.10), (150, 0.14), (120, 0.20)):
        cv.disc(700, 560, r, (255, 214, 120), alpha=a)
    cv.disc(700, 560, 92, (255, 236, 170))
    cv.disc(700, 560, 78, (255, 244, 205))
    cv.disc(700, 560, 60, (255, 250, 225))


def draw_god_rays(cv):
    # translucent wedges fanning out from the sun
    for k, ang in enumerate((-38, -22, -6, 12, 30)):
        rad = math.radians(ang)
        x1 = int(700 + 560 * math.cos(rad - 0.045))
        y1 = int(560 + 560 * math.sin(rad - 0.045))
        x2 = int(700 + 560 * math.cos(rad + 0.045))
        y2 = int(560 + 560 * math.sin(rad + 0.045))
        cv.polygon([(700, 560), (x1, y1), (x2, y2)],
                   (255, 226, 150), alpha=0.07 if k % 2 else 0.10)


def cloud_blob(cv, rng, cx, cy, spread, color, alpha):
    for _ in range(9):
        ox = rng.randint(-spread, spread)
        oy = rng.randint(-spread // 3, spread // 3)
        rx = rng.randint(spread // 3, spread // 2 + 12)
        ry = rng.randint(spread // 6, spread // 4 + 8)
        cv.ellipse(cx + ox, cy + oy, rx, ry, color, alpha=alpha)


def draw_cloud_sea(cv, rng):
    # layered sea of clouds filling the lower third
    for cy in (700, 760, 830, 910, 980):
        tint = (255, 226, 205) if cy < 800 else (255, 240, 224)
        for cx in range(-40, W + 60, 90):
            cloud_blob(cv, rng, cx + rng.randint(-25, 25), cy + rng.randint(-14, 14),
                       95, tint, 0.85)
    # soft shadows between cloud banks
    for _ in range(26):
        cv.ellipse(rng.randint(0, W), rng.randint(720, 990),
                   rng.randint(40, 110), rng.randint(10, 22),
                   (214, 170, 190), alpha=0.16)


def draw_high_clouds(cv, rng):
    for _ in range(14):
        cx = rng.randint(0, W)
        cy = rng.randint(60, 260)
        cloud_blob(cv, rng, cx, cy, 70, (255, 220, 210), 0.35)


def draw_island(cv, rng):
    # rock body: wide grassy top tapering to a point below
    rock = [(205, 330), (815, 330), (780, 430), (700, 545),
            (580, 635), (512, 668), (448, 628), (330, 540), (238, 425)]
    cv.polygon(rock, (96, 70, 58))
    # rock shading: darker underside + strata bands
    cv.polygon([(238, 425), (330, 540), (448, 628), (512, 668),
                (580, 635), (700, 545), (780, 430), (815, 330),
                (700, 380), (512, 420), (330, 380)], (74, 52, 44), alpha=0.55)
    for y, w in ((470, 250), (540, 190), (600, 120)):
        cv.line(512 - w, y, 512 + w, y + 6, (60, 42, 36), thick=5, alpha=0.5)
    # grassy cap
    cv.ellipse(512, 332, 312, 42, (74, 140, 72))
    cv.ellipse(512, 322, 300, 30, (96, 164, 84))
    # warm rim light on the sun-facing (right) edge of the rock
    cv.line(780, 430, 700, 545, (255, 196, 110), thick=5, alpha=0.55)
    cv.line(700, 545, 580, 635, (255, 180, 100), thick=4, alpha=0.45)
    cv.line(205, 330, 815, 330, (255, 214, 140), thick=3, alpha=0.35)
    # hanging roots / vines under the rim
    for _ in range(12):
        x = rng.randint(260, 760)
        cv.line(x, 360, x + rng.randint(-6, 6), 360 + rng.randint(18, 46),
                (52, 96, 52), thick=2, alpha=0.8)


def draw_house(cv, x, y, w, h, wall, roof):
    # warm-lit house: walls, pitched roof, glowing windows, chimney
    cv.fill_rect(x, y, x + w, y + h, wall)
    cv.polygon([(x - 8, y), (x + w // 2, y - 34), (x + w + 8, y)], roof)
    cv.fill_rect(x + w - 18, y - 52, x + w - 8, y - 20, (120, 84, 60))
    # window glow halo, then the lit window itself
    for wx in (x + 12, x + w - 30):
        cv.fill_rect(wx - 5, y + 14, wx + 23, y + 36, (255, 200, 90), alpha=0.45)
        cv.fill_rect(wx, y + 18, wx + 18, y + 32, (255, 214, 110))
        cv.line(wx + 9, y + 18, wx + 9, y + 32, (90, 60, 30), thick=2)
    cv.fill_rect(x + w // 2 - 9, y + h - 26, x + w // 2 + 9, y + h,
                 (70, 44, 28))


def draw_village(cv, rng):
    houses = [
        (268, 268, 74, 62, (232, 196, 140), (168, 62, 52)),
        (360, 252, 86, 74, (214, 178, 128), (120, 58, 78)),
        (470, 258, 78, 66, (240, 208, 158), (70, 96, 120)),
        (566, 246, 90, 78, (226, 188, 136), (168, 62, 52)),
        (676, 266, 72, 60, (210, 172, 122), (96, 74, 110)),
    ]
    for hx, hy, hw, hh, wall, roof in houses:
        draw_house(cv, hx, hy, hw, hh, wall, roof)
    # a lantern post and a little tree between houses
    cv.line(448, 300, 448, 246, (40, 30, 24), thick=4)
    cv.disc(448, 238, 12, (255, 205, 100))
    cv.disc(448, 238, 20, (255, 205, 100), alpha=0.3)
    cv.line(620, 318, 620, 282, (70, 48, 30), thick=5)
    cv.disc(620, 268, 20, (52, 122, 60))
    cv.disc(608, 278, 14, (66, 140, 70))
    cv.disc(634, 278, 14, (66, 140, 70))
    # chimney smoke curls
    for sx, sy in ((342, 200), (452, 196), (648, 190)):
        for i in range(4):
            cv.disc(sx + i * 7 - 10, sy - i * 12, 9 - i,
                    (255, 240, 230), alpha=0.28)


def draw_waterfall(cv, rng):
    # pours off the island's left rim down into the cloud sea
    top_x, top_y, bot_y = 330, 352, 872
    for y in range(top_y, bot_y):
        t = (y - top_y) / (bot_y - top_y)
        wob = int(14 * math.sin(y * 0.045) + 8 * math.sin(y * 0.013))
        half = int(34 - 10 * t)
        cx = top_x + wob
        for x in range(cx - half, cx + half + 1):
            edge = abs(x - cx) / half
            base = lerp((190, 224, 245), (255, 255, 255), 1 - edge)
            streak = 0.5 + 0.5 * math.sin(x * 0.9 + y * 0.22)
            col = lerp(base, (255, 255, 255), streak * 0.35)
            cv.blend(x, y, col, 0.92)
    # foam where it meets the clouds
    cv.ellipse(330, 872, 78, 26, (255, 255, 255), alpha=0.9)
    cv.ellipse(330, 884, 56, 18, (235, 246, 252), alpha=0.85)
    # a second, thinner fall on the right rim
    for y in range(360, 640):
        t = (y - 360) / 280
        cx = 700 + int(8 * math.sin(y * 0.05))
        half = int(14 - 4 * t)
        for x in range(cx - half, cx + half + 1):
            cv.blend(x, y, (215, 236, 248), 0.85)


def draw_ship(cv, cx, cy, scale, sails=True):
    # hull
    hull = [(cx - 150 * scale, cy), (cx + 150 * scale, cy),
            (cx + 118 * scale, cy + 42 * scale),
            (cx - 118 * scale, cy + 42 * scale)]
    hull = [(int(a), int(b)) for a, b in hull]
    cv.polygon(hull, (74, 48, 34))
    cv.polygon([(hull[0][0], hull[0][1]), (hull[1][0], hull[1][1]),
                (hull[1][0], hull[1][1] + 8), (hull[0][0], hull[0][1] + 8)],
               (150, 96, 52))
    # deck cabins + bowsprit
    cv.fill_rect(int(cx - 60 * scale), int(cy - 26 * scale),
                 int(cx + 40 * scale), int(cy), (96, 64, 44))
    cv.line(int(cx + 150 * scale), int(cy - 4 * scale),
            int(cx + 196 * scale), int(cy - 30 * scale),
            (74, 48, 34), thick=int(4 * scale) or 2)
    if not sails:
        return
    # masts
    for mx in (-70, 30):
        cv.line(int(cx + mx * scale), int(cy),
                int(cx + mx * scale), int(cy - 190 * scale),
                (52, 36, 26), thick=int(5 * scale) or 2)
    # big cream sails, bellied by the wind
    cv.polygon([(int(cx - 70 * scale), int(cy - 186 * scale)),
                (int(cx - 70 * scale), int(cy - 22 * scale)),
                (int(cx - 150 * scale), int(cy - 30 * scale))],
               (250, 238, 210))
    cv.polygon([(int(cx - 66 * scale), int(cy - 186 * scale)),
                (int(cx - 66 * scale), int(cy - 22 * scale)),
                (int(cx + 6 * scale), int(cy - 34 * scale))],
               (244, 226, 192))
    cv.polygon([(int(cx + 30 * scale), int(cy - 160 * scale)),
                (int(cx + 30 * scale), int(cy - 22 * scale)),
                (int(cx + 108 * scale), int(cy - 30 * scale))],
               (250, 238, 210))
    cv.polygon([(int(cx + 34 * scale), int(cy - 160 * scale)),
                (int(cx + 34 * scale), int(cy - 22 * scale)),
                (int(cx - 26 * scale), int(cy - 34 * scale))],
               (238, 216, 178))
    # pennant on the main mast
    cv.polygon([(int(cx - 70 * scale), int(cy - 190 * scale)),
                (int(cx - 38 * scale), int(cy - 182 * scale)),
                (int(cx - 70 * scale), int(cy - 174 * scale))],
               (214, 64, 52))
    # warm lanterns on the stern
    for lx in (-128, 128):
        cv.disc(int(cx + lx * scale), int(cy - 12 * scale),
                max(3, int(5 * scale)), (255, 205, 100))


def draw_birds(cv, rng):
    for _ in range(9):
        x = rng.randint(60, 960)
        y = rng.randint(120, 420)
        s = rng.randint(7, 15)
        cv.line(x - s, y, x, y - s // 2, (40, 30, 48), thick=2)
        cv.line(x, y - s // 2, x + s, y, (40, 30, 48), thick=2)
    # three fixed birds circling high near the rising sun
    for bx, by, bs in ((588, 430, 12), (626, 452, 9), (812, 420, 11)):
        cv.line(bx - bs, by, bx, by - bs // 2, (40, 30, 48), thick=2)
        cv.line(bx, by - bs // 2, bx + bs, by, (40, 30, 48), thick=2)


def draw_caption(cv):
    # dark ribbon at the bottom, then two centred lines of text
    cv.fill_rect(0, 928, W, H, (24, 18, 52), alpha=0.42)
    draw_text(cv, "THE VILLAGE THAT SAILED THE SKY", 512, 940, 3,
              (255, 244, 214))
    draw_text(cv, "A HOME ABOVE THE SEA OF CLOUDS", 512, 978, 2,
              (255, 214, 150))


def render():
    rng = random.Random(SEED)
    cv = Canvas(W, H)
    draw_sky(cv)
    draw_stars(cv, rng)
    draw_sun(cv)
    draw_god_rays(cv)
    draw_high_clouds(cv, rng)
    draw_island(cv, rng)
    draw_village(cv, rng)
    draw_waterfall(cv, rng)
    draw_cloud_sea(cv, rng)
    # distant small ship on the horizon, then the hero ship
    draw_ship(cv, 838, 668, 0.30, sails=True)
    draw_ship(cv, 430, 806, 1.0, sails=True)
    draw_birds(cv, rng)
    draw_caption(cv)
    return cv


def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw.extend(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])
    comp = zlib.compress(bytes(raw), level=9)

    def chunk(ctype, data):
        out = struct.pack(">I", len(data)) + ctype + data
        out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out = os.environ.get("OUTPUT_PATH")
    if not out:
        d = os.environ.get("MAKEFUN_OUTPUT_DIR")
        out = os.path.join(d, "entry.png") if d else "/output/entry.png"
    cv = render()
    size = write_png(cv, out)
    print(f"wrote {out} ({size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
