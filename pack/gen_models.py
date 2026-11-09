#!/usr/bin/env python3
"""ValqLegends resource pack, version 2: real 3D models (cuboid elements) for every weapon.

usage: python gen_models.py <out.zip> [preview.png]
Every weapon is a stack of small boxes (blade slices with a ridge and bevelled sides, guards, grips, gems, orbs, spikes)
painted from a 16-colour palette texture, so the game's face shading gives the volume. Models are built pointing up (+Y);
the display transforms lay them into the hand, the inventory and item frames. Preview: a small software renderer.
Needs Pillow and numpy.
"""
import hashlib, io, json, math, os, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw

C = 8.0   # centre of the 16 x 16 frame


def rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def mix(a, b, t): return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
def lt(c, t=0.35): return mix(c, (255, 255, 255), t)
def dk(c, t=0.4): return mix(c, (0, 0, 0), t)


class Model:
    def __init__(self):
        self.els = []          # (from, to, color, rotation or None)
        self.colors = []       # palette order

    def col(self, c):
        if c not in self.colors: self.colors.append(c)
        return self.colors.index(c)

    def box(self, x0, y0, z0, x1, y1, z1, color, rot=None):
        """rot = (axis, angle, origin) with the angle in 22.5 degree steps."""
        self.els.append(((min(x0, x1), min(y0, y1), min(z0, z1)), (max(x0, x1), max(y0, y1), max(z0, z1)), self.col(color), rot))

    # ------------------------------------------------------------ parts
    def blade(self, y0, y1, w0, w1, thick, mid, edge, tip=True, shift=lambda t: 0.0, steps=None, ridge=0.7):
        """a blade slice by slice: a thick ridge in the middle, bevelled thinner sides; width tapers w0 -> w1, optional sideways bend."""
        w0 *= 1.3; w1 *= 1.3; thick *= 1.3
        n = steps or max(6, int((y1 - y0) * 1.6))
        for i in range(n):
            t = i / n; ya = y0 + (y1 - y0) * t; yb = y0 + (y1 - y0) * (i + 1) / n
            w = (w0 + (w1 - w0) * t) / 2; sh = shift(t)
            if tip and i >= n - 2: w = max(0.5, w * (0.55 if i == n - 2 else 0.3))
            self.box(C - w * ridge + sh, ya, C - thick / 2, C + w * ridge + sh, yb, C + thick / 2, mid)
            self.box(C - w + sh, ya, C - thick * 0.3, C - w * ridge + sh, yb, C + thick * 0.3, edge)
            self.box(C + w * ridge + sh, ya, C - thick * 0.3, C + w + sh, yb, C + thick * 0.3, edge)
            if i % 3 == 1 and i < n - 3 and w > 1.2:        # engraved runes along the ridge
                self.box(C - 0.35 + sh, ya + 0.2, C + thick / 2, C + 0.35 + sh, ya + 0.9, C + thick / 2 + 0.2, lt(mid, 0.55))
                self.box(C - 0.35 + sh, ya + 0.2, C - thick / 2 - 0.2, C + 0.35 + sh, ya + 0.9, C - thick / 2, lt(mid, 0.55))

    def guard(self, y, width, col, trim, thick=2.4, style="bar"):
        width *= 1.25; thick *= 1.2
        if style == "bar":
            self.box(C - width / 2, y, C - thick / 2, C + width / 2, y + 1.6, C + thick / 2, col)
            self.box(C - width / 2 - 0.8, y - 0.4, C - thick / 2, C - width / 2 + 0.4, y + 2.6, C + thick / 2, trim)
            self.box(C + width / 2 - 0.4, y - 0.4, C - thick / 2, C + width / 2 + 0.8, y + 2.6, C + thick / 2, trim)
        elif style == "wing":
            for s in (-1, 1):
                for k in range(4):
                    x = C + s * (1.2 + k * width / 7.0)
                    self.box(min(x, x + s * width / 7), y + k * 0.9, C - thick / 2, max(x, x + s * width / 7), y + 1.6 + k * 0.9, C + thick / 2, col if k % 2 == 0 else trim)
            self.box(C - 1.6, y - 0.4, C - thick / 2 - 0.2, C + 1.6, y + 1.8, C + thick / 2 + 0.2, trim)
        elif style == "spike":
            self.box(C - width / 2, y, C - thick / 2, C + width / 2, y + 1.6, C + thick / 2, col)
            for s in (-1, 1):
                self.box(C + s * width / 2 - (0.6 if s > 0 else -0.6) * 0 - 0.6, y + 1.6, C - 0.8, C + s * width / 2 + 0.6, y + 3.6, C + 0.8, trim)
                self.box(C + s * (width / 2 + 0.2) - 0.4, y + 3.6, C - 0.5, C + s * (width / 2 + 0.2) + 0.4, y + 4.8, C + 0.5, trim)
        else:  # curved quillons
            self.box(C - 1.4, y, C - thick / 2, C + 1.4, y + 1.6, C + thick / 2, col)
            for s in (-1, 1):
                self.box(C + s * 1.4 - 0.7, y - 0.2, C - 1, C + s * 1.4 + 0.7 + s * 1.4, y + 1.2, C + 1, col)
                self.box(C + s * 3.2 - 0.6, y - 1.4, C - 0.8, C + s * 3.2 + 0.6, y + 0.2, C + 0.8, trim)

    def grip(self, y0, y1, col, wrap, r=0.9):
        self.box(C - r, y0, C - r, C + r, y1, C + r, col)
        y = y0 + 0.6
        while y < y1 - 0.5:
            self.box(C - r - 0.18, y, C - r - 0.18, C + r + 0.18, y + 0.55, C + r + 0.18, wrap); y += 1.3

    def gem(self, cx, cy, cz, r, col, hi=None):
        self.box(cx - r, cy - r, cz - r * 0.85, cx + r, cy + r, cz + r * 0.85, col)
        self.box(cx - r, cy - r, cz - r * 0.85, cx + r, cy + r, cz + r * 0.85, lt(col, 0.2), ("z", 45.0, (cx, cy, cz)))
        if hi: self.box(cx - r * 0.35, cy + r * 0.1, cz + r * 0.8, cx + r * 0.15, cy + r * 0.6, cz + r * 0.95, hi)

    def orb(self, cx, cy, cz, r, col):
        r *= 1.2
        self.box(cx - r, cy - r, cz - r, cx + r, cy + r, cz + r, dk(col, 0.25))
        self.box(cx - r * 0.85, cy - r * 0.85, cz - r * 0.85, cx + r * 0.85, cy + r * 0.85, cz + r * 0.85, col, ("y", 45.0, (cx, cy, cz)))
        self.box(cx - r * 0.85, cy - r * 0.85, cz - r * 0.85, cx + r * 0.85, cy + r * 0.85, cz + r * 0.85, lt(col, 0.2), ("x", 45.0, (cx, cy, cz)))
        self.box(cx - r * 0.45, cy - r * 0.1, cz + r * 0.6, cx, cy + r * 0.5, cz + r * 1.05, lt(col, 0.8))

    def pole(self, y0, y1, col, r=0.8, trim=None):
        self.box(C - r, y0, C - r, C + r, y1, C + r, col)
        if trim:
            y = y0 + 3
            while y < y1 - 2: self.box(C - r - 0.2, y, C - r - 0.2, C + r + 0.2, y + 0.7, C + r + 0.2, trim); y += 4.5

    def pommel(self, y, r, col, gem_col=None):
        self.box(C - r, y - r, C - r, C + r, y + r, C + r, col)
        self.box(C - r, y - r, C - r, C + r, y + r, C + r, lt(col, 0.2), ("y", 45.0, (C, y, C)))
        if gem_col: self.box(C - 0.5, y - 0.5, C + r - 0.1, C + 0.5, y + 0.5, C + r + 0.35, gem_col)

    # ------------------------------------------------------------ output
    def palette_png(self):
        im = Image.new("RGBA", (32, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for i, c in enumerate(self.colors):
            x, y = (i % 8) * 4, (i // 8) * 4
            d.rectangle((x, y, x + 3, y + 3), fill=c + (255,))
        return im

    def uv(self, i):
        x, y = (i % 8) * 4 + 1, (i // 8) * 4 + 1
        return [x, y, x + 2, y + 2]

    def fit(self):
        """models must stay inside -16..32: shrink the whole model about its base if it sticks out."""
        top = max(max(a[1], b[1]) for a, b, _, _ in self.els)
        side = max(max(abs(a[0] - 8), abs(b[0] - 8), abs(a[2] - 8), abs(b[2] - 8)) for a, b, _, _ in self.els)
        f = min(1.0, 31.5 / top if top > 31.5 else 1.0, 23.5 / side if side > 23.5 else 1.0)
        if f >= 0.999: return
        sc = lambda p: (8 + (p[0] - 8) * f, p[1] * f, 8 + (p[2] - 8) * f)
        self.els = [(sc(a), sc(b), ci, (rot[0], rot[1], sc(rot[2])) if rot else None) for a, b, ci, rot in self.els]

    def json(self, tex, display):
        self.fit()
        els = []
        for (a, b, ci, rot) in self.els:
            f = {k: {"uv": self.uv(ci), "texture": "#0"} for k in ("north", "south", "east", "west", "up", "down")}
            e = {"from": [round(v, 3) for v in a], "to": [round(v, 3) for v in b], "faces": f}
            if rot: e["rotation"] = {"origin": [round(v, 3) for v in rot[2]], "axis": rot[0], "angle": rot[1]}
            els.append(e)
        return {"textures": {"0": tex, "particle": tex}, "elements": els, "display": display}


# ---------------------------------------------------------------- the weapons (all built pointing up, centre x = z = 8)
def crimson_fang():
    m = Model(); r = rgb("#C0392B")
    m.blade(9, 31, 5.0, 1.4, 1.8, r, dk(r, 0.3), shift=lambda t: -3.2 * t * t)
    m.guard(7.5, 7.0, rgb("#3C3C46"), rgb("#7A1F2A"), style="spike"); m.grip(2.5, 7.5, rgb("#2B1418"), rgb("#8B2330"))
    m.pommel(1.6, 1.6, rgb("#3C3C46"), rgb("#FF4D5E")); m.gem(C, 8.9, C + 0.9, 0.9, rgb("#FF4D5E"), rgb("#FFC1C8")); return m
def inferno_scythe():
    m = Model(); o = rgb("#FF8C1E")
    m.pole(0, 27, rgb("#5B3A1E"), 0.9, rgb("#C0752A"))
    m.blade(24, 31, 3.0, 2.2, 1.6, o, rgb("#C45A0B"), tip=False)
    for i in range(10):
        t = i / 10; m.box(C + 1 + t * 8.5, 26.5 + math.sin(t * 2.4) * 4.2 - t * 5.5, C - 0.8, C + 2.4 + t * 8.5, 29.2 + math.sin(t * 2.4) * 4.2 - t * 6.5, C + 0.8, lt(o, 0.2 * (1 - t)) if i % 3 else o)
    m.orb(C, 29, C, 1.4, rgb("#FFB347")); m.gem(C, 24, C + 0.9, 0.8, rgb("#FFD27A")); return m
def soul_staff():
    m = Model(); b = rgb("#5DADE2")
    m.pole(0, 22, rgb("#96601E"), 0.9, rgb("#E0A53A"))
    for s in (-1, 1):
        m.box(C + s * 2.3 - 0.4, 22, C - 0.4, C + s * 2.3 + 0.4, 28.5, C + 0.4, rgb("#44445A"))
        m.box(C + s * 1.0 - 0.4, 28.4, C - 0.4, C + s * 1.0 + 0.4, 30.2, C + 0.4, rgb("#44445A"))
    m.box(C - 0.4, 22, C + 2.3 - 0.4, C + 0.4, 28.5, C + 2.3 + 0.4, rgb("#44445A")); m.box(C - 0.4, 22, C - 2.3 - 0.4, C + 0.4, 28.5, C - 2.3 + 0.4, rgb("#44445A"))
    m.orb(C, 26, C, 1.9, b); m.guard(21, 4.5, rgb("#55556B"), rgb("#9AA0B5"), style="curve"); return m
def warden_mace():
    m = Model(); t = rgb("#1FA896")
    m.pole(0, 22, rgb("#173F44"), 0.9, rgb("#2E8F8A"))
    m.box(C - 3, 20, C - 3, C + 3, 30, C + 3, rgb("#12494F")); m.box(C - 3.5, 22, C - 3.5, C + 3.5, 28, C + 3.5, t)
    m.box(C - 3, 20, C - 3, C + 3, 30, C + 3, lt(t, 0.15), ("y", 45.0, (C, 25, C)))
    for dx, dz in ((-3.8, 0), (3.8, 0), (0, -3.8), (0, 3.8)):
        m.box(C + dx - 0.9, 23, C + dz - 0.9, C + dx + 0.9, 27, C + dz + 0.9, rgb("#0E7C73")); m.box(C + dx - 0.4, 27, C + dz - 0.4, C + dx + 0.4, 29, C + dz + 0.4, rgb("#0E7C73"))
    m.box(C - 1, 30, C - 1, C + 1, 32, C + 1, rgb("#6FFFE9")); m.gem(C, 25, C + 3.6, 1.2, rgb("#7CFFEE"), rgb("#E8FFFB")); return m
def storm_trident():
    m = Model(); g = rgb("#E0B93A")
    m.pole(0, 25, rgb("#C99A2E"), 0.6, rgb("#7A5A15"))
    for dx, h in ((-3.0, 4.5), (0, 7), (3.0, 4.5)):
        m.box(C + dx - 0.55, 24, C - 0.5, C + dx + 0.55, 24 + h, C + 0.5, g); m.box(C + dx - 0.9, 24 + h, C - 0.5, C + dx + 0.9, 24 + h + 1.4, C + 0.5, lt(g, 0.4), ("z", 45.0, (C + dx, 24 + h + .7, C)))
    m.box(C - 3.6, 23.2, C - 0.6, C + 3.6, 24.6, C + 0.6, g); m.orb(C, 22, C, 1.2, rgb("#7FD4FF")); m.pommel(0.5, 1.0, g); return m
def thorn_blade():
    m = Model(); g = rgb("#2FBF5B")
    m.blade(9, 30, 3.8, 1.4, 1.8, g, dk(g, 0.35), shift=lambda t: 0.8 * math.sin(t * 9))
    for i in range(7):
        y = 11 + i * 3; s = 1 if i % 2 else -1
        m.box(C + s * 2.0, y, C - 0.5, C + s * 3.9, y + 1.6, C + 0.5, lt(g, 0.25), ("z", 22.5 * s, (C + s * 2.5, y, C)))
    m.guard(7.5, 6, rgb("#355E35"), rgb("#7BE07B"), style="curve"); m.grip(2.5, 7.5, rgb("#4B3320"), rgb("#2E8F4B")); m.pommel(1.6, 1.5, rgb("#4C7A44"), rgb("#FF5FA8")); return m
def time_daggers():
    m = Model(); v = rgb("#B68CF0")
    m.blade(11, 27, 3.2, 1.0, 1.4, v, dk(v, 0.4))
    m.guard(9.5, 6, rgb("#D4AF37"), rgb("#8E6D12"), style="bar"); m.orb(C, 8.7, C, 1.5, rgb("#C8A2FF")); m.grip(3.5, 9, rgb("#3A2256"), rgb("#8E65C6")); m.pommel(2.6, 1.3, rgb("#D4AF37"))
    # a second, smaller dagger crossed behind (the time twin)
    m.box(C - 0.5, 12, C + 1.2, C + 0.5, 22, C + 1.7, lt(v, 0.4), ("z", 22.5, (C, 12, C + 1.2))); return m
def umbral_knives():
    m = Model(); p = rgb("#6B4FC0")
    m.blade(10, 29, 4.2, 1.0, 1.5, rgb("#1D1630"), p, shift=lambda t: 2.6 * t * t * 1.0)
    m.guard(8, 6, rgb("#241C3A"), rgb("#7A58E0"), style="spike"); m.grip(3, 8, rgb("#18122A"), rgb("#5B3FB5")); m.pommel(2.2, 1.4, rgb("#3A2E5C"), rgb("#B66BFF")); return m
def void_axe():
    m = Model(); v = rgb("#7D3FC0")
    m.pole(0, 29, rgb("#33204A"), 0.9, rgb("#7A4AB5"))
    for i in range(9):
        t = i / 8; w = 2.2 + 4.8 * math.sin(t * math.pi); m.box(C + 0.9, 19 + i * 1.3, C - 0.9, C + 0.9 + w, 20.3 + i * 1.3, C + 0.9, mix(rgb("#4A1E7E"), rgb("#B87CF0"), 0.35 + 0.5 * math.sin(t * math.pi)))
    m.box(C - 5.5, 22, C - 0.7, C - 0.9, 27, C + 0.7, rgb("#4A1E7E")); m.orb(C + 4.2, 24.4, C, 1.2, rgb("#D9A8FF")); m.gem(C, 18, C + 1, 0.8, rgb("#B87CF0")); m.pommel(0.4, 1.0, rgb("#7A4AB5")); return m
def frost_brand():
    m = Model(); i = rgb("#A8DCFF")
    m.blade(9, 31, 5.4, 0.8, 2.2, i, rgb("#4E9AD6"), steps=18)
    for k in range(4): m.box(C - 0.6, 12 + k * 4.5, C + 1.0, C + 0.6, 14 + k * 4.5, C + 1.5, rgb("#FFFFFF"))
    m.guard(7.3, 8, rgb("#C9E4FA"), rgb("#6FB1E8"), style="wing"); m.grip(2.5, 7.3, rgb("#1F3F72"), rgb("#78B5E8")); m.pommel(1.6, 1.6, rgb("#D9EEFF"), rgb("#7FC7FF")); return m
def gale_blade():
    m = Model(); t = rgb("#5FD9C4")
    m.blade(9, 31, 4.6, 1.2, 1.8, t, rgb("#228C7E"))
    m.guard(7.3, 9, rgb("#D5F5EF"), rgb("#7ADCCB"), style="wing"); m.grip(2.5, 7.3, rgb("#1F5B57"), rgb("#4FC5B4")); m.pommel(1.6, 1.5, rgb("#D5F5EF"), rgb("#5FFFE0"))
    for s in (-1, 1): m.box(C + s * 4.6 - 0.4, 10.4, C - 0.4, C + s * 4.6 + 0.4, 13.6, C + 0.4, rgb("#FFFFFF")); return m
def earth_hammer():
    m = Model(); b = rgb("#9C6330")
    m.pole(0, 23, rgb("#6B3F1B"), 1.0, rgb("#B07A3C"))
    m.box(C - 5.5, 22, C - 3.4, C + 5.5, 30, C + 3.4, dk(b, 0.2)); m.box(C - 5, 22.6, C - 3.8, C + 5, 29.4, C + 3.8, b)
    for s in (-1, 1): m.box(C + s * 5.5 - (0 if s > 0 else 1.6), 22, C - 3.6, C + s * 5.5 + (1.6 if s > 0 else 0), 30, C + 3.6, rgb("#8A8F99"))
    m.gem(C, 26, C + 3.9, 1.3, rgb("#FFAA3C"), rgb("#FFE2A8")); m.gem(C, 26, C - 3.9, 1.3, rgb("#FFAA3C")); m.pommel(0.4, 1.2, rgb("#8A8F99")); return m
def life_staff():
    m = Model(); g = rgb("#52C25A")
    m.pole(0, 23, rgb("#5C8F3B"), 0.8, rgb("#A5D66E"))
    for s in (-1, 1):
        for k in range(5): m.box(C + s * (1.0 + k * 0.85) - 0.5, 23 + k * 1.2, C - 0.4, C + s * (1.0 + k * 0.85) + 0.5, 24.6 + k * 1.2, C + 0.4, g if k % 2 else lt(g, 0.2))
    m.orb(C, 27.2, C, 2.0, rgb("#7CFFA0")); m.guard(22, 4, rgb("#3E7A32"), rgb("#8BE07A"), style="curve"); return m
def solar_bow():
    m = Model(); g = rgb("#E6A935")
    for i in range(14):
        t = i / 13; y = 2 + t * 28; x = C - 4.5 * math.sin(t * math.pi) * 1.0
        m.box(x - 0.9, y, C - 0.7, x + 0.9, y + 2.4, C + 0.7, mix(rgb("#8B5A12"), g, math.sin(t * math.pi)))
    m.box(C + 0.6, 2, C - 0.1, C + 0.9, 30.4, C + 0.1, rgb("#F5EBC8"))
    m.orb(C - 3.8, 16, C, 1.3, rgb("#FFD15A")); m.gem(C - 3.5, 16, C + 1.0, 0.7, rgb("#FF7A1E")); return m
def abyss_crossbow():
    m = Model(); p = rgb("#7D3FC0")
    m.pole(1, 22, rgb("#241C3A"), 1.0, rgb("#7A58E0"))
    for s in (-1, 1):
        for k in range(5): m.box(C + s * (1.5 + k * 1.5) - 0.8, 21 + k * 0.9, C - 0.9, C + s * (1.5 + k * 1.5) + 0.8, 23.2 + k * 0.9, C + 0.9, p if k % 2 else lt(p, 0.15))
    m.box(C - 7.5, 25, C - 0.2, C + 7.5, 25.3, C + 0.2, rgb("#E9DDFF"))
    m.orb(C, 22.8, C, 1.4, rgb("#B66BFF")); m.box(C - 0.4, 22, C - 0.4, C + 0.4, 31, C + 0.4, rgb("#D9C4FF")); m.box(C - 0.9, 31, C - 0.9, C + 0.9, 32.4, C + 0.9, rgb("#8E65C6"), ("y", 45.0, (C, 31, C))); return m
def lunar_katana():
    m = Model(); s = rgb("#DCEBFF")
    m.blade(11, 31, 2.8, 0.9, 1.1, s, rgb("#7FA6D9"), shift=lambda t: 3.4 * t * t, steps=24, ridge=0.55)
    m.box(C - 2.6, 9.6, C - 2.6, C + 2.6, 11.0, C + 2.6, rgb("#E3C45A")); m.box(C - 1.9, 9.2, C - 1.9, C + 1.9, 9.8, C + 1.9, rgb("#8A6E1C"))
    m.grip(2.6, 9.4, rgb("#1D2140"), rgb("#6E86D9"), r=0.95); m.pommel(1.7, 1.5, rgb("#E3C45A"), rgb("#9FC3FF")); return m
def blaze_cleaver():
    m = Model(); o = rgb("#F3A12A")
    for i in range(14):
        t = i / 13; w = 4.0 + 2.2 * math.sin(t * 2.2); m.box(C - 1.4, 10 + i * 1.55, C - 1.1, C - 1.4 + w, 11.7 + i * 1.55, C + 1.1, mix(rgb("#B85A12"), o, 0.35 + 0.65 * t))
    m.box(C - 1.4, 10, C - 1.1, C - 0.2, 32, C + 1.1, rgb("#FFE08A"))
    m.guard(8.2, 5, rgb("#7B3B12"), rgb("#D98A2B"), style="bar"); m.grip(2.5, 8.2, rgb("#4A2410"), rgb("#D9741B")); m.pommel(1.6, 1.5, rgb("#E39A2E"), rgb("#FF5A1E"))
    m.orb(C + 2.2, 22, C, 1.0, rgb("#FFE08A")); return m
def venom_fang():
    m = Model(); g = rgb("#6FD43A")
    m.blade(10, 28, 4.0, 0.8, 1.5, g, rgb("#2E7D1C"), shift=lambda t: -2.4 * t * t)
    m.guard(8, 5, rgb("#33552A"), rgb("#8CE05A"), style="curve"); m.grip(3, 8, rgb("#3C2C18"), rgb("#6FB32F")); m.pommel(2.2, 1.3, rgb("#5C8F3B"), rgb("#C8FF6A"))
    m.box(C - 0.5, 12, C + 0.9, C + 0.5, 15, C + 1.3, rgb("#D9FF9A")); return m
def star_wand():
    m = Model(); y = rgb("#F5D76E")
    m.pole(0, 22, rgb("#E9E2F5"), 0.6, rgb("#B9A8DA"))
    m.box(C - 1.0, 21, C - 1.0, C + 1.0, 23, C + 1.0, rgb("#C9A63A"))
    for ang in range(0, 360, 72):
        a = math.radians(ang + 90); cx = C + math.cos(a) * 3.8; cy = 27.5 + math.sin(a) * 3.8
        m.box(cx - 0.8, cy - 0.8, C - 0.7, cx + 0.8, cy + 0.8, C + 0.7, y)
        m.box(C + math.cos(a) * 1.9 - 0.9, 27.5 + math.sin(a) * 1.9 - 0.9, C - 0.8, C + math.cos(a) * 1.9 + 0.9, 27.5 + math.sin(a) * 1.9 + 0.9, C + 0.8, lt(y, 0.2))
    m.orb(C, 27.5, C, 1.6, rgb("#FFF3B0")); return m
def reaper_scythe():
    m = Model(); p = rgb("#7B4FB8")
    m.pole(0, 27, rgb("#2B2336"), 0.9, rgb("#6A4A9E"))
    for i in range(11):
        t = i / 10; m.box(C + 0.6 + t * 8.5, 25.5 + math.sin(t * 2.5) * 4 - t * 5.5, C - 0.7, C + 2.8 + t * 8.5, 28.2 + math.sin(t * 2.5) * 4 - t * 6.5, C + 0.7, mix(rgb("#2A1B45"), rgb("#B792FF"), 0.25 + 0.6 * math.sin(t * math.pi)))
    m.box(C - 1.2, 25, C - 0.9, C + 1.4, 29, C + 0.9, rgb("#4A3470")); m.orb(C, 29.4, C, 1.1, rgb("#C9A0FF")); m.gem(C, 23.5, C + 0.9, 0.8, rgb("#B66BFF")); m.pommel(0.4, 1.0, rgb("#6A4A9E")); return m


WEAPONS = {f.__name__: f for f in (crimson_fang, inferno_scythe, soul_staff, warden_mace, storm_trident, thorn_blade, time_daggers, umbral_knives, void_axe,
                                     frost_brand, gale_blade, earth_hammer, life_staff, solar_bow, abyss_crossbow, lunar_katana, blaze_cleaver, venom_fang,
                                     star_wand, reaper_scythe)}
GLOW = {"crimson_fang": "#C0392B"}


# ---------------------------------------------------------------- how it sits in the hand, inventory and frames
# (vertical model: these numbers are tuned in game; change them here and regenerate)
DISPLAY = {
    "thirdperson_righthand": {"rotation": [0, -90, 10], "translation": [0, 3.5, 1.0], "scale": [0.8, 0.8, 0.8]},
    "thirdperson_lefthand": {"rotation": [0, 90, -10], "translation": [0, 3.5, 1.0], "scale": [0.8, 0.8, 0.8]},
    "firstperson_righthand": {"rotation": [0, -90, -20], "translation": [1.13, 3.2, 1.13], "scale": [0.55, 0.55, 0.55]},
    "firstperson_lefthand": {"rotation": [0, 90, 20], "translation": [1.13, 3.2, 1.13], "scale": [0.55, 0.55, 0.55]},
    "gui": {"rotation": [20, 205, -45], "translation": [0, -1.5, 0], "scale": [0.62, 0.62, 0.62]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.55, 0.55, 0.55]},
    "fixed": {"rotation": [0, 90, -45], "translation": [0, -1, 0], "scale": [0.6, 0.6, 0.6]},
    "head": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [0.8, 0.8, 0.8]},
}


# ---------------------------------------------------------------- preview (a tiny software renderer)
def render(model, yaw=35, pitch=22, size=256):
    pts, polys = [], []
    az, el = math.radians(yaw), math.radians(pitch)

    def tr(p):
        x, y, z = p[0] - 8, p[1] - 16, p[2] - 8
        x, z = x * math.cos(az) + z * math.sin(az), -x * math.sin(az) + z * math.cos(az)
        y, z = y * math.cos(el) - z * math.sin(el), y * math.sin(el) + z * math.cos(el)
        return np.array([x, y, z])

    for (a, b, ci, rot) in model.els:
        x0, y0, z0 = a; x1, y1, z1 = b
        cs = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        if rot:
            ax, ang, o = rot; t = math.radians(ang); c, s = math.cos(t), math.sin(t); out = []
            for (x, y, z) in cs:
                dx, dy, dz = x - o[0], y - o[1], z - o[2]
                if ax == "y": dx, dz = dx * c + dz * s, -dx * s + dz * c
                elif ax == "x": dy, dz = dy * c - dz * s, dy * s + dz * c
                else: dx, dy = dx * c - dy * s, dx * s + dy * c
                out.append((o[0] + dx, o[1] + dy, o[2] + dz))
            cs = out
        V = [tr(p) for p in cs]
        idx = {(i >> 2 & 1, i >> 1 & 1, i & 1): i for i in range(8)}
        faces = [((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0), (-1, 0, 0)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1), (1, 0, 0)),
                 ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1), (0, -1, 0)), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)),
                 ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, -1)), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1))]
        for f in faces:
            q = [V[idx[k]] for k in f[:4]]
            n = np.cross(q[1] - q[0], q[3] - q[0]); ln = np.linalg.norm(n)
            if ln < 1e-6: continue
            n = n / ln
            if n[2] > 0: n = -n                       # facing the camera (z towards the viewer is negative here)
            nz = -n[2]
            sh = 0.55 + 0.45 * (0.5 * nz + 0.5 * max(0, -n[1] * 0 + n[1] * -0.6 + 0.4)) + 0.15 * (n[0] * 0.4)
            polys.append((sum(p[2] for p in q) / 4, q, mix(model.colors[ci], (0, 0, 0), max(0, 1 - sh)) if sh < 1 else lt(model.colors[ci], min(0.3, sh - 1)), nz))
    img = Image.new("RGBA", (size, size), (46, 46, 54, 255)); d = ImageDraw.Draw(img)
    sc = size / 40.0
    for depth, q, col, nz in sorted(polys, key=lambda p: -p[0]):
        if nz <= 0: continue
        d.polygon([(size / 2 + p[0] * sc, size / 2 - p[1] * sc) for p in q], fill=col + (255,), outline=dk(col, 0.35) + (255,))
    return img


def build(out_zip, preview=None):
    z = zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED)
    z.writestr("pack.mcmeta", json.dumps({"pack": {"description": "ValqLegends: 3D legendary weapons", "min_format": 75, "max_format": 79}}))
    sheet = []
    for wid, fn in WEAPONS.items():
        m = fn()
        b = io.BytesIO(); m.palette_png().save(b, "PNG"); z.writestr(f"assets/valqlegends/textures/item/{wid}.png", b.getvalue())
        z.writestr(f"assets/valqlegends/models/item/{wid}.json", json.dumps(m.json(f"valqlegends:item/{wid}", DISPLAY)))
        z.writestr(f"assets/valqlegends/items/{wid}.json", json.dumps({"model": {"type": "minecraft:model", "model": f"valqlegends:item/{wid}"}}))
        sheet.append((wid, m))
    z.close()
    if preview:
        cell = 256; cols = 5; rows = math.ceil(len(sheet) / cols)
        img = Image.new("RGBA", (cols * cell, rows * cell), (46, 46, 54, 255))
        for i, (wid, m) in enumerate(sheet): img.alpha_composite(render(m), ((i % cols) * cell, (i // cols) * cell))
        img.save(preview)
    print("pack", out_zip, "sha1", hashlib.sha1(open(out_zip, "rb").read()).hexdigest(), "weapons", len(sheet), "elements", sum(len(m.els) for _, m in sheet))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
