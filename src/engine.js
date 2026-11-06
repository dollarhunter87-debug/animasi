/* Motion engine: easing, preset teks kinetik, layout, dan renderer Canvas.
 * Murni (tanpa DOM) supaya bisa dites di Node. Global: window.Motion / module.exports. */
(function (root) {
  'use strict';

  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  // Angka acak deterministik per indeks (animasi sama setiap kali diputar/diekspor)
  const rnd = (i, s = 0) => {
    const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453;
    return x - Math.floor(x);
  };

  const outBounce = (t) => {
    const n = 7.5625, d = 2.75;
    if (t < 1 / d) return n * t * t;
    if (t < 2 / d) { t -= 1.5 / d; return n * t * t + 0.75; }
    if (t < 2.5 / d) { t -= 2.25 / d; return n * t * t + 0.9375; }
    t -= 2.625 / d; return n * t * t + 0.984375;
  };

  const EASINGS = {
    linear: (t) => t,
    inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    outCubic: (t) => 1 - Math.pow(1 - t, 3),
    outExpo: (t) => 1 - Math.pow(2, -10 * t),
    outBack: (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
    outElastic: (t) => Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * (2 * Math.PI / 3)) + 1,
    outBounce,
    spring: (t) => 1 - Math.exp(-6 * t) * Math.cos(t * 10),
    step: (t) => (t > 0 ? 1 : 0),
  };

  function ease(name, t) {
    t = clamp(t);
    if (t >= 1) return 1;
    return (EASINGS[name] || EASINGS.linear)(t);
  }

  const IDENT = { x: 0, y: 0, sx: 1, sy: 1, rot: 0, op: 1 };

  // `from` = keadaan awal (x/y dalam satuan em, rot dalam radian). unit = per char | word | line.
  const PRESETS = {
    pop:        { label: 'Pop',                unit: 'word', ease: 'outBack',    from: () => ({ sx: 0, sy: 0, op: 0 }) },
    bounceUp:   { label: 'Bounce naik',        unit: 'char', ease: 'outBounce',  from: () => ({ y: 1.3, op: 0 }) },
    dropIn:     { label: 'Jatuh + miring',     unit: 'char', ease: 'outBounce',  from: (i) => ({ y: -5, rot: (rnd(i) - 0.5) * 1.4, op: 0 }) },
    spinIn:     { label: 'Putar masuk',        unit: 'char', ease: 'outBack',    from: () => ({ rot: -Math.PI, sx: 0, sy: 0, op: 0 }) },
    stretch:    { label: 'Stretch kenyal',     unit: 'char', ease: 'outElastic', from: () => ({ sx: 0.2, sy: 2.4, op: 0 }) },
    slideLeft:  { label: 'Slide dari kiri',    unit: 'word', ease: 'outCubic',   from: () => ({ x: -4, op: 0 }) },
    slideRight: { label: 'Slide dari kanan',   unit: 'word', ease: 'outCubic',   from: () => ({ x: 4, op: 0 }) },
    zoomSlam:   { label: 'Zoom slam',          unit: 'line', ease: 'outExpo',    from: () => ({ sx: 4, sy: 4, op: 0 }) },
    typewriter: { label: 'Typewriter',         unit: 'char', ease: 'step',       from: () => ({ op: 0 }) },
    fade:       { label: 'Fade',               unit: 'line', ease: 'inOutCubic', from: () => ({ op: 0 }) },
  };

  const LOOPS = { none: 'Tanpa loop', pulse: 'Pulse', wiggle: 'Wiggle', float: 'Float' };

  let _id = 0;
  function newLayer(p) {
    return Object.assign({
      id: 'L' + (++_id) + '_' + Math.random().toString(36).slice(2, 6),
      text: 'TEKS BARU', start: 0, dur: 2.5,
      preset: 'pop', unit: 'auto', ease: '', // ease kosong = bawaan preset
      inDur: 0.5, stagger: 0.08, out: true, loop: 'none',
      font: 'Impact', weight: 800, fontSize: 150, x: 0.5, y: 0.5,
      color: '#ffffff', strokeColor: '#000000', strokeWidth: 0,
      glowColor: '#00e5ff', glow: 0,
    }, p || {});
  }

  function newScene() {
    return { width: 1080, height: 1920, duration: 8, bpm: 120, bg1: '#150b3a', bg2: '#4a1d8f', layers: [] };
  }

  // Keadaan transform satu unit (huruf/kata/baris) pada waktu t (detik, waktu scene).
  function unitState(L, t, i, n) {
    const P = PRESETS[L.preset] || PRESETS.fade;
    const easeName = L.ease || P.ease;
    const inDur = Math.max(0.01, L.inDur);
    const st = L.stagger || 0;
    const local = t - L.start;
    const f = Object.assign({}, IDENT, P.from(i, n));
    const p = clamp((local - i * st) / inDur);
    const q = L.out ? clamp((local - (L.dur - inDur - (n - 1 - i) * st)) / inDur) : 0;
    const s = {};
    for (const k in IDENT) {
      s[k] = q > 0 ? lerp(IDENT[k], f[k], ease(easeName, q)) : lerp(f[k], IDENT[k], ease(easeName, p));
    }
    const lt = local + i * 0.15;
    if (L.loop === 'pulse') { const k = 1 + 0.05 * Math.sin(lt * Math.PI * 4); s.sx *= k; s.sy *= k; }
    else if (L.loop === 'wiggle') s.rot += 0.05 * Math.sin(lt * 9);
    else if (L.loop === 'float') s.y += 0.1 * Math.sin(lt * 3);
    s.op = clamp(s.op);
    return s;
  }

  function layout(ctx, L, W, H) {
    const size = L.fontSize;
    ctx.font = `${L.weight || 800} ${size}px ${L.font}`;
    const maxW = W * 0.88;
    const lines = [];
    for (const para of String(L.text).split('\n')) {
      let cur = '';
      for (const w of para.split(/\s+/).filter(Boolean)) {
        const test = cur ? cur + ' ' + w : w;
        if (cur && ctx.measureText(test).width > maxW) { lines.push(cur); cur = w; } else cur = test;
      }
      lines.push(cur);
    }
    const mode = L.unit && L.unit !== 'auto' ? L.unit : (PRESETS[L.preset] || PRESETS.fade).unit;
    const lh = size * 1.2;
    const top = L.y * H - (lines.length * lh) / 2 + lh / 2;
    const units = [];
    lines.forEach((line, li) => {
      const lw = ctx.measureText(line).width;
      const cy = top + li * lh;
      const push = (a, b) => {
        const pre = ctx.measureText(line.slice(0, a)).width;
        const w = ctx.measureText(line.slice(a, b)).width;
        units.push({ text: line.slice(a, b), cx: L.x * W - lw / 2 + pre + w / 2, cy });
      };
      if (mode === 'line') { if (line) push(0, line.length); }
      else if (mode === 'word') { const re = /\S+/g; let m; while ((m = re.exec(line))) push(m.index, m.index + m[0].length); }
      else for (let k = 0; k < line.length; k++) if (line[k] !== ' ') push(k, k + 1);
    });
    return { units, size };
  }

  function drawLayer(ctx, L, t, W, H) {
    const local = t - L.start;
    if (local < 0 || local > L.dur) return;
    const { units, size } = layout(ctx, L, W, H);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineJoin = 'round';
    units.forEach((u, i) => {
      const s = unitState(L, t, i, units.length);
      if (s.op <= 0.001) return;
      ctx.save();
      ctx.translate(u.cx + s.x * size, u.cy + s.y * size);
      ctx.rotate(s.rot);
      ctx.scale(s.sx, s.sy);
      ctx.globalAlpha = s.op;
      if (L.glow > 0) { ctx.shadowColor = L.glowColor; ctx.shadowBlur = L.glow; }
      if (L.strokeWidth > 0) {
        ctx.lineWidth = L.strokeWidth * 2;
        ctx.strokeStyle = L.strokeColor;
        ctx.strokeText(u.text, 0, 0);
      }
      ctx.fillStyle = L.color;
      ctx.fillText(u.text, 0, 0);
      ctx.restore();
    });
  }

  function renderScene(ctx, scene, t) {
    const { width: W, height: H } = scene;
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, scene.bg1);
    g.addColorStop(1, scene.bg2);
    ctx.globalAlpha = 1;
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    for (const L of scene.layers) drawLayer(ctx, L, t, W, H);
  }

  const api = { EASINGS, ease, PRESETS, LOOPS, IDENT, newLayer, newScene, unitState, layout, renderScene, clamp };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Motion = api;
})(typeof window !== 'undefined' ? window : globalThis);
