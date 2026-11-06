"""Render: gerak kamera (Ken Burns), subtitle besar per frasa, transisi, lalu mux ke MP4 lewat ffmpeg."""
import re
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw

from .tts import SR
from .util import ffmpeg_exe, find_font

PAD = 0.45          # jeda hening antar adegan (detik)
FADE_FRAMES = 6     # lama transisi antar adegan (frame)
MARGIN = 1.3        # gambar dasar sebesar 1.3x layar supaya ada ruang untuk zoom/pan
WHITE, YELLOW, BLACK = (255, 255, 255), (255, 221, 64), (0, 0, 0)


def make_chunks(words, max_words=3, max_chars=22):
    """Kelompokkan kata jadi frasa pendek untuk subtitle."""
    chunks, cur = [], []
    for w in words:
        n = sum(len(x[0]) for x in cur) + len(cur) + len(w[0])
        if cur and (len(cur) >= max_words or n > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?,]$", w[0]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def ease(p):
    return p * p * (3 - 2 * p)


def prepare_base(img, w, h):
    """Crop tengah ke rasio layar, lalu skala ke MARGIN x ukuran output."""
    bw, bh = int(w * MARGIN), int(h * MARGIN)
    ratio = w / h
    iw, ih = img.size
    if iw / ih > ratio:
        nw = int(ih * ratio)
        img = img.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
    else:
        nh = int(iw / ratio)
        img = img.crop((0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh))
    return img.resize((bw, bh), Image.LANCZOS)


def camera_frame(base, mode, p, w, h):
    bw, bh = base.size
    p = ease(p)
    cx, cy = bw / 2, bh / 2
    if mode == "zoom_out":
        s = 1.0 + 0.25 * p
    elif mode in ("pan_kiri", "pan_kanan"):
        s = 1.12
        span = (bw - w * s) / 2
        cx += span * (1 - 2 * p) * (1 if mode == "pan_kiri" else -1)
    else:  # zoom_in (bawaan)
        s = 1.25 - 0.25 * p
    cw, ch = w * s, h * s
    x0 = min(max(cx - cw / 2, 0), bw - cw)
    y0 = min(max(cy - ch / 2, 0), bh - ch)
    return base.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def caption_image(words, active, font, w, size):
    """Gambar RGBA frasa subtitle; kata aktif berwarna kuning."""
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    maxw = int(w * 0.86)
    space = d0.textlength(" ", font=font)
    lines, cur, curw = [], [], 0.0
    for i, (text, _, _) in enumerate(words):
        tw = d0.textlength(text, font=font)
        if cur and curw + space + tw > maxw:
            lines.append((cur, curw))
            cur, curw = [], 0.0
        curw += (space if cur else 0) + tw
        cur.append((i, text, tw))
    lines.append((cur, curw))
    lh = int(size * 1.3)
    stroke = max(5, size // 9)
    pad = stroke * 2
    img = Image.new("RGBA", (w, lh * len(lines) + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = pad
    for line, lw in lines:
        x = (w - lw) / 2
        for i, text, tw in line:
            d.text((x, y), text, font=font, fill=YELLOW if i == active else WHITE,
                   stroke_width=stroke, stroke_fill=BLACK)
            x += tw + space
        y += lh
    return img


def _bottom_shade(w, h):
    """Gradasi gelap di bagian bawah supaya subtitle selalu terbaca."""
    mask = Image.new("L", (1, h))
    for y in range(h):
        k = max(0.0, (y / h - 0.45) / 0.55)
        mask.putpixel((0, y), int(130 * k))
    return mask.resize((w, h))


def _write_audio(narrations, path):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SR)
        for n in narrations:
            with wave.open(str(n.wav), "rb") as r:
                out.writeframes(r.readframes(r.getnframes()))
            out.writeframes(b"\x00\x00" * int(SR * PAD))


def render_video(scenes, narrations, images, out_path, workdir, w=1080, h=1920, fps=30,
                 font_path=None, music=None, log=print):
    """scenes: list dict naskah (field 'kamera'); narrations & images sejajar dengan scenes."""
    out_path, workdir = Path(out_path), Path(workdir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio = workdir / "narasi_semua.wav"
    _write_audio(narrations, audio)

    font = find_font(max(34, int(w * 0.085)), font_path)
    size = font.size if hasattr(font, "size") else int(w * 0.085)
    shade = _bottom_shade(w, h)
    black = Image.new("RGB", (w, h), BLACK)

    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-i", str(audio)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music), "-filter_complex",
                "[2:a]volume=0.12[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    prev_last = None
    try:
        for si, (sc, nar, img) in enumerate(zip(scenes, narrations, images)):
            base = prepare_base(img, w, h)
            mode = sc.get("kamera", "zoom_in")
            length = nar.duration + PAD
            n = max(1, round(length * fps))
            chunks = make_chunks(nar.words)
            cache = {}
            log(f"  adegan {si + 1}/{len(scenes)}: {length:.1f} dtk, {n} frame")
            for fi in range(n):
                t = fi / fps
                frame = camera_frame(base, mode, fi / max(1, n - 1), w, h)
                frame.paste(black, (0, 0), shade)

                for ci, ch in enumerate(chunks):
                    start = ch[0][1]
                    end = chunks[ci + 1][0][1] if ci + 1 < len(chunks) else length
                    if start <= t < end:
                        active = max((i for i, wd in enumerate(ch) if wd[1] <= t), default=0)
                        key = (ci, active)
                        if key not in cache:
                            cache[key] = caption_image(ch, active, font, w, size)
                        cap = cache[key]
                        age = t - start
                        if age < 0.12:  # efek pop kecil saat frasa muncul
                            k = 0.85 + 0.15 * (age / 0.12)
                            cap = cap.resize((w, max(1, int(cap.height * k))), Image.BILINEAR)
                        frame.paste(cap, (0, int(h * 0.64 - cap.height / 2)), cap)
                        break

                if fi < FADE_FRAMES:
                    src = prev_last if prev_last is not None else black
                    frame = Image.blend(src, frame, (fi + 1) / (FADE_FRAMES + 1))
                proc.stdin.write(frame.tobytes())
            prev_last = frame
    finally:
        proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg gagal (kode {code})")
    return out_path
