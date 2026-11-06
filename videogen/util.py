"""Utilitas: lokasi ffmpeg dan font."""
import os
import shutil

from PIL import ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\ariblk.ttf",   # Arial Black (Windows)
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/Library/Fonts/Arial Black.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def ffmpeg_exe():
    """Pakai ffmpeg di PATH; kalau tidak ada, pakai yang dibawa paket imageio-ffmpeg."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "ffmpeg tidak ditemukan. Jalankan: pip install imageio-ffmpeg"
        ) from e


def find_font(size, custom=None):
    for path in ([custom] if custom else []) + FONT_CANDIDATES:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()
