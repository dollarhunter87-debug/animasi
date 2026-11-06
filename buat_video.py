"""CLI: naskah JSON -> video MP4 9:16 (TikTok / Reels / Shorts / Facebook).

Contoh:
    python buat_video.py naskah/langit_biru.json
    python buat_video.py naskah/langit_biru.json --draft        # cepat, resolusi kecil, untuk cek
    python buat_video.py naskah/langit_biru.json --offline      # tes tanpa internet (tanpa suara)
"""
import argparse
import json
import re
import sys
from pathlib import Path

from videogen.images import get_image
from videogen.render import render_video
from videogen.tts import make_narration

DEFAULT_STYLE = ("3D animated render, soft cinematic lighting, vibrant colors, "
                 "vertical composition, no text, no watermark")
KAMERA = {"zoom_in", "zoom_out", "pan_kiri", "pan_kanan"}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "video"


def load_naskah(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    scenes = data.get("adegan")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("Naskah tidak valid: field 'adegan' harus berupa daftar yang tidak kosong.")
    for i, sc in enumerate(scenes, 1):
        if not str(sc.get("narasi", "")).strip():
            raise SystemExit(f"Naskah tidak valid: adegan {i} tidak punya 'narasi'.")
        if sc.get("kamera") and sc["kamera"] not in KAMERA:
            raise SystemExit(f"Adegan {i}: 'kamera' harus salah satu dari {sorted(KAMERA)}.")
        if sc.get("video"):
            vp = resolve(path, sc["video"])
            if not vp.exists():
                raise SystemExit(f"Adegan {i}: file klip tidak ditemukan: {vp}\n"
                                 "Buat klipnya dulu (lihat --prompt-klip), atau hapus field 'video' "
                                 "agar adegan memakai gambar + zoom.")
    return data


def resolve(naskah_path, rel):
    p = Path(rel)
    return p if p.is_absolute() else Path(naskah_path).resolve().parent / p


def tulis_prompt_klip(data, naskah_path, slug, w, h, start_images, offline):
    """Tulis daftar prompt untuk generator video AI + (opsional) unduh gambar awal tiap adegan."""
    folder = Path("klip") / slug
    folder.mkdir(parents=True, exist_ok=True)
    style = data.get("gaya", DEFAULT_STYLE)
    lines = [f"DAFTAR KLIP: {data.get('judul', slug)}",
             "Buat satu klip 5 detik, format vertikal 9:16, untuk tiap adegan. Simpan sebagai adegan_N.mp4 "
             f"di folder {folder} lalu isi field \"video\" di naskah.", ""]
    for i, sc in enumerate(data["adegan"], 1):
        est = max(2.0, len(sc["narasi"].split()) * 0.38) + 0.45
        gerak = sc.get("prompt_gerak") or sc.get("gambar_prompt", "")
        lines += [f"--- Adegan {i} (narasi ~{est:.0f} detik) ---",
                  f"Narasi : {sc['narasi']}",
                  f"Prompt : {gerak}. {style}",
                  f"Simpan : {folder / f'adegan_{i}.mp4'}", ""]
        if start_images:
            img = get_image(sc, i - 1, style, w, h, folder, Path(naskah_path).resolve().parent, offline)
            img.save(folder / f"adegan_{i}.jpg", quality=92)
    out = folder / "daftar_prompt.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Buat video explainer dari naskah JSON.")
    ap.add_argument("naskah", help="file naskah .json")
    ap.add_argument("-o", "--output", help="file MP4 keluaran (bawaan: keluaran/<judul>.mp4)")
    ap.add_argument("--draft", action="store_true", help="resolusi 540x960 supaya cepat")
    ap.add_argument("--offline", action="store_true", help="tanpa internet: audio hening + gambar cadangan")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--musik", help="file musik latar (mp3/wav) yang boleh dipakai komersial")
    ap.add_argument("--font", help="path file font .ttf untuk subtitle")
    ap.add_argument("--cache", default="cache", help="folder cache suara & gambar")
    ap.add_argument("--prompt-klip", action="store_true",
                    help="hanya tulis daftar prompt untuk generator video AI, lalu selesai")
    ap.add_argument("--gambar-awal", action="store_true",
                    help="dengan --prompt-klip: unduh juga gambar awal tiap adegan (untuk image-to-video)")
    args = ap.parse_args(argv)

    data = load_naskah(args.naskah)
    base_dir = Path(args.naskah).resolve().parent
    title = data.get("judul", Path(args.naskah).stem)
    slug = slugify(title)
    w, h = (540, 960) if args.draft else (1080, 1920)
    out = Path(args.output) if args.output else Path("keluaran") / f"{slug}.mp4"
    work = Path(args.cache) / slug
    work.mkdir(parents=True, exist_ok=True)

    if args.prompt_klip:
        daftar = tulis_prompt_klip(data, args.naskah, slug, w, h, args.gambar_awal, args.offline)
        print(f"Daftar prompt klip: {daftar}")
        return 0

    voice = data.get("suara", "id-ID-ArdiNeural")
    rate = data.get("kecepatan", "+0%")
    style = data.get("gaya", DEFAULT_STYLE)
    scenes = data["adegan"]

    print(f"[1/3] Membuat narasi suara ({len(scenes)} adegan)...")
    narrations = [make_narration(sc["narasi"], voice, rate, work / f"narasi_{i}", args.offline)
                  for i, sc in enumerate(scenes)]

    print("[2/3] Menyiapkan gambar/klip...")
    images, clips = [], []
    for i, sc in enumerate(scenes):
        if sc.get("video"):
            print(f"  klip {i + 1}/{len(scenes)}: {sc['video']}")
            clips.append(resolve(args.naskah, sc["video"]))
            images.append(None)
        else:
            print(f"  gambar {i + 1}/{len(scenes)}")
            clips.append(None)
            images.append(get_image(sc, i, style, w, h, work, base_dir, args.offline))

    print("[3/3] Merender video...")
    render_video(scenes, narrations, images, out, work, w, h, args.fps,
                 font_path=args.font, music=args.musik, clips=clips)

    caption = data.get("caption", title)
    tags = data.get("hashtag", [])
    txt = out.with_suffix(".txt")
    txt.write_text(
        caption + "\n\n" + " ".join(tags) + "\n\n"
        "[Ingat] Aktifkan label 'konten buatan AI' saat upload dan cek ulang fakta di naskah.\n",
        encoding="utf-8")
    print(f"Selesai: {out}\nCaption: {txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
