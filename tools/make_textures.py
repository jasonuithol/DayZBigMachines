#!/usr/bin/env python3
"""Draws the Big Machines livery decals: DayZ's own fictional construction brand FAT (the
vanilla wrecked diggers and bulldozers carry it) in a clean, working-machine version.

    python3 tools/make_textures.py          -> textures/*.png
    tools/img2paa.sh textures/*.png BigMachines/data

Every decal is a _ca texture (colour + alpha) shown on a thin quad over the paint
(rv.MeshBuilder.decal). The letters are drawn as shapes, not from a font: blocky F and T,
and the A as a triangle, as on the vanilla logo plate.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "textures")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BLACK = (22, 20, 18, 255)
WHITE = (236, 232, 220, 255)
RED = (170, 28, 22, 255)
YELLOW = (204, 140, 20, 255)    # matches paint_yellow in the Blender scripts (0.80, 0.55, 0.08)
CLEAR = (0, 0, 0, 0)


def fat_letters(d, x, y, h, colour, inner=None):
    """F, triangle-A and T, `h` tall from (x, y) top-left; returns the width used"""
    s = h / 10.0        # stroke unit
    w = 6.4 * s         # letter width
    gap = 1.4 * s
    # F
    d.rectangle([x, y, x + 2.2 * s, y + h], fill=colour)
    d.rectangle([x, y, x + w, y + 2.0 * s], fill=colour)
    d.rectangle([x, y + 4.2 * s, x + w * 0.82, y + 6.0 * s], fill=colour)
    x += w + gap
    # A: a triangle, with a smaller one inside in the paint colour (as on the vanilla plate)
    aw = w * 1.35
    d.polygon([(x, y + h), (x + aw / 2, y), (x + aw, y + h)], fill=colour)
    if inner is not None:
        d.polygon([(x + aw * 0.30, y + h - 1.4 * s), (x + aw / 2, y + h * 0.42), (x + aw * 0.70, y + h - 1.4 * s)],
                  fill=inner)
    x += aw + gap
    # T
    d.rectangle([x, y, x + w, y + 2.0 * s], fill=colour)
    d.rectangle([x + w / 2 - 1.1 * s, y, x + w / 2 + 1.1 * s, y + h], fill=colour)
    x += w
    return x


def letters_width(h):
    s = h / 10.0
    w = 6.4 * s
    return w + 1.4 * s + w * 1.35 + 1.4 * s + w


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print("drew", name, img.size)


def logo_plate():
    """The badge: black plate, white FAT, yellow inside the A, red pinstripe"""
    img = Image.new("RGBA", (512, 256), CLEAR)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 507, 251], radius=28, fill=BLACK)
    h = 150
    x0 = (512 - letters_width(h)) / 2
    fat_letters(d, x0, 34, h, WHITE, inner=YELLOW)
    d.rectangle([40, 206, 472, 216], fill=RED)
    return img


def stripe():
    """A long black band with a red pinstripe along its bottom edge, FAT in white at the
    left: down the boom, along a hood"""
    img = Image.new("RGBA", (1024, 128), BLACK)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 104, 1023, 112], fill=RED)
    fat_letters(d, 40, 18, 76, WHITE, inner=BLACK)
    return img


def letters():
    """FAT in black straight on the paint: the counterweight, a blade"""
    img = Image.new("RGBA", (512, 256), CLEAR)
    d = ImageDraw.Draw(img)
    h = 180
    fat_letters(d, (512 - letters_width(h)) / 2, 38, h, BLACK, inner=None)
    return img


def hazard():
    """Black and yellow diagonal stripes"""
    img = Image.new("RGBA", (256, 256), YELLOW)
    d = ImageDraw.Draw(img)
    for k in range(-4, 6):
        o = k * 64
        d.polygon([(o, 256), (o + 32, 256), (o + 32 + 256, 0), (o + 256, 0)], fill=BLACK)
    return img


def badge(text):
    """Model number in black on the paint"""
    img = Image.new("RGBA", (256, 64), CLEAR)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 46)
    box = d.textbbox((0, 0), text, font=font)
    d.text(((256 - (box[2] - box[0])) / 2 - box[0], (64 - (box[3] - box[1])) / 2 - box[1]), text, font=font,
           fill=BLACK)
    return img


def main():
    save(logo_plate(), "bm_fat_logo_ca.png")
    save(stripe(), "bm_fat_stripe_ca.png")
    save(letters(), "bm_fat_letters_ca.png")
    save(hazard(), "bm_hazard_ca.png")
    save(badge("FAT 218"), "bm_badge_exc_ca.png")
    save(badge("FAT D14"), "bm_badge_dozer_ca.png")


main()
