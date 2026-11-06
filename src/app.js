/* UI editor: preview, inspector, timeline, ekspor. Bergantung pada window.Motion (engine.js). */
(function () {
  'use strict';
  const M = window.Motion;
  const $ = (s) => document.querySelector(s);
  const canvas = $('#stage');
  const ctx = canvas.getContext('2d');
  const PPS = 90; // piksel timeline per detik

  let scene = defaultScene();
  let sel = scene.layers[0].id;
  let t = 0, playing = false, last = 0, recorder = null;
  let snapOn = true;
  const layerInputs = {};

  function defaultScene() {
    const s = M.newScene();
    s.layers = [
      M.newLayer({ text: 'MOTION\nSTUDIO', start: 0.2, dur: 3, preset: 'zoomSlam', fontSize: 230, y: 0.38, strokeWidth: 8, glow: 40, inDur: 0.6 }),
      M.newLayer({ text: 'teks yang hidup & kenyal', start: 1.2, dur: 3.5, preset: 'bounceUp', fontSize: 90, y: 0.56, font: 'Arial Black', color: '#ffe14d', loop: 'float', stagger: 0.04 }),
      M.newLayer({ text: 'GAS TERUS', start: 4.6, dur: 3.2, preset: 'stretch', fontSize: 200, y: 0.5, color: '#ff4d8d', glow: 50, glowColor: '#ff4d8d', loop: 'pulse' }),
    ];
    return s;
  }

  const byId = (id) => scene.layers.find((l) => l.id === id);
  const cur = () => byId(sel);

  // ---------- Form builder ----------
  const presetOpts = Object.entries(M.PRESETS).map(([k, v]) => [k, v.label]);
  const easeOpts = [['', 'Bawaan preset']].concat(Object.keys(M.EASINGS).map((k) => [k, k]));
  const loopOpts = Object.entries(M.LOOPS);
  const unitOpts = [['auto', 'Otomatis'], ['char', 'Per huruf'], ['word', 'Per kata'], ['line', 'Per baris']];
  const fontOpts = ['Impact', 'Arial Black', 'Helvetica', 'Georgia', 'Courier New', 'system-ui'].map((f) => [f, f]);

  const LAYER_FIELDS = [
    ['text', 'Teks', 'textarea'],
    ['preset', 'Preset', 'select', presetOpts],
    ['unit', 'Unit animasi', 'select', unitOpts],
    ['ease', 'Easing', 'select', easeOpts],
    ['loop', 'Loop', 'select', loopOpts],
    ['start', 'Mulai (dtk)', 'number', { step: 0.05, min: 0 }],
    ['dur', 'Durasi (dtk)', 'number', { step: 0.05, min: 0.2 }],
    ['inDur', 'Durasi masuk', 'number', { step: 0.05, min: 0.05 }],
    ['stagger', 'Jeda antar unit', 'number', { step: 0.01, min: 0 }],
    ['out', 'Animasi keluar', 'checkbox'],
    ['font', 'Font', 'select', fontOpts],
    ['fontSize', 'Ukuran', 'number', { step: 5, min: 10 }],
    ['color', 'Warna', 'color'],
    ['strokeWidth', 'Outline', 'number', { step: 1, min: 0 }],
    ['strokeColor', 'Warna outline', 'color'],
    ['glow', 'Glow', 'number', { step: 5, min: 0 }],
    ['glowColor', 'Warna glow', 'color'],
    ['x', 'Posisi X', 'range', { min: 0, max: 1, step: 0.01 }],
    ['y', 'Posisi Y', 'range', { min: 0, max: 1, step: 0.01 }],
  ];
  const SCENE_FIELDS = [
    ['duration', 'Durasi scene', 'number', { step: 0.5, min: 1 }],
    ['bpm', 'BPM (grid beat)', 'number', { step: 1, min: 0 }],
    ['bg1', 'Latar atas', 'color'],
    ['bg2', 'Latar bawah', 'color'],
  ];

  function makeInput(type, extra) {
    let el;
    if (type === 'textarea') el = document.createElement('textarea');
    else if (type === 'select') {
      el = document.createElement('select');
      for (const [v, l] of extra) el.add(new Option(l, v));
    } else {
      el = document.createElement('input');
      el.type = type;
      if (extra && type !== 'checkbox') Object.assign(el, extra);
    }
    return el;
  }

  function buildForm(container, fields, getObj, onChange, registry) {
    container.innerHTML = '';
    for (const [key, label, type, extra] of fields) {
      const lab = document.createElement('label');
      lab.textContent = label;
      const el = makeInput(type, extra);
      const isNum = type === 'number' || type === 'range';
      el.addEventListener('input', () => {
        const o = getObj();
        if (!o) return;
        o[key] = type === 'checkbox' ? el.checked : isNum ? parseFloat(el.value) || 0 : el.value;
        onChange(key);
      });
      container.append(lab, el);
      registry[key] = el;
    }
  }

  function fillForm(fields, obj, registry) {
    if (!obj) return;
    for (const [key, , type] of fields) {
      const el = registry[key];
      if (!el || document.activeElement === el) continue;
      if (type === 'checkbox') el.checked = !!obj[key]; else el.value = obj[key];
    }
  }

  const sceneInputs = {};
  buildForm($('#sceneForm'), SCENE_FIELDS, () => scene, (k) => {
    if (k === 'duration') t = Math.min(t, scene.duration);
    buildTimeline(); draw();
  }, sceneInputs);
  buildForm($('#layerForm'), LAYER_FIELDS, cur, (k) => {
    if (['start', 'dur', 'text'].includes(k)) buildTimeline();
    draw();
  }, layerInputs);

  function refreshForms() {
    fillForm(SCENE_FIELDS, scene, sceneInputs);
    fillForm(LAYER_FIELDS, cur(), layerInputs);
  }

  // ---------- Render ----------
  function draw() {
    M.renderScene(ctx, scene, t);
    $('#time').textContent = `${t.toFixed(2)} / ${scene.duration.toFixed(2)}s`;
    const ph = $('#ph');
    if (ph) ph.style.left = t * PPS + 'px';
  }

  function tick(now) {
    if (playing) {
      t += (now - last) / 1000;
      if (t >= scene.duration) {
        if (recorder) { t = scene.duration; draw(); recorder.stop(); return; }
        t = 0;
      }
      draw();
    }
    last = now;
    requestAnimationFrame(tick);
  }

  function setPlaying(p) {
    playing = p;
    $('#btnPlay').textContent = p ? '⏸ Jeda' : '▶ Putar';
  }

  // ---------- Timeline ----------
  const el = (tag, cls) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };

  function snap(v) {
    if (!snapOn) return v;
    const step = scene.bpm > 0 ? 60 / scene.bpm / 2 : 0.1;
    return Math.round(v / step) * step;
  }

  function buildTimeline() {
    const tl = $('#tl');
    tl.innerHTML = '';
    tl.style.width = scene.duration * PPS + 40 + 'px';
    const ruler = el('div', 'ruler');
    tl.appendChild(ruler);
    for (let s = 0; s <= Math.floor(scene.duration); s++) {
      const tk = el('div', 'tick'); tk.style.left = s * PPS + 'px'; tk.textContent = s + 's'; ruler.appendChild(tk);
    }
    if (scene.bpm > 0) {
      const step = 60 / scene.bpm;
      for (let b = 0; b <= scene.duration; b += step) { const d = el('div', 'beat'); d.style.left = b * PPS + 'px'; tl.appendChild(d); }
    }
    const scrub = (e) => {
      const r = tl.getBoundingClientRect();
      t = M.clamp((e.clientX - r.left) / PPS, 0, scene.duration);
      draw();
    };
    ruler.addEventListener('pointerdown', (e) => {
      scrub(e);
      const up = () => { removeEventListener('pointermove', scrub); removeEventListener('pointerup', up); };
      addEventListener('pointermove', scrub); addEventListener('pointerup', up);
    });

    scene.layers.forEach((L) => {
      const row = el('div', 'row');
      const bar = el('div', 'bar' + (L.id === sel ? ' sel' : ''));
      bar.dataset.id = L.id;
      bar.style.left = L.start * PPS + 'px';
      bar.style.width = L.dur * PPS + 'px';
      bar.textContent = L.text.replace(/\n/g, ' ');
      const handle = el('div', 'handle');
      bar.appendChild(handle);
      bar.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        select(L.id);
        const mode = e.target === handle ? 'resize' : 'move';
        const x0 = e.clientX, s0 = L.start, d0 = L.dur;
        const mv = (ev) => {
          const dt = (ev.clientX - x0) / PPS;
          if (mode === 'move') L.start = Math.max(0, snap(s0 + dt));
          else L.dur = Math.max(0.2, snap(d0 + dt));
          bar.style.left = L.start * PPS + 'px';
          bar.style.width = L.dur * PPS + 'px';
          refreshForms(); draw();
        };
        const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); };
        addEventListener('pointermove', mv); addEventListener('pointerup', up);
      });
      row.appendChild(bar);
      tl.appendChild(row);
    });
    const ph = el('div'); ph.id = 'ph'; tl.appendChild(ph);
    ph.style.left = t * PPS + 'px';
  }

  function select(id) {
    sel = id;
    document.querySelectorAll('.bar').forEach((b) => b.classList.toggle('sel', b.dataset.id === id));
    refreshForms();
  }

  // ---------- Aksi ----------
  function download(blob, name) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  function exportVideo() {
    const types = ['video/mp4;codecs=avc1', 'video/webm;codecs=vp9', 'video/webm'];
    const mime = window.MediaRecorder && types.find((m) => MediaRecorder.isTypeSupported(m));
    if (!mime) { alert('Browser ini tidak mendukung perekaman video dari canvas. Pakai Chrome/Edge/Firefox terbaru.'); return; }
    const chunks = [];
    recorder = new MediaRecorder(canvas.captureStream(30), { mimeType: mime, videoBitsPerSecond: 8e6 });
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = () => {
      const ext = mime.startsWith('video/mp4') ? 'mp4' : 'webm';
      download(new Blob(chunks, { type: mime }), `motion.${ext}`);
      recorder = null; setPlaying(false); $('#btnExport').textContent = 'Ekspor video';
      requestAnimationFrame(tick);
    };
    $('#btnExport').textContent = 'Merekam…';
    t = 0; last = performance.now(); setPlaying(true);
    recorder.start();
  }

  $('#btnPlay').onclick = () => { if (recorder) return; if (t >= scene.duration) t = 0; setPlaying(!playing); };
  $('#btnStop').onclick = () => { if (recorder) return; setPlaying(false); t = 0; draw(); };
  $('#chkSafe').onchange = (e) => { $('#safe').hidden = !e.target.checked; };
  $('#btnExport').onclick = () => { if (!recorder) exportVideo(); };
  $('#btnPng').onclick = () => canvas.toBlob((b) => download(b, 'frame.png'));
  $('#btnSave').onclick = () => download(new Blob([JSON.stringify(scene, null, 2)], { type: 'application/json' }), 'motion-scene.json');
  $('#btnLoad').onclick = () => $('#fileLoad').click();
  $('#fileLoad').onchange = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    try {
      const d = JSON.parse(await f.text());
      if (!Array.isArray(d.layers)) throw new Error('format tidak valid');
      scene = Object.assign(M.newScene(), d);
      scene.layers = d.layers.map((l) => M.newLayer(l));
      sel = scene.layers[0] && scene.layers[0].id; t = 0;
      buildTimeline(); refreshForms(); draw();
    } catch (err) { alert('Gagal membuka file: ' + err.message); }
    e.target.value = '';
  };
  $('#btnAdd').onclick = () => {
    const L = M.newLayer({ start: Math.min(t, scene.duration - 0.5) });
    scene.layers.push(L); sel = L.id; buildTimeline(); refreshForms(); draw();
  };
  $('#btnDup').onclick = () => {
    const c = cur(); if (!c) return;
    const L = M.newLayer(Object.assign({}, c, { id: undefined, start: c.start + 0.3 }));
    scene.layers.push(L); sel = L.id; buildTimeline(); refreshForms(); draw();
  };
  $('#btnDel').onclick = () => {
    scene.layers = scene.layers.filter((l) => l.id !== sel);
    sel = scene.layers.length ? scene.layers[scene.layers.length - 1].id : null;
    buildTimeline(); refreshForms(); draw();
  };
  addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
      e.preventDefault(); $('#btnPlay').click();
    }
  });

  buildTimeline(); refreshForms();
  t = 1.6; draw(); t = 0;
  requestAnimationFrame(tick);
  window.__motion = { get scene() { return scene; }, setT: (v) => { t = v; draw(); } }; // untuk debugging/tes
})();
