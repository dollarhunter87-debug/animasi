"""Narasi suara: edge-tts (gratis, suara Indonesia) + waktu per kata untuk subtitle.
Mode offline membuat audio hening supaya alur bisa dites tanpa internet."""
import asyncio
import re
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from .util import ffmpeg_exe

SR = 44100


@dataclass
class Narration:
    wav: Path
    duration: float
    words: list  # [(teks, mulai, selesai)] detik, relatif terhadap awal adegan


def even_words(text, duration):
    """Bagi waktu ke tiap kata sebanding panjang kata (cadangan bila TTS tak memberi timestamp)."""
    toks = re.findall(r"\S+", text)
    if not toks:
        return []
    weights = [max(1, len(t)) for t in toks]
    total = sum(weights)
    t, out = 0.0, []
    for tok, w in zip(toks, weights):
        d = duration * w / total
        out.append((tok, t, t + d))
        t += d
    return out


def _silent_wav(path, duration):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"\x00\x00" * int(SR * duration))


def wav_duration(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


async def _edge(text, voice, rate, mp3_path):
    import edge_tts

    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:  # edge-tts versi lama: WordBoundary sudah bawaan
        comm = edge_tts.Communicate(text, voice, rate=rate)
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((chunk["text"], start, start + chunk["duration"] / 1e7))
    return words


def make_narration(text, voice, rate, base, offline=False):
    base = Path(base)
    wav = base.with_suffix(".wav")
    if offline:
        dur = max(2.0, len(text.split()) * 0.38)
        _silent_wav(wav, dur)
        return Narration(wav, dur, even_words(text, dur))

    mp3 = base.with_suffix(".mp3")
    try:
        words = asyncio.run(_edge(text, voice, rate, mp3))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"Gagal membuat suara dengan edge-tts ({e}). Cek koneksi internet, "
            "atau jalankan dengan --offline untuk tes tanpa suara."
        ) from e
    subprocess.run(
        [ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(mp3),
         "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", str(wav)],
        check=True,
    )
    dur = wav_duration(wav)
    words = [(w, s, min(e, dur)) for (w, s, e) in words] or even_words(text, dur)
    return Narration(wav, dur, words)
