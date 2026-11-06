"""Klip video per adegan: dicocokkan ke durasi narasi (diperlambat / dipotong / frame terakhir ditahan)."""
import re
import subprocess

from PIL import Image

from .util import ffmpeg_exe


def clip_duration(path):
    r = subprocess.run([ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise RuntimeError(f"Tidak bisa membaca klip video: {path}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def clip_frames(path, length, w, h, fps, max_slow=2.0):
    """Generator frame PIL (RGB, w x h) sepanjang `length` detik; setelah klip habis, frame terakhir ditahan."""
    dur = clip_duration(path)
    slow = min(max(1.0, length / dur), max_slow) if dur < length else 1.0
    vf = (f"setpts=PTS*{slow:.4f},fps={fps},"
          f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
          f"tpad=stop_mode=clone:stop_duration={length:.3f}")
    cmd = [ffmpeg_exe(), "-loglevel", "error", "-i", str(path), "-an", "-vf", vf,
           "-t", f"{length:.3f}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = w * h * 3
    last = None
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            last = Image.frombytes("RGB", (w, h), buf)
            yield last
        if last is None:
            raise RuntimeError(f"Klip tidak menghasilkan frame: {path}")
        while True:
            yield last
    finally:
        proc.stdout.close()
        proc.kill()
        proc.wait()
