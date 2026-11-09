#!/usr/bin/env python3
"""ValqLegends resource pack: a hand-painted 64x64 icon for every weapon, bound with the `item_model` component.

usage: python gen_pack.py <out.zip> [preview.png]
Each icon is painted pointing up on a big canvas (a blade, a staff...), rotated 45 degrees, outlined, lit with a soft glow
and scaled down. Needs Pillow and numpy.
"""
import hashlib, io, json, math, os, sys, zipfile
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 512          # painting canvas
OUT = 64         # icon size in the pack
CX = S // 2


def rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def mix(a, b, t): return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
def lighter(c, t=0.35): return mix(c, (255, 255, 255), t)
def darker(c, t=0.45): return mix(c, (0, 0, 0), t)


def layer(): return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def hgrad_fill(img, pts, c_edge, c_mid, c_hi=None):
    """polygon filled with a horizontal gradient: edge colour at the sides, mid colour in the centre, thin highlight."""
    xs = [p[0] for p in pts]; x0, x1 = min(xs), max(xs)
    mask = Image.new("L", (S, S), 0); ImageDraw.Draw(mask).polygon(pts, fill=255)
    cols = np.arange(S, dtype=np.float32)
    mid = (x0 + x1) / 2; half = max(1, (x1 - x0) / 2)
    t = 1 - np.clip(np.abs(cols - mid) / half, 0, 1)                  # 1 in the centre
    a = np.zeros((S, S, 3), np.float32)
    for i in range(3):
        a[:, :, i] = c_edge[i] * (1 - t) + c_mid[i] * t
    if c_hi is not None:
        hl = np.exp(-((cols - (mid - half * 0.25)) / (half * 0.12 + 1)) ** 2)
        for i in range(3):
            a[:, :, i] = a[:, :, i] * (1 - 0.7 * hl) + c_hi[i] * 0.7 * hl
    g = Image.fromarray(a.astype(np.uint8), "RGB").convert("RGBA")
    g.putalpha(mask)
    img.alpha_composite(g)


def vgrad_fill(img, pts, top, bot):
    mask = Image.new("L", (S, S), 0); ImageDraw.Draw(mask).polygon(pts, fill=255)
    ys = [p[1] for p in pts]; y0, y1 = min(ys), max(ys)
    rows = np.clip((np.arange(S, dtype=np.float32) - y0) / max(1, y1 - y0), 0, 1)
    a = np.zeros((S, S, 3), np.float32)
    for i in range(3):
        a[:, :, i] = (top[i] * (1 - rows) + bot[i] * rows)[:, None]
    g = Image.fromarray(a.astype(np.uint8), "RGB").convert("RGBA"); g.putalpha(mask); img.alpha_composite(g)


def orb(img, cx, cy, r, col):
    for k in range(6, 0, -1):
        rr = int(r * (1 + k * 0.28)); a = int(26 * (7 - k))
        ImageDraw.Draw(img, "RGBA").ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col + (a // 2,))
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=darker(col, 0.35) + (255,))
    d.ellipse((cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8), fill=col + (255,))
    d.ellipse((cx - r * 0.5, cy - r * 0.55, cx + r * 0.1, cy + r * 0.0), fill=lighter(col, 0.7) + (230,))
    d.ellipse((cx - r * 0.3, cy - r * 0.42, cx - r * 0.1, cy - r * 0.22), fill=(255, 255, 255, 255))


def gem(img, cx, cy, r, col):
    d = ImageDraw.Draw(img, "RGBA")
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    d.polygon(pts, fill=darker(col, 0.4) + (255,))
    d.polygon([(cx, cy - r * 0.8), (cx + r * 0.8, cy), (cx, cy + r * 0.8), (cx - r * 0.8, cy)], fill=col + (255,))
    d.polygon([(cx, cy - r * 0.8), (cx - r * 0.8, cy), (cx - r * 0.1, cy - r * 0.1)], fill=lighter(col, 0.6) + (255,))


def grip(img, y0, y1, w, base, wrap):
    hgrad_fill(img, [(CX - w, y0), (CX + w, y0), (CX + w, y1), (CX - w, y1)], darker(base, 0.5), base, lighter(base, 0.3))
    d = ImageDraw.Draw(img, "RGBA")
    n = max(3, (y1 - y0) // 26)
    for i in range(n):
        y = y0 + 8 + i * (y1 - y0 - 12) / n
        d.line((CX - w, y + 8, CX + w, y - 8), fill=wrap + (255,), width=9)


def guard(img, y, half, col, thick=26, style="bar"):
    c_mid, c_edge = col, darker(col, 0.5)
    if style == "bar":
        pts = [(CX - half, y - thick // 3), (CX + half, y - thick // 3), (CX + half + 10, y + thick), (CX - half - 10, y + thick)]
    elif style == "wing":
        pts = [(CX - half - 40, y - 46), (CX - 20, y - thick // 2), (CX + 20, y - thick // 2), (CX + half + 40, y - 46),
               (CX + half, y + thick), (CX, y + thick * 0.4), (CX - half, y + thick)]
    elif style == "curve":
        pts = [(CX - half, y + 30), (CX - half + 16, y - 6), (CX, y + 6), (CX + half - 16, y - 6), (CX + half, y + 30), (CX, y + 26)]
    else:  # cross with spikes
        pts = [(CX - half - 14, y - 22), (CX - half + 20, y + 4), (CX + half - 20, y + 4), (CX + half + 14, y - 22),
               (CX + half, y + thick + 6), (CX - half, y + thick + 6)]
    hgrad_fill(img, pts, c_edge, c_mid, lighter(col, 0.5))


def pommel(img, y, r, col, gem_col=None):
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((CX - r, y - r, CX + r, y + r), fill=darker(col, 0.5) + (255,))
    d.ellipse((CX - r + 5, y - r + 5, CX + r - 5, y + r - 5), fill=col + (255,))
    d.ellipse((CX - r * 0.6, y - r * 0.7, CX - r * 0.1, y - r * 0.2), fill=lighter(col, 0.6) + (255,))
    if gem_col: gem(img, CX, y, int(r * 0.55), gem_col)


def blade(img, y_tip, y_base, w, c_edge, c_mid, c_hi, style="straight", fuller=True, curve=0):
    sh = int((y_base - y_tip) * 0.13)
    if style == "straight":
        pts = [(CX, y_tip), (CX + w, y_tip + sh + 20), (CX + w, y_base), (CX - w, y_base), (CX - w, y_tip + sh + 20)]
    elif style == "broad":
        pts = [(CX, y_tip), (CX + w, y_tip + sh), (CX + w * 1.15, y_base), (CX - w * 1.15, y_base), (CX - w, y_tip + sh)]
    elif style == "wavy":
        pts = [(CX, y_tip)]
        n = 9
        for i in range(1, n + 1):
            y = y_tip + (y_base - y_tip) * i / n
            pts.append((CX + w + (10 if i % 2 else -8), y))
        for i in range(n, 0, -1):
            y = y_tip + (y_base - y_tip) * i / n
            pts.append((CX - w - (10 if i % 2 else -8), y))
    elif style == "curved":      # katana-like: the tip bends to the right
        pts = []; n = 14
        for i in range(n + 1):
            t = i / n; y = y_tip + (y_base - y_tip) * t
            pts.append((CX + w + curve * (1 - t) ** 2 * 1.0, y))
        for i in range(n, -1, -1):
            t = i / n; y = y_tip + (y_base - y_tip) * t
            pts.append((CX - w + curve * (1 - t) ** 2 * 1.0 + (6 if t < 0.12 else 0), y))
        pts[0] = (CX + curve, y_tip - 8)
    elif style == "fang":        # a curved horn
        pts = []; n = 14
        for i in range(n + 1):
            t = i / n; y = y_tip + (y_base - y_tip) * t
            pts.append((CX + w * (0.2 + 0.8 * t) - curve * (1 - t) ** 1.5, y))
        for i in range(n, -1, -1):
            t = i / n; y = y_tip + (y_base - y_tip) * t
            pts.append((CX - w * (0.2 + 0.8 * t) - curve * (1 - t) ** 1.5, y))
    else:                        # crystal
        pts = [(CX, y_tip), (CX + w * 0.8, y_tip + sh * 1.4), (CX + w, y_tip + (y_base - y_tip) * 0.55), (CX + w * 0.7, y_base),
               (CX - w * 0.7, y_base), (CX - w, y_tip + (y_base - y_tip) * 0.55), (CX - w * 0.8, y_tip + sh * 1.4)]
    hgrad_fill(img, pts, c_edge, c_mid, c_hi)
    if fuller and style in ("straight", "broad", "crystal"):
        ImageDraw.Draw(img, "RGBA").line((CX, y_tip + sh + 30, CX, y_base - 20), fill=darker(c_mid, 0.4) + (200,), width=max(6, int(w * 0.18)))


def pole(img, y0, y1, w, col):
    hgrad_fill(img, [(CX - w, y0), (CX + w, y0), (CX + w, y1), (CX - w, y1)], darker(col, 0.5), col, lighter(col, 0.35))


# ------------------------------------------------------------------ the weapons
def p_crimson_fang(c):
    im = layer(); blade(im, 40, 330, 34, (90, 12, 24), (210, 40, 52), (255, 170, 170), "fang", False, curve=34)
    guard(im, 330, 62, (60, 60, 70), style="spike"); grip(im, 372, 450, 15, (60, 20, 24), (130, 30, 40)); pommel(im, 468, 26, (80, 80, 90), (230, 40, 60)); return im
def p_inferno_scythe(c):
    im = layer(); pole(im, 150, 490, 13, (80, 40, 24))
    pts = [(CX, 70), (CX + 150, 64), (CX + 250, 130), (CX + 210, 120), (CX + 120, 108), (CX + 30, 150), (CX, 160)]
    hgrad_fill(im, pts, (160, 40, 8), (255, 150, 30), (255, 240, 170)); orb(im, CX + 30, 120, 22, (255, 120, 30)); gem(im, CX, 175, 20, (255, 90, 20)); return im
def p_soul_staff(c):
    im = layer(); pole(im, 150, 490, 14, (150, 90, 30))
    for dx in (-52, 52): pole_x = CX + dx; ImageDraw.Draw(im, "RGBA").polygon([(pole_x - 7, 170), (pole_x + 7, 170), (CX + dx * 0.2 + 5, 90), (CX + dx * 0.2 - 5, 90)], fill=(70, 70, 90, 255))
    orb(im, CX, 118, 46, (90, 190, 255)); guard(im, 170, 56, (80, 80, 100), style="curve"); return im
def p_warden_mace(c):
    im = layer(); pole(im, 220, 490, 15, (30, 60, 66)); grip(im, 380, 470, 16, (20, 50, 56), (40, 120, 120))
    ImageDraw.Draw(im, "RGBA").ellipse((CX - 95, 70, CX + 95, 250), fill=(20, 60, 66, 255))
    hgrad_fill(im, [(CX - 88, 100), (CX + 88, 100), (CX + 100, 210), (CX - 100, 210)], (14, 70, 74), (40, 170, 160), (170, 255, 240))
    for dx in (-100, -60, 0, 60, 100): ImageDraw.Draw(im, "RGBA").polygon([(CX + dx - 14, 100), (CX + dx + 14, 100), (CX + dx, 50)], fill=(20, 120, 120, 255))
    gem(im, CX, 150, 26, (110, 255, 235)); return im
def p_storm_trident(c):
    im = layer(); pole(im, 150, 490, 11, (180, 140, 40))
    for dx, top in ((-66, 70), (0, 30), (66, 70)):
        ImageDraw.Draw(im, "RGBA").polygon([(CX + dx - 12, 180), (CX + dx + 12, 180), (CX + dx + 8, top + 36), (CX + dx, top), (CX + dx - 8, top + 36)], fill=(240, 210, 90, 255))
    hgrad_fill(im, [(CX - 78, 150), (CX + 78, 150), (CX + 60, 190), (CX - 60, 190)], (140, 100, 20), (240, 200, 60), (255, 250, 190))
    orb(im, CX, 128, 20, (120, 200, 255)); return im
def p_thorn_blade(c):
    im = layer(); blade(im, 36, 340, 32, (20, 70, 30), (60, 190, 90), (190, 255, 190), "wavy", False)
    guard(im, 340, 58, (50, 100, 50), style="curve"); grip(im, 380, 450, 14, (60, 40, 20), (40, 120, 50)); pommel(im, 466, 24, (70, 120, 60), (230, 70, 140)); return im
def p_time_daggers(c):
    im = layer(); blade(im, 90, 330, 28, (70, 40, 120), (180, 140, 240), (240, 230, 255), "straight")
    guard(im, 330, 54, (210, 170, 70), style="bar"); orb(im, CX, 345, 20, (190, 140, 255)); grip(im, 375, 450, 13, (50, 30, 70), (120, 80, 170)); pommel(im, 466, 22, (210, 170, 70)); return im
def p_umbral_knives(c):
    im = layer(); blade(im, 50, 320, 26, (20, 14, 40), (70, 50, 120), (190, 150, 255), "fang", False, curve=-26)
    guard(im, 322, 48, (30, 24, 50), style="spike"); grip(im, 362, 450, 13, (24, 18, 36), (80, 50, 140)); pommel(im, 466, 22, (50, 36, 80), (190, 90, 255)); return im
def p_void_axe(c):
    im = layer(); pole(im, 70, 490, 14, (50, 30, 70))
    pts = [(CX + 10, 80), (CX + 150, 60), (CX + 190, 150), (CX + 150, 250), (CX + 10, 220)]
    hgrad_fill(im, pts, (50, 20, 90), (150, 70, 210), (230, 190, 255)); orb(im, CX + 110, 150, 26, (200, 120, 255)); gem(im, CX, 250, 18, (150, 60, 220)); return im
def p_frost_brand(c):
    im = layer(); blade(im, 30, 330, 38, (60, 140, 210), (170, 225, 255), (255, 255, 255), "crystal")
    guard(im, 332, 62, (180, 210, 240), style="wing"); grip(im, 376, 450, 14, (30, 60, 110), (100, 160, 220)); pommel(im, 466, 24, (200, 230, 255), (120, 200, 255)); return im
def p_gale_blade(c):
    im = layer(); blade(im, 40, 330, 30, (30, 130, 120), (120, 230, 215), (230, 255, 250), "straight")
    guard(im, 332, 66, (200, 240, 235), style="wing"); grip(im, 378, 450, 13, (30, 80, 80), (80, 190, 180)); pommel(im, 466, 22, (180, 240, 230), (90, 230, 200)); return im
def p_earth_hammer(c):
    im = layer(); pole(im, 220, 490, 15, (110, 66, 30)); grip(im, 380, 470, 16, (80, 46, 20), (160, 110, 60))
    hgrad_fill(im, [(CX - 120, 80), (CX + 120, 80), (CX + 120, 230), (CX - 120, 230)], (70, 46, 30), (170, 110, 60), (230, 190, 140))
    d = ImageDraw.Draw(im, "RGBA"); d.rectangle((CX - 140, 100, CX - 120, 210), fill=(90, 90, 100, 255)); d.rectangle((CX + 120, 100, CX + 140, 210), fill=(90, 90, 100, 255))
    gem(im, CX, 155, 26, (255, 170, 60)); return im
def p_life_staff(c):
    im = layer(); pole(im, 140, 490, 13, (90, 140, 60))
    for dx, rot in ((-60, -1), (60, 1)):
        ImageDraw.Draw(im, "RGBA").polygon([(CX, 160), (CX + dx * 1.4, 90 - 10), (CX + dx * 0.9, 150), (CX + dx * 0.3, 190)], fill=(70, 170, 70, 255))
    orb(im, CX, 110, 44, (110, 255, 150)); guard(im, 170, 40, (60, 120, 50), style="curve"); return im
def p_solar_bow(c):
    im = layer(); d = ImageDraw.Draw(im, "RGBA")
    for k in range(34):
        t = k / 33; ang = math.radians(-70 + 140 * t); x = CX - 90 + math.cos(ang) * 150; y = 260 + math.sin(ang) * 215
        d.ellipse((x - 17, y - 17, x + 17, y + 17), fill=mix((140, 90, 20), (255, 215, 80), 1 - abs(t - 0.5) * 2) + (255,))
    d.line((CX - 90 + math.cos(math.radians(-70)) * 150, 260 + math.sin(math.radians(-70)) * 215, CX - 90 + math.cos(math.radians(70)) * 150, 260 + math.sin(math.radians(70)) * 215), fill=(250, 240, 200, 255), width=7)
    orb(im, CX + 40, 260, 28, (255, 200, 60)); gem(im, CX + 60, 260, 16, (255, 120, 30)); return im
def p_abyss_crossbow(c):
    im = layer(); d = ImageDraw.Draw(im, "RGBA")
    pole(im, 110, 470, 17, (30, 24, 50))
    d.polygon([(CX - 190, 210), (CX - 150, 170), (CX, 230), (CX + 150, 170), (CX + 190, 210), (CX + 140, 240), (CX, 260), (CX - 140, 240)], fill=(60, 40, 110, 255))
    d.line((CX - 188, 212, CX, 150, CX + 188, 212), fill=(230, 220, 255, 255), width=6)
    orb(im, CX, 210, 24, (170, 90, 255)); d.polygon([(CX - 8, 60), (CX + 8, 60), (CX, 20)], fill=(200, 160, 255, 255)); return im
def p_lunar_katana(c):
    im = layer(); blade(im, 36, 360, 22, (70, 100, 150), (200, 225, 255), (255, 255, 255), "curved", False, curve=40)
    d = ImageDraw.Draw(im, "RGBA"); d.ellipse((CX - 36, 340, CX + 36, 376), fill=(230, 200, 90, 255)); d.ellipse((CX - 26, 346, CX + 26, 370), fill=(60, 50, 40, 255))
    grip(im, 372, 460, 14, (30, 30, 50), (90, 110, 200)); pommel(im, 474, 20, (230, 200, 90), (150, 190, 255)); return im
def p_blaze_cleaver(c):
    im = layer(); pts = [(CX - 10, 40), (CX + 70, 70), (CX + 90, 190), (CX + 60, 330), (CX - 40, 340), (CX - 30, 120)]
    hgrad_fill(im, pts, (160, 70, 10), (255, 170, 40), (255, 245, 170)); guard(im, 345, 52, (120, 60, 20), style="bar")
    grip(im, 380, 456, 14, (70, 30, 14), (200, 90, 20)); pommel(im, 470, 22, (230, 150, 40), (255, 80, 20)); orb(im, CX + 40, 160, 20, (255, 210, 80)); return im
def p_venom_fang(c):
    im = layer(); blade(im, 80, 320, 24, (30, 80, 20), (120, 220, 60), (230, 255, 170), "fang", False, curve=24)
    guard(im, 322, 44, (50, 80, 30), style="curve"); grip(im, 360, 440, 12, (50, 40, 20), (110, 170, 40)); pommel(im, 456, 20, (90, 140, 50), (190, 255, 80)); return im
def p_star_wand(c):
    im = layer(); pole(im, 180, 490, 11, (230, 220, 245))
    d = ImageDraw.Draw(im, "RGBA"); pts = []
    for i in range(10):
        r = 100 if i % 2 == 0 else 42; a = math.radians(-90 + i * 36); pts.append((CX + math.cos(a) * r, 110 + math.sin(a) * r))
    hgrad_fill(im, pts, (200, 140, 30), (255, 225, 100), (255, 255, 230)); orb(im, CX, 110, 24, (255, 240, 170)); return im
def p_reaper_scythe(c):
    im = layer(); pole(im, 130, 490, 13, (40, 34, 50))
    pts = [(CX, 60), (CX + 160, 50), (CX + 262, 140), (CX + 190, 124), (CX + 100, 112), (CX + 24, 160), (CX, 170)]
    hgrad_fill(im, pts, (20, 14, 34), (90, 60, 140), (200, 170, 255)); gem(im, CX, 175, 20, (170, 90, 255)); orb(im, CX + 30, 105, 14, (190, 130, 255)); return im


ICONS = {
    "crimson_fang": (p_crimson_fang, "#E74C3C"), "inferno_scythe": (p_inferno_scythe, "#FF8C1E"), "soul_staff": (p_soul_staff, "#5DADE2"),
    "warden_mace": (p_warden_mace, "#1ABC9C"), "storm_trident": (p_storm_trident, "#F1C40F"), "thorn_blade": (p_thorn_blade, "#27AE60"),
    "time_daggers": (p_time_daggers, "#9B59B6"), "umbral_knives": (p_umbral_knives, "#8E44AD"), "void_axe": (p_void_axe, "#A569BD"),
    "frost_brand": (p_frost_brand, "#85C1E9"), "gale_blade": (p_gale_blade, "#76D7C4"), "earth_hammer": (p_earth_hammer, "#CA6F1E"),
    "life_staff": (p_life_staff, "#2ECC71"), "solar_bow": (p_solar_bow, "#F5B041"), "abyss_crossbow": (p_abyss_crossbow, "#7D3C98"),
    "lunar_katana": (p_lunar_katana, "#AED6F1"), "blaze_cleaver": (p_blaze_cleaver, "#F39C12"), "venom_fang": (p_venom_fang, "#82E0AA"),
    "star_wand": (p_star_wand, "#F9E79F"), "reaper_scythe": (p_reaper_scythe, "#BB8FCE"),
}


def finish(im, glow_col):
    """rotate so the tip points up-right, add outline + glow, crop to the centre, scale down."""
    im = im.rotate(-45, resample=Image.BICUBIC, expand=False, center=(S // 2, S // 2))
    alpha = im.split()[3]
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    glow = Image.new("RGBA", (S, S), glow_col + (0,)); glow.putalpha(alpha.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.55)))
    out.alpha_composite(glow)
    edge = alpha.filter(ImageFilter.MaxFilter(9)); edge = ImageChops.subtract(edge, alpha)
    outline = Image.new("RGBA", (S, S), (14, 8, 18, 0)); outline.putalpha(edge.point(lambda v: min(255, v * 2)))
    out.alpha_composite(outline); out.alpha_composite(im)
    bbox = out.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    pad = 14
    box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(S, bbox[2] + pad), min(S, bbox[3] + pad))
    c = out.crop(box); side = max(c.size); sq = Image.new("RGBA", (side, side), (0, 0, 0, 0)); sq.paste(c, ((side - c.width) // 2, (side - c.height) // 2))
    return sq.resize((OUT, OUT), Image.LANCZOS)


def build(out_zip, preview=None):
    icons = {}
    for wid, (fn, glow) in ICONS.items():
        icons[wid] = finish(fn(None), rgb(glow))
    z = zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED)
    z.writestr("pack.mcmeta", json.dumps({"pack": {"description": "ValqLegends: legendary weapon icons", "min_format": 75, "max_format": 79}}))
    for wid, im in icons.items():
        b = io.BytesIO(); im.save(b, "PNG", optimize=True)
        z.writestr(f"assets/valqlegends/textures/item/{wid}.png", b.getvalue())
        z.writestr(f"assets/valqlegends/models/item/{wid}.json", json.dumps({"parent": "minecraft:item/handheld", "textures": {"layer0": f"valqlegends:item/{wid}"}}))
        z.writestr(f"assets/valqlegends/items/{wid}.json", json.dumps({"model": {"type": "minecraft:model", "model": f"valqlegends:item/{wid}"}}))
    z.close()
    if preview:
        cols = 5; rows = math.ceil(len(icons) / cols); cell = 192
        sheet = Image.new("RGBA", (cols * cell, rows * cell), (54, 54, 62, 255))
        for i, (wid, im) in enumerate(icons.items()):
            big = im.resize((cell - 16, cell - 16), Image.NEAREST); sheet.alpha_composite(big, ((i % cols) * cell + 8, (i // cols) * cell + 8))
        sheet.save(preview)
    sha = hashlib.sha1(open(out_zip, "rb").read()).hexdigest()
    print("pack", out_zip, "sha1", sha, "icons", len(icons))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
