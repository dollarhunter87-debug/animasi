"""Gambar adegan: file lokal > Pollinations (AI gratis, tanpa API key) > placeholder gradien."""
import colorsys
import hashlib
import io
import random
import textwrap
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

from .util import find_font

UA = {"User-Agent": "Mozilla/5.0 (videogen)"}


def _pollinations(prompt, w, h, seed, retries=3, timeout=120):
    url = (
        "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
        + f"?width={w}&height={h}&seed={seed}&nologo=true"
    )
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                img = Image.open(io.BytesIO(r.read()))
                img.load()
                return img.convert("RGB")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last))


def placeholder(label, seed, w, h):
    """Gambar cadangan: gradien + lingkaran lembut + teks kata kunci."""
    rnd = random.Random(seed)
    hue = rnd.random()
    top = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.55, 0.55))
    bot = tuple(int(c * 255) for c in colorsys.hsv_to_rgb((hue + 0.12) % 1, 0.6, 0.95))
    img = Image.new("RGB", (w, h))
    px = ImageDraw.Draw(img)
    for y in range(h):
        k = y / (h - 1)
        px.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
    over = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    for _ in range(7):
        r = rnd.randint(w // 8, w // 3)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        od.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rnd.randint(18, 46)))
    img = Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")
    d = ImageDraw.Draw(img)
    font = find_font(max(22, w // 22))
    lines = textwrap.wrap(label, width=20)[:4]  # tetap di area tengah agar tidak terpotong zoom kamera
    y = h * 0.2
    for line in lines:
        tw = d.textlength(line, font=font)
        d.text(((w - tw) / 2, y), line, font=font, fill=(255, 255, 255))
        y += font.size * 1.3 if hasattr(font, "size") else 40
    return img


def get_image(scene, idx, style, w, h, cache_dir, base_dir, offline=False, log=print):
    """Kembalikan PIL.Image RGB untuk satu adegan."""
    local = scene.get("gambar")
    if local:
        p = Path(local)
        if not p.is_absolute():
            p = Path(base_dir) / p
        return Image.open(p).convert("RGB")

    prompt = scene.get("gambar_prompt") or scene.get("narasi", "")
    seed = int(scene.get("seed", 1000 + idx))
    if offline:
        return placeholder(prompt, seed, w, h)

    full = f"{prompt}, {style}" if style else prompt
    key = hashlib.sha1(f"{full}|{seed}|{w}x{h}".encode("utf-8")).hexdigest()[:16]
    cached = Path(cache_dir) / f"img_{key}.jpg"
    if cached.exists():
        return Image.open(cached).convert("RGB")
    try:
        img = _pollinations(full, w, h, seed)
        img.save(cached, quality=92)
        return img
    except Exception as e:  # noqa: BLE001
        log(f"  ! adegan {idx + 1}: gagal membuat gambar AI ({e}); pakai gambar cadangan. "
            "Taruh gambar sendiri lewat field 'gambar' di naskah.")
        return placeholder(prompt, seed, w, h)
