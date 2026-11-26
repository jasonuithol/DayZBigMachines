#!/usr/bin/env python3
"""Draws the Big Machines' weathered surface textures: tiling squares (TILE metres across) of
worn paint (yellow; the combine's mint green and cream), dark steel, track steel and concrete,
each as a DayZ texture set:

    textures/bm_<name>_co.png     colour
    textures/bm_<name>_nohq.png   normal map (DirectX style: green = -Y, as DayZHandCart)
    textures/bm_<name>_smdi.png   specular (G) and glossiness (B), R = 1
    BigMachines/data/bm_<name>.rvmat

    python3 tools/make_weathering.py
    tools/img2paa.sh textures/bm_*_{co,nohq,smdi}.png BigMachines/data

The models map them by box projection in metres (rv.MeshBuilder.to_object): on walls the
texture's up is the world's up, so rust streaks and grime run downwards. Everything is made
from periodic noise (filtered in the frequency domain), so the squares tile without seams.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "textures")
DATA = os.path.join(ROOT, "BigMachines", "data")
GAME_DATA = "BigMachines\\data\\"

N = 1024            # pixels across a square
TILE = 2.0          # metres across a square (blender/rv.py WEATHER_TILE)
PX = N / TILE       # pixels per metre


def srgb(c):
    return np.array(c, dtype=np.float64) / 255.0


class Noise:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        f = np.fft.fftfreq(N)
        self.fy, self.fx = np.meshgrid(f, f, indexing="ij")

    def field(self, sx, sy=None):
        """Periodic Gaussian-filtered noise, blur sigma sx by sy pixels: mean 0, std 1"""
        sy = sx if sy is None else sy
        w = np.fft.fft2(self.rng.standard_normal((N, N)))
        g = np.exp(-2 * math.pi ** 2 * ((sx * self.fx) ** 2 + (sy * self.fy) ** 2))
        a = np.real(np.fft.ifft2(w * g))
        return (a - a.mean()) / (a.std() + 1e-12)

    def fbm(self, s, octaves=4, sy=None):
        sy = s if sy is None else sy
        total, amp, norm = 0.0, 1.0, 0.0
        for k in range(octaves):
            total = total + amp * self.field(s / 2 ** k, sy / 2 ** k)
            norm += amp
            amp *= 0.55
        return total / norm


def smooth(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = t[..., None]
    return a * (1 - t) + b * t


def drips(start, noise, length_m, wobble):
    """Streaks running down the texture from `start` (0..1), fading over about `length_m`,
    each column at its own pace; wraps round (the texture tiles)"""
    rows = int(length_m * PX)
    decay = np.exp(-1.0 / max(rows, 1)) - 0.012 * np.clip(noise.field(1.5, 40), 0, None) * wobble
    decay = np.clip(decay, 0.0, 0.9995)
    s = start.copy()
    for _ in range(2):          # twice round so streaks cross the bottom edge into the top
        for y in range(N):
            s[y] = np.maximum(s[y], s[y - 1] * decay[y])
    return s


def scratches(seed, count, length_m, width_px):
    """Thin bright lines, mostly horizontal (scraped by things going past)"""
    rng = np.random.default_rng(seed)
    img = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.uniform(0, N, 2)
        a = rng.normal(0, 0.35) + (math.pi if rng.random() < 0.5 else 0)
        ln = rng.uniform(0.3, 1.0) * length_m * PX
        x2, y2 = x + math.cos(a) * ln, y + math.sin(a) * ln
        v = int(rng.uniform(120, 255))
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d.line([(x + ox, y + oy), (x2 + ox, y2 + oy)], fill=v, width=width_px)
    return np.asarray(img, dtype=np.float64) / 255.0


def normal_map(h, strength):
    """Tangent-space normals from a height field (metres-ish units scaled by strength)"""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
    dy_up = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) / 2     # rows go down the image
    nx, ny, nz = -dx * strength, -dy_up * strength, np.ones_like(h)
    ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    ny = -ny                                             # DirectX style
    return np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], -1)


def painted_metal(seed, paint, chip_amount, rust_amount, grime_amount, primer=(70, 66, 60),
                  steel=(96, 94, 90), rust=(104, 54, 26), grime=(58, 50, 40), mud_amount=0.0,
                  paint_spec=0.35, paint_gloss=0.45):
    """Paint worn over steel: faded patches, grime and its downward streaks, chips through to
    primer and bare steel, rust spots with streaks running down, scrapes; optional mud"""
    n = Noise(seed)
    paint, primer, steel, rust, grime = map(srgb, (paint, primer, steel, rust, grime))

    # the paint: uneven tone, sun-faded patches
    col = np.broadcast_to(paint, (N, N, 3)).copy()
    tone = n.fbm(160, 3)
    col *= (1 + 0.05 * tone)[..., None]
    fade = smooth(n.fbm(220, 3), 0.2, 1.4)
    faded = paint * 0.82 + np.mean(paint) * 0.18 + 0.05
    col = mix(col, np.broadcast_to(faded, (N, N, 3)), fade * 0.45)
    spec = np.full((N, N), paint_spec)
    gloss = np.full((N, N), paint_gloss) - 0.12 * fade
    height = 0.008 * n.field(1.2)             # orange peel

    # grime: blotches and streaks running down
    blot = smooth(n.fbm(90, 4), 0.4, 2.2) * grime_amount * 0.6
    streak = smooth(n.fbm(7, 3, sy=110), 0.5, 2.2) * smooth(n.field(120), -0.4, 1.0) * grime_amount
    g = np.clip(blot * 0.7 + streak * 0.55, 0, 0.7)
    col = mix(col, np.broadcast_to(grime, (N, N, 3)), g)
    gloss -= 0.25 * g
    spec -= 0.2 * g

    # chips: small, in clusters, more of them in worn patches
    cluster = n.fbm(70, 3)
    fine = n.fbm(5, 3)
    chips = smooth(fine + 0.85 * cluster, 2.6 - chip_amount, 2.75 - chip_amount)
    edge = smooth(fine + 0.85 * cluster, 2.35 - chip_amount, 2.6 - chip_amount) - chips  # primer ring
    rusty = smooth(n.field(25) + rust_amount * 1.5, 0.0, 1.2)
    chip_col = mix(np.broadcast_to(steel, (N, N, 3)), np.broadcast_to(rust, (N, N, 3)), rusty)
    col = mix(col, np.broadcast_to(primer, (N, N, 3)), np.clip(edge, 0, 1) * 0.8)
    col = mix(col, chip_col, chips)
    height -= 0.6 * chips + 0.25 * np.clip(edge, 0, 1)
    spec = spec * (1 - chips) + chips * (0.5 * (1 - rusty) + 0.05 * rusty)
    gloss = gloss * (1 - chips) + chips * (0.55 * (1 - rusty) + 0.08 * rusty)

    # rust spots of their own (bubbling under the paint)
    spots = smooth(n.fbm(10, 3) + 0.7 * n.field(90), 2.9 - rust_amount, 3.1 - rust_amount)
    col = mix(col, np.broadcast_to(rust * 0.85, (N, N, 3)), spots)
    height += 0.25 * spots * n.field(1.5)
    spec -= 0.25 * spots
    gloss -= 0.35 * spots

    # rust streaks down from the rusty chips and spots
    run = drips(np.clip(chips * rusty + spots, 0, 1) * 0.75, n, 0.35 + 0.4 * rust_amount, 1.0)
    run = np.clip(run - np.clip(chips + spots, 0, 1), 0, 1) * smooth(n.field(2, 30), -0.6, 0.8)
    col = mix(col, np.broadcast_to(rust * 1.05, (N, N, 3)), run * 0.55 * min(1.0, 0.4 + rust_amount))
    gloss -= 0.2 * run

    # scrapes through to the metal
    scr = scratches(seed + 1, int(40 * chip_amount + 10), 0.25, 2)
    col = mix(col, np.broadcast_to(steel * 1.25, (N, N, 3)), scr * 0.65)
    spec = spec * (1 - scr) + scr * 0.6
    gloss = gloss * (1 - scr) + scr * 0.6
    height -= 0.2 * scr

    # mud: dried splashes, lighter at their edges
    if mud_amount > 0:
        m = n.fbm(14, 4) + 0.9 * n.fbm(140, 2)
        mud = smooth(m, 1.9 - mud_amount, 2.2 - mud_amount)
        mud_col = srgb((92, 80, 62)) * (1 + 0.1 * n.field(4))[..., None]
        col = mix(col, mud_col, mud * 0.9)
        height += 0.5 * mud * (1 + 0.5 * n.field(2))
        spec = spec * (1 - mud) + mud * 0.03
        gloss = gloss * (1 - mud) + mud * 0.05

    return np.clip(col, 0, 1), height, np.clip(spec, 0, 1), np.clip(gloss, 0, 1)


def concrete(seed):
    """Cast concrete: mottled grey, pits, water stains running down, a few hairline cracks"""
    n = Noise(seed)
    base = srgb((120, 118, 112))
    col = np.broadcast_to(base, (N, N, 3)).copy()
    col *= (1 + 0.08 * n.fbm(60, 4) + 0.04 * n.field(2))[..., None]
    height = 0.15 * n.fbm(6, 3)
    pits = smooth(-n.field(1.8), 2.2, 2.8)
    col *= (1 - 0.45 * pits)[..., None]
    height -= 0.6 * pits
    stain = smooth(n.fbm(4, 3, sy=160), 0.2, 1.6) * smooth(n.field(150), -0.3, 1.0)
    col = mix(col, np.broadcast_to(srgb((70, 66, 58)), (N, N, 3)), stain * 0.5)
    rust = drips(smooth(n.fbm(12, 2) + 0.6 * n.field(200), 2.7, 2.9), n, 0.5, 1.0)
    col = mix(col, np.broadcast_to(srgb((110, 70, 40)), (N, N, 3)), np.clip(rust, 0, 1) * 0.35)
    crack = np.zeros((N, N))
    rng = np.random.default_rng(seed + 7)
    img = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(img)
    for _ in range(3):
        x, y = rng.uniform(0, N, 2)
        a = rng.uniform(0, 2 * math.pi)
        pts = [(x, y)]
        for _ in range(30):
            a += rng.normal(0, 0.5)
            x, y = x + math.cos(a) * 9, y + math.sin(a) * 9
            pts.append((x, y))
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d.line([(px + ox, py + oy) for px, py in pts], fill=255, width=1)
    crack = np.asarray(img, dtype=np.float64) / 255.0
    col *= (1 - 0.25 * crack)[..., None]
    height -= 0.5 * crack
    spec = np.full((N, N), 0.04)
    gloss = np.full((N, N), 0.08) + 0.1 * stain
    return np.clip(col, 0, 1), height, spec, np.clip(gloss, 0, 1)


SETS = {
    # name: (generator, kwargs, normal strength, specular colour for the rvmat)
    "paint_yellow": (painted_metal, dict(seed=11, paint=(204, 140, 20), chip_amount=0.55, rust_amount=0.45,
                                         grime_amount=0.75), 3.0),
    "steel_dark": (painted_metal, dict(seed=23, paint=(42, 42, 41), chip_amount=0.7, rust_amount=0.7,
                                       grime_amount=0.5, primer=(55, 52, 48), steel=(110, 108, 104),
                                       grime=(30, 26, 22), paint_spec=0.3, paint_gloss=0.4), 3.0),
    "track_steel": (painted_metal, dict(seed=37, paint=(34, 30, 27), chip_amount=1.0, rust_amount=1.0,
                                        grime_amount=0.9, primer=(60, 42, 30), steel=(120, 116, 110),
                                        rust=(92, 50, 28), grime=(40, 34, 28), mud_amount=0.6,
                                        paint_spec=0.25, paint_gloss=0.3), 8.0),
    "concrete": (concrete, dict(seed=41), 5.0),
    # the combine harvester: the map wreck's faded mint green and the cream of its grain tank
    "paint_mint": (painted_metal, dict(seed=53, paint=(112, 160, 122), chip_amount=0.6, rust_amount=0.55,
                                       grime_amount=0.7), 3.0),
    "paint_cream": (painted_metal, dict(seed=59, paint=(214, 207, 186), chip_amount=0.5, rust_amount=0.5,
                                        grime_amount=0.8), 3.0),
}

RVMAT = """ambient[]={{1,1,1,1}};
diffuse[]={{1,1,1,1}};
forcedDiffuse[]={{0,0,0,0}};
emmisive[]={{0,0,0,0}};
specular[]={{{spec},{spec},{spec},1}};
specularPower={power};
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1
{{
	texture="{data}bm_{name}_nohq.paa"; uvSource="tex"; class uvTransform {{aside[]={{1,0,0}}; up[]={{0,1,0}}; dir[]={{0,0,0}}; pos[]={{0,0,0}};}};
}};
class Stage2
{{
	texture="#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)"; uvSource="tex"; class uvTransform {{aside[]={{1,0,0}}; up[]={{0,1,0}}; dir[]={{0,0,0}}; pos[]={{0,0,0}};}};
}};
class Stage3
{{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)"; uvSource="tex"; class uvTransform {{aside[]={{1,0,0}}; up[]={{0,1,0}}; dir[]={{0,0,0}}; pos[]={{0,0,0}};}};
}};
class Stage4
{{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)"; uvSource="tex"; class uvTransform {{aside[]={{1,0,0}}; up[]={{0,1,0}}; dir[]={{0,0,0}}; pos[]={{0,0,0}};}};
}};
class Stage5
{{
	texture="{data}bm_{name}_smdi.paa"; uvSource="tex"; class uvTransform {{aside[]={{1,0,0}}; up[]={{0,1,0}}; dir[]={{0,0,0}}; pos[]={{0,0,0}};}};
}};
class Stage6
{{
	texture="#(ai,64,64,1)fresnel(1.3,0.7)"; uvSource="none";
}};
class Stage7
{{
	texture="dz\\data\\data\\env_land_co.paa"; useWorldEnvMap="true"; uvSource="none";
}};
"""


def save(a, name):
    img = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    img.save(os.path.join(TEX, name))
    print("drew", name)


def main():
    os.makedirs(TEX, exist_ok=True)
    for name, (gen, kw, strength) in SETS.items():
        col, height, spec, gloss = gen(**kw)
        save(col, f"bm_{name}_co.png")
        save(normal_map(height, strength), f"bm_{name}_nohq.png")
        save(np.stack([np.ones_like(spec), spec, gloss], -1), f"bm_{name}_smdi.png")
        power = 40 if name != "concrete" else 10
        rv_spec = 0.5 if name != "concrete" else 0.15
        with open(os.path.join(DATA, f"bm_{name}.rvmat"), "w", newline="\r\n") as f:
            f.write(RVMAT.format(spec=rv_spec, power=power, data=GAME_DATA, name=name))


main()
