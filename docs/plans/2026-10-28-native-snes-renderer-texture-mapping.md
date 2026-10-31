# Native SNES renderer: preserve the full framebuffer in responsive layouts

## Problem

The responsive layout computes a 4:3 game rectangle and places metadata and performance panels in the remaining device space. The native renderer then uses that rectangle’s clip-space vertex positions for **both** screen placement and texture coordinates:

```glsl
gl_Position = vec4(p, 0., 1.);
uv = (p + 1.) * .5;
```

Here `p` is already inset to leave the gutters. Therefore `uv` does not span `[0, 1]` when the game rectangle does not fill the screen. The renderer samples only part of the 256×224 framebuffer. How much it crops depends on the fitted rectangle, so the visible SNES image changes between device shapes and orientations. The attached landscape example shows the title text cut at both edges.

The problem is in the native texture mapping. The 4:3 layout rectangle and its gutter calculations are still the intended geometry.

![Before: the inset game rectangle is reused as texture coordinates, cropping the framebuffer](assets/native-renderer-viewport/before-cropped-texture.svg)

## Correction

Keep clip-space positions for placing the quad. Pass the game rectangle’s clip-space bounds separately, then normalize each vertex position relative to those bounds:

```glsl
gl_Position = vec4(p, 0., 1.);
uv = (p - bounds.xy) / bounds.zw;
```

The native renderer supplies `bounds = (left, bottom, right - left, top - bottom)`. At the game rectangle’s left, right, bottom, and top edges, `uv` is exactly `0` or `1`, independent of the rectangle’s location or size. The fragment shader’s existing vertical flip remains unchanged.

![After: the entire framebuffer maps into the fitted 4:3 game rectangle in either orientation](assets/native-renderer-viewport/after-full-texture.svg)

The source framebuffer remains 256×224 samples (8:7 sample grid). The 4:3 game rectangle applies the horizontal expansion used for the traditional SNES television presentation. The fix changes which framebuffer samples are shown; it does not change the requested display aspect ratio.

## Implementation status

The bounds-normalized shader is implemented in [MainActivity.java](../../android/app/src/main/java/org/bsnesjg/tv/MainActivity.java). The 31 October coordinator checks recovered the earlier Pixel blocker and verified the corrected native engine on Pixel and Cast1: WRAM `0x204F` at frame 5800 and zero differing pixels against the canonical 256×224 reference.

Those checks also found and fixed an independent native color-channel error: the packed `0x00RRGGBB` framebuffer had been copied as BGR. Before the correction 38,718 pixels differed; after it both ARM64 and ARMv7 passed. The reference check now runs inside the emulation-step loop, so a multi-step render callback cannot skip frame 5800.

A dedicated native layout benchmark freezes at frame 5800. Pixel portrait job `J‑ccf4f03cf386` produced a 1008×756 game rectangle (exactly 4:3); sampling all 57,344 source-pixel centers from the actual hardware screenshot produced zero differences. Landscape job `J‑ae4268b0701b` also matched all 57,344 source pixels, in a rasterized 1345×1008 rectangle (one pixel of width rounding). Both captures report no OpenGL error and preserve the complete framebuffer. The captures and full job ledger are in the [31 October report](../performance/2026-10-31/comparison.html). Hardware screenshots, raw logs and downloaded coordinator receipts remain under `docs/diagnostics/android-repeat-2026-10-31/`.

## Validation

- Compare captures at the same deterministic SNES frame in portrait and landscape. The complete 256×224 source must be visible in both; only the rectangle’s position and scale may change.
- Confirm the fitted game rectangle remains 4:3, with no gutter overlap or edge crop.
- Capture on Pixel after coordinator recovery and compare the title screen against the complete source frame.
- Compare native emulation and draw metrics before and after. This adds one `glUniform4f` update and a few vertex-shader arithmetic operations per draw; it does not add framebuffer copies or fragment work.

