# Phase 1 ROM fixture

This directory freezes the single ROM used by the Android TV Phase 1 app. The app build consumes these files only; it does not read the sibling checkout at build time.

| Input | Original location | SHA-256 |
|---|---|---|
| ROM | `../llvm-mos-65816/build/mandel-display.sfc` | `6c13c9042ca68be06f42650862ad7e116cc782e3a433ceaf9f760f090b430353` |
| Link map | `../llvm-mos-65816/build/mandel-display.map` | `44ebc8e330f5e70c5723ff90b80e1a55fb53b914c6a4d4d1dc970a933b27c3cb` |

The observed sibling checkout revision at import was `e7301ac712c4f8e88e4197cce4c03c5c45a7124b`. This only identifies the checkout observed during fixture import; it does not prove which source revision produced these already-built ROM bytes.

The map places `corpus_result` at WRAM offset `$0580`; the selected self-check reads two bytes and expects `0x204F` after 5800 frames. The native `jgxcheck` gate passed on these frozen bytes in the sibling LLVM-MOS container:

```text
SMOKE: PASS off=0x580 len=2 got=0x204F (ran 5800 frames, bsnes-jg)
```

Its deterministic entropy-zero, 8-line-overscan-cropped 256×224 reference image is [reference-5800.png](reference-5800.png), SHA-256 `7acaa3825b82b7e61fe641ca950508d58e8aeb0cb2ff7849547d17eacaab4abe`. The Android build checks this hash and the ROM's map-derived offset. A fixture refresh must update ROM, map, reference image and hashes, rerun the native gate, and update the generated app manifest in one reviewed change.
