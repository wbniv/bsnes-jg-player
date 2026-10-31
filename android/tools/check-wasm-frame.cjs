// Run from the repository root. Host correctness only, not Android hardware proof.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const crypto = require('node:crypto');
const output = process.argv[2] || 'docs/diagnostics/android-repeat-2026-10-31';
fs.mkdirSync(output, { recursive: true });
// The shipped browser-only glue fetches its WASM. Serve those exact local bytes.
const wasm = fs.readFileSync('web/cores/bsnes_jg.wasm');
global.fetch = async () => new Response(wasm, { headers: { 'Content-Type': 'application/wasm' } });
vm.runInThisContext(fs.readFileSync('web/cores/bsnes_jg.js', 'utf8'));
(async () => {
  const module = await BsnesJg();
  const rom = fs.readFileSync('android/fixture/mandel-display.sfc');
  const ptr = module._malloc(rom.length);
  module.HEAPU8.set(rom, ptr);
  if (!module._bjg_load(ptr, rom.length)) throw Error('Core rejected the fixture');
  for (let frame = 1; frame <= 5800; frame++) {
    module._bjg_run();
    if (frame % 1000 === 0) console.error(`Frame ${frame}/5800`);
  }
  const width = module._bjg_video_w(), height = module._bjg_video_h();
  const pitch = module._bjg_video_pitch(), base = module._bjg_video() >>> 2;
  const pixels = Buffer.alloc(256 * 224 * 3);
  for (let y = 0; y < 224; y++) {
    for (let x = 0; x < 256; x++) {
      const color = module.HEAPU32[base + (y + (height >= 232 ? 8 : 0)) * pitch + x * (width >= 512 ? 2 : 1)];
      const index = (y * 256 + x) * 3;
      pixels[index] = color >>> 16;
      pixels[index + 1] = color >>> 8;
      pixels[index + 2] = color;
    }
  }
  const ram = module._bjg_wram() + 0x580;
  const actual = module.HEAPU8[ram] | module.HEAPU8[ram + 1] << 8;
  const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
  fs.writeFileSync(path.join(output, 'wasm-5800.rgb'), pixels);
  const result = { frame: 5800, wram: actual, expected: 0x204f, width, height, pitch,
    wasmSha256: sha(wasm), romSha256: sha(rom), rgbSha256: sha(pixels), scope: 'host' };
  fs.writeFileSync(path.join(output, 'host-wasm-run.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  if (actual !== 0x204f) process.exitCode = 1;
})().catch(error => { console.error(error.message); process.exitCode = 1; });
