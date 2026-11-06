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
