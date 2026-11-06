"""Tes pipeline video. Jalankan: python tests/test_videogen.py (butuh ffmpeg atau imageio-ffmpeg)."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from buat_video import load_naskah, main  # noqa: E402
from videogen.render import make_chunks  # noqa: E402
from videogen.tts import even_words  # noqa: E402
from videogen.util import ffmpeg_exe  # noqa: E402


def test_chunks():
    words = [(f"kata{i}", i * 0.3, i * 0.3 + 0.3) for i in range(7)]
    chunks = make_chunks(words)
    assert sum(len(c) for c in chunks) == 7, "semua kata harus masuk frasa"
    assert all(len(c) <= 3 for c in chunks)
    punct = make_chunks([("halo,", 0, 1), ("dunia", 1, 2)])
    assert len(punct) == 2, "koma harus memutus frasa"


def test_even_words():
    w = even_words("satu dua tiga", 3.0)
    assert len(w) == 3 and abs(w[-1][2] - 3.0) < 1e-9
    assert all(w[i][2] <= w[i + 1][1] + 1e-9 for i in range(2))


def test_naskah_contoh_valid():
    d = load_naskah(ROOT / "naskah" / "langit_biru.json")
    assert len(d["adegan"]) >= 5


def test_render_offline():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        naskah = tmp / "t.json"
        naskah.write_text(json.dumps({
            "judul": "Tes",
            "caption": "c", "hashtag": ["#a"],
            "adegan": [
                {"narasi": "Halo dunia sains yang menakjubkan.", "kamera": "zoom_in"},
                {"narasi": "Ini adegan kedua untuk tes.", "kamera": "pan_kiri"},
            ]}), encoding="utf-8")
        out = tmp / "out.mp4"
        rc = main([str(naskah), "-o", str(out), "--offline", "--draft", "--fps", "10",
                   "--cache", str(tmp / "cache")])
        assert rc == 0 and out.exists() and out.stat().st_size > 1000
        assert out.with_suffix(".txt").exists()
        info = subprocess.run([ffmpeg_exe(), "-i", str(out)], capture_output=True, text=True).stderr
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
        dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
        assert 4 < dur < 12, f"durasi tak wajar: {dur}"
        assert "540x960" in info and "Audio" in info


def test_render_dengan_klip():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        clip = tmp / "c.mp4"  # klip 1 dtk, lebih pendek dari narasi -> harus diperlambat/ditahan
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=size=320x568:rate=15:duration=1", "-pix_fmt", "yuv420p", str(clip)], check=True)
        naskah = tmp / "t.json"
        naskah.write_text(json.dumps({
            "judul": "Klip", "adegan": [
                {"narasi": "Adegan dengan klip video buatan AI.", "video": "c.mp4"},
                {"narasi": "Adegan tanpa klip pakai gambar."},
            ]}), encoding="utf-8")
        out = tmp / "o.mp4"
        assert main([str(naskah), "-o", str(out), "--offline", "--draft", "--fps", "10",
                     "--cache", str(tmp / "cache")]) == 0
        assert out.exists() and out.stat().st_size > 1000
        # klip hilang -> pesan jelas, bukan crash tak terduga
        naskah.write_text(json.dumps({"adegan": [{"narasi": "x", "video": "tidak_ada.mp4"}]}), encoding="utf-8")
        try:
            main([str(naskah), "--offline"])
            raise AssertionError("seharusnya gagal")
        except SystemExit as e:
            assert "klip tidak ditemukan" in str(e)


def test_klip_otomatis():
    from buat_video import klip_otomatis
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        assert klip_otomatis(tmp, 1) is None
        (tmp / "adegan_2.mov").write_bytes(b"x")
        assert klip_otomatis(tmp, 2).name == "adegan_2.mov" and klip_otomatis(tmp, 1) is None
        # end-to-end: klip di folder dipakai tanpa field 'video'
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=size=320x568:rate=15:duration=1", "-pix_fmt", "yuv420p",
                        str(tmp / "adegan_1.mp4")], check=True)
        naskah = tmp / "t.json"
        naskah.write_text(json.dumps({"judul": "Auto", "adegan": [{"narasi": "Satu dua tiga empat."}]}),
                          encoding="utf-8")
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main([str(naskah), "-o", str(tmp / "o.mp4"), "--offline", "--draft", "--fps", "10",
                       "--cache", str(tmp / "cache"), "--klip-dir", str(tmp)])
        assert rc == 0 and "KLIP VIDEO adegan_1.mp4" in buf.getvalue()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("videogen tests OK")
