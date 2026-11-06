# Motion Studio

Editor kinetic typography 9:16 (format TikTok/Reels/Shorts) berbasis web. Tanpa build, tanpa dependensi.

## Menjalankan
Buka `index.html` di Chrome/Edge/Firefox. Tes engine: `node tests/engine.test.js`.

## Fitur
- Kanvas 1080x1920 dengan preview real-time (Spasi = putar/jeda)
- 10 preset teks: pop, bounce, jatuh+miring, putar, stretch kenyal, slide, zoom slam, typewriter, fade
- Animasi per huruf / kata / baris dengan stagger, animasi masuk + keluar, loop (pulse/wiggle/float)
- Easing: outBack, outElastic, outBounce, spring, outExpo, dll.
- Glow, outline, warna, font, posisi
- Timeline: drag untuk geser, tarik tepi kanan untuk durasi, klik penggaris untuk scrub, snap ke grid BPM
- Overlay safe area TikTok (tidak ikut terekam)
- Ekspor video (MP4 bila didukung browser, selain itu WebM), PNG frame, simpan/buka scene JSON

## Struktur
- `src/engine.js` — easing, preset, layout, renderer (murni, bisa dites di Node)
- `src/app.js` — UI: inspector, timeline, ekspor

---

# Pembuat Video Explainer Otomatis (Windows, gratis)

Dari satu file naskah JSON menjadi video MP4 9:16 (1080x1920) untuk TikTok, Reels, Shorts, dan Facebook:
narasi suara Indonesia -> gambar AI per adegan -> gerak kamera -> subtitle besar per frasa -> MP4.

## Pasang (sekali saja)
```
pip install -r requirements.txt
```
ffmpeg ikut terpasang lewat paket `imageio-ffmpeg`, tidak perlu pasang terpisah.

## Pakai
```
python buat_video.py naskah\langit_biru.json
```
Hasil: `keluaran\kenapa_langit_biru.mp4` dan file `.txt` berisi caption + hashtag.

Opsi: `--draft` (resolusi kecil, cepat untuk cek), `--musik lagu.mp3` (musik latar bebas hak cipta),
`--offline` (tes tanpa internet, tanpa suara), `--font C:\path\font.ttf`.

## Membuat video baru
Minta Claude: "buatkan naskah sains tentang <topik>". Simpan hasil JSON-nya di folder `naskah\`, lalu jalankan perintah di atas.
Tiap adegan: `narasi`, `gambar_prompt` (deskripsi gambar, bahasa Inggris lebih akurat), `kamera`
(`zoom_in`, `zoom_out`, `pan_kiri`, `pan_kanan`). Mau pakai gambar sendiri: isi `"gambar": "folder\\foto.png"`.

## Yang perlu diketahui
- Suara memakai edge-tts dan gambar memakai Pollinations: keduanya gratis tapi layanan tidak resmi, bisa lambat atau berubah.
  Kalau gambar gagal dibuat, program memakai gambar cadangan dan memberi peringatan.
- Hasil visual adalah ilustrasi AI bergerak (zoom/pan), bukan animasi 3D sungguhan.
- Cek ulang fakta naskah sebelum upload, aktifkan label konten AI, dan pakai musik berlisensi jelas.
- Tes: `python tests/test_videogen.py`

## Video dengan gerakan sungguhan (klip AI per adegan)

Gambar diam + zoom kurang hidup. Untuk gerakan sungguhan, ubah tiap adegan jadi klip video lewat generator
video AI online (tidak perlu GPU), lalu pipeline menggabungkannya dengan suara dan subtitle.

1. Buat daftar prompt dan gambar awal tiap adegan:
   ```
   py buat_video.py naskah\langit_biru.json --prompt-klip --gambar-awal
   ```
   Hasil di `klip\<judul>\`: `daftar_prompt.txt` dan `adegan_1.jpg`, `adegan_2.jpg`, dst.
2. Di situs/aplikasi generator video AI pilih mode **image-to-video**: unggah `adegan_N.jpg`, tempel prompt dari
   `daftar_prompt.txt`, pilih rasio 9:16 dan durasi sekitar 5 detik. Unduh hasilnya sebagai `adegan_N.mp4`
   ke folder yang sama. (Kuota gratis dan ketentuan tiap layanan berbeda; cek langsung di situsnya.)
3. Di naskah, tambahkan ke tiap adegan: `"video": "..\\klip\\kenapa_langit_biru\\adegan_1.mp4"`
   (path relatif terhadap folder file naskah). Adegan tanpa field `video` tetap memakai gambar + zoom,
   jadi boleh dicampur.
4. Render seperti biasa: `py buat_video.py naskah\langit_biru.json`

Klip yang lebih pendek dari narasi diperlambat (maks 2x) lalu frame terakhirnya ditahan; klip yang lebih
panjang dipotong. Audio klip dibuang, yang dipakai hanya narasi.
