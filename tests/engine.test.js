const assert = require('assert');
const M = require('../src/engine.js');

// Easing: titik ujung harus tepat 0 dan 1
for (const name of Object.keys(M.EASINGS)) {
  if (name === 'step') continue;
  assert.ok(Math.abs(M.ease(name, 0)) < 1e-6, `${name}(0) harus 0`);
  assert.strictEqual(M.ease(name, 1), 1, `${name}(1) harus 1`);
}
assert.ok(M.ease('outBack', 0.7) > 1, 'outBack harus overshoot');
assert.strictEqual(M.ease('step', 0.01), 1);

// Unit state: sebelum mulai = keadaan awal, setelah masuk = identitas, setelah keluar = awal lagi
const L = M.newLayer({ preset: 'pop', start: 1, dur: 3, inDur: 0.5, stagger: 0, out: true });
let s = M.unitState(L, 1, 0, 1);
assert.ok(Math.abs(s.sx) < 1e-9); assert.ok(s.op < 1e-9);
s = M.unitState(L, 2, 0, 1);
assert.deepStrictEqual([s.sx, s.sy, s.op, s.rot], [1, 1, 1, 0]);
s = M.unitState(L, 4, 0, 1);
assert.ok(Math.abs(s.sx) < 1e-9);

// Stagger: unit kedua mulai belakangan
const T = M.newLayer({ preset: 'typewriter', start: 0, dur: 5, stagger: 0.5, inDur: 0.1 });
assert.strictEqual(M.unitState(T, 0.3, 0, 3).op, 1);
assert.strictEqual(M.unitState(T, 0.3, 1, 3).op, 0);

// Layout dengan ctx palsu: 1 unit per huruf non-spasi, wrap menurut lebar
const fake = { font: '', measureText: (txt) => ({ width: txt.length * 50 }) };
const lay = M.layout(fake, M.newLayer({ text: 'AB CD', preset: 'bounceUp', fontSize: 100 }), 1080, 1920);
assert.strictEqual(lay.units.length, 4);
const wrapped = M.layout(fake, M.newLayer({ text: 'aaaaaaaaaa bbbbbbbbbb', preset: 'fade', fontSize: 100 }), 1080, 1920);
// 21 karakter x 50px = 1050 > 0.88 * 1080 = 950, jadi harus pecah jadi 2 baris
assert.strictEqual(new Set(wrapped.units.map((u) => u.cy)).size, 2, 'teks panjang harus di-wrap');

console.log('engine tests OK');
