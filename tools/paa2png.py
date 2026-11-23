#!/usr/bin/env python3
"""Convert a DayZ/Arma .paa texture to PNG (the largest mipmap), for reference only.

    tools/paa2png.py in.paa out.png

Handles DXT1 / DXT5 (LZO-compressed or not) and ARGB8888. Pure Python + Pillow.
"""
import struct
import sys

from PIL import Image

TYPES = {0xFF01: ("bcn", 1), 0xFF05: ("bcn", 3), 0x8888: ("raw", None)}


def lzo1x_decompress(src, out_len):
    """LZO1X, per the Linux kernel's Documentation/staging/lzo.rst"""
    dst = bytearray()
    ip = 0

    def run_length(t, mask_bits, base):
        nonlocal ip
        if t:
            return t
        n = 0
        while src[ip] == 0:
            n += 255
            ip += 1
        n += base + src[ip]
        ip += 1
        return n

    def copy_match(dist, length):
        start = len(dst) - dist
        for i in range(length):
            dst.append(dst[start + i])

    state = 0
    if src[0] > 17:
        t = src[0] - 17
        ip = 1
        dst += src[ip:ip + t]
        ip += t
        state = 4 if t >= 4 else t
    while len(dst) < out_len:
        t = src[ip]
        ip += 1
        if t < 16:
            if state == 0:
                length = 3 + run_length(t & 15, 4, 15)
                dst += src[ip:ip + length]
                ip += length
                state = 4
                continue
            h = src[ip]
            ip += 1
            if state < 4:
                copy_match((h << 2) + (t >> 2) + 1, 2)
            else:
                copy_match((h << 2) + (t >> 2) + 2049, 3)
            s = t & 3
        elif t < 32:
            length = 2 + run_length(t & 7, 3, 7)
            b1, b2 = src[ip], src[ip + 1]
            ip += 2
            dist = 16384 + ((t & 8) << 11) + (b1 >> 2) + (b2 << 6)
            if dist == 16384:
                break
            copy_match(dist, length)
            s = b1 & 3
        elif t < 64:
            length = 2 + run_length(t & 31, 5, 31)
            b1, b2 = src[ip], src[ip + 1]
            ip += 2
            copy_match((b1 >> 2) + (b2 << 6) + 1, length)
            s = b1 & 3
        else:
            h = src[ip]
            ip += 1
            if t < 128:
                length = 3 + ((t >> 5) & 1)
            else:
                length = 5 + ((t >> 5) & 3)
            copy_match((h << 3) + ((t >> 2) & 7) + 1, length)
            s = t & 3
        dst += src[ip:ip + s]
        ip += s
        state = s
    return bytes(dst[:out_len])


def read_paa(path):
    data = open(path, "rb").read()
    kind = struct.unpack_from("<H", data, 0)[0]
    if kind not in TYPES:
        raise SystemExit(f"unsupported PAA type {kind:#x}")
    pos = 2
    while data[pos:pos + 4] == b"GGAT":
        size = struct.unpack_from("<I", data, pos + 8)[0]
        pos += 12 + size
    palette = struct.unpack_from("<H", data, pos)[0]
    pos += 2 + 3 * palette
    w, h = struct.unpack_from("<HH", data, pos)
    size = int.from_bytes(data[pos + 4:pos + 7], "little")
    raw = data[pos + 7:pos + 7 + size]
    lzo = bool(w & 0x8000)
    w &= 0x7FFF
    decoder, n = TYPES[kind]
    if decoder == "bcn":
        want = (w // 4) * (h // 4) * (8 if n == 1 else 16)
        if lzo:
            raw = lzo1x_decompress(raw, want)
        return Image.frombytes("RGBA", (w, h), raw, "bcn", n)
    img = Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA")
    return img


if __name__ == "__main__":
    read_paa(sys.argv[1]).save(sys.argv[2])
    print("saved", sys.argv[2])
