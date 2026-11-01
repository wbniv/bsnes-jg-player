// Helpers for library-ui.test.mjs: the published catalog fixture, synthetic
// catalog builders, the Playwright loader and a page launcher that serves the
// real library assets from android/app/src/main/assets/.
//
// Nothing here writes to disk: every request the page makes is answered from
// memory by Playwright's request interception, on a made-up origin.

import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const ASSETS = fileURLToPath(new URL("../app/src/main/assets/", import.meta.url));
const ORIGIN = "http://library.test";

export const CATEGORY_LABELS = {
  bignums: "Big Numbers", algorithms: "Algorithms & Data", rendering: "Rendering & Graphics",
  signals: "Signals & Audio", motion: "Motion & Curves", ciphers: "Ciphers & Bit Tricks",
  video: "Video Playback", cartridge: "Cartridge & Mapping Tests", physics: "Physics & Simulation",
  fractals: "Fractals", classics: "Games & Classics", cellular: "Cellular Automata",
};

// The 152 published ROMs in gallery order, from sync-published-library.py's
// library.json (snapshot 2026-11-01): [slug, title, category, mode7, interactive,
// compilerBug, size]. Only the fields library.js reads are kept.
export const PUBLISHED = [
  ["ovmatrix", "Overflow Family Matrix", "bignums", 0, 0, 0, 32768],
  ["byvaledge", "By-Value Boundary Trio", "algorithms", 0, 0, 1, 32768],
  ["jtsparse", "Sparse Switch Ladder", "algorithms", 0, 0, 0, 32768],
  ["jtedge", "Jump-Table Boundary Sweep", "algorithms", 0, 0, 0, 32768],
  ["vlanest", "Nested VLA Pyramid", "algorithms", 0, 0, 0, 32768],
  ["trapguard", "Unreachable Sentinel", "algorithms", 0, 0, 0, 32768],
  ["packrec", "Unaligned Record Reader", "algorithms", 0, 0, 0, 32768],
  ["strcmprace", "Lexicographic Race", "algorithms", 0, 0, 0, 32768],
  ["bsearchviz", "Bisection Oracle", "algorithms", 0, 0, 0, 32768],
  ["dblbridge", "Precision Bridge", "bignums", 0, 0, 0, 65536],
  ["bigbyval", "Affine Stage Pipeline", "rendering", 0, 0, 0, 32768],
  ["borrowov", "Reservoir Ladder", "algorithms", 0, 0, 0, 32768],
  ["vlastack", "Run-Length Scanline Decoder", "rendering", 0, 0, 0, 32768],
  ["jt256", "ISA-256 Bytecode Machine", "algorithms", 0, 0, 0, 32768],
  ["dpbank", "Bank/Direct-Page Windows", "signals", 0, 0, 0, 32768],
  ["irqgate", "IRQ Gate", "signals", 0, 0, 0, 32768],
  ["retryjmp", "Retry-On-Fault Ladder", "algorithms", 0, 0, 1, 32768],
  ["csrjmp", "Callee-Saved Restore Curve", "motion", 0, 0, 0, 32768],
  ["backtrack", "Backtracking Solver", "algorithms", 0, 0, 1, 32768],
  ["brkcop", "Software Vectors", "signals", 0, 0, 1, 32768],
  ["farptrcmp", "Far-Pointer Order Shuffle", "algorithms", 0, 0, 0, 524288],
  ["bankwalk", "64K Bank-Boundary Walk", "signals", 0, 0, 0, 524288],
  ["modethread", "Threaded Mode Interpreter", "algorithms", 0, 0, 0, 32768],
  ["isrbracket", "Mid-Bracket NMI Tunnel", "signals", 0, 0, 0, 32768],
  ["llabs64", "Seismograph Absolute Trace", "signals", 0, 0, 0, 32768],
  ["shift64seam", "64-Bit Limb-Seam Barrel", "ciphers", 0, 0, 0, 32768],
  ["bitboard64", "Bitboard Knight Tour", "algorithms", 0, 0, 0, 32768],
  ["farspill", "Far-Pointer Spill Funnel", "signals", 0, 0, 0, 65536],
  ["absdiff", "Motion-Detect Difference Field", "signals", 0, 0, 0, 32768],
  ["asmisland", "Inline-Asm Island", "signals", 0, 0, 0, 32768],
  ["mixedwidth", "Split-Personality Link", "signals", 0, 0, 0, 32768],
  ["nmitally", "VBlank Interrupt Tally", "signals", 0, 0, 1, 32768],
  ["apollo-daylight", "Apollo 11 Daylight Launch", "video", 1, 0, 0, 4194304],
  ["seamdemo", "Seam Demo — Three-Act Boundary Cartridge", "cartridge", 0, 0, 1, 6291456],
  ["svx2-fastrom-video", "SVX2 60 FPS FastROM Video", "video", 1, 1, 0, 8388608],
  ["cartsize-exhirom-8m", "ExHiROM 64 Mbit Cartridge Test", "cartridge", 0, 0, 0, 8388608],
  ["cartsize-exhirom-6m", "ExHiROM 48 Mbit Cartridge Test", "cartridge", 0, 0, 0, 6291456],
  ["cartsize-hirom-4m", "HiROM 32 Mbit Cartridge Test", "cartridge", 0, 0, 0, 4194304],
  ["cardioid", "Times-table Cardioid", "motion", 0, 0, 0, 32768],
  ["tea", "TEA Cipher Avalanche", "ciphers", 0, 0, 0, 32768],
  ["hilbert", "Hilbert Curve", "motion", 0, 0, 0, 32768],
  ["fft", "FFT Spectrum Analyser", "signals", 0, 0, 0, 32768],
  ["vaprintf", "VA_ARG Formatter", "motion", 0, 0, 0, 32768],
  ["bhut", "Barnes-Hut Galaxy", "physics", 0, 0, 0, 32768],
  ["fn-plot", "Function Plotter", "fractals", 0, 0, 0, 32768],
  ["lsystem", "L-System Plant", "fractals", 0, 0, 1, 32768],
  ["truchet", "Truchet · Packed Bitfields", "ciphers", 0, 0, 0, 32768],
  ["turtle-vm", "Bytecode-VM Turtle", "classics", 0, 0, 0, 32768],
  ["boids", "Boids Flock", "physics", 0, 0, 0, 32768],
  ["avalanche", "64-Bit Avalanche", "bignums", 1, 0, 0, 32768],
  ["mandel-double", "Double-Precision Mandelbrot", "fractals", 1, 0, 0, 65536],
  ["mandel-float", "Soft-Float Mandelbrot", "fractals", 1, 0, 0, 32768],
  ["burning-ship", "Burning Ship Fractal", "fractals", 0, 0, 0, 32768],
  ["raycaster", "Raycaster Maze", "physics", 0, 0, 0, 32768],
  ["julia", "Julia Set Explorer", "fractals", 1, 0, 0, 32768],
  ["harmonograph", "Lissajous Harmonograph", "motion", 0, 0, 0, 32768],
  ["life", "Conway's Game of Life", "cellular", 0, 0, 0, 32768],
  ["epicycles", "Fourier Epicycles", "motion", 0, 0, 0, 32768],
  ["maze", "Maze Generate + Solve", "algorithms", 0, 0, 0, 32768],
  ["sort-race", "Sorting Race", "algorithms", 0, 0, 0, 32768],
  ["doom-fire", "Doom Fire", "cellular", 0, 0, 0, 32768],
  ["cordic", "CORDIC Rotator", "motion", 0, 0, 0, 32768],
  ["buddhabrot", "Buddhabrot", "fractals", 1, 0, 0, 32768],
  ["newton", "Newton's Fractal", "fractals", 0, 0, 0, 32768],
  ["factorial", "Bignum Factorial", "bignums", 0, 0, 0, 32768],
  ["rdiff", "Reaction-Diffusion", "cellular", 0, 0, 0, 32768],
  ["n-body", "N-body Orbits", "physics", 0, 0, 0, 32768],
  ["1d-ca", "1-D Cellular Automaton", "cellular", 0, 1, 0, 32768],
  ["double-pendulum", "Double Pendulum (Chaos)", "physics", 0, 0, 0, 32768],
  ["spigot", "π Spigot + Monte-Carlo", "bignums", 0, 0, 0, 32768],
  ["3d-wireframe", "Wireframe 3-D Solid", "physics", 0, 1, 0, 32768],
  ["spirograph", "Spirograph", "motion", 0, 1, 0, 32768],
  ["space-invaders", "Space Invaders", "classics", 0, 1, 0, 32768],
  ["blossom", "Blossom", "classics", 1, 1, 1, 32768],
  ["bf-vm", "Brainfuck Threaded-Code VM", "classics", 0, 0, 0, 32768],
  ["hdr-bloom", "HDR Additive Bloom", "rendering", 0, 0, 0, 32768],
  ["iir-scope", "IIR Resonant-Filter Scope", "signals", 0, 0, 0, 32768],
  ["polyfill", "Polygon Scanline Fill (VLA)", "rendering", 0, 0, 0, 32768],
  ["seqvm", "Step-Sequencer VM (Sparse Switch)", "signals", 0, 0, 1, 32768],
  ["divclock", "Division Clock + Odometer", "classics", 0, 0, 0, 32768],
  ["crctex", "CRC32 Hash-Marble Texture", "rendering", 0, 0, 0, 32768],
  ["poolfx", "Free-List Pool Allocator", "classics", 0, 0, 0, 32768],
  ["duff", "Duff Dissolve", "algorithms", 0, 0, 0, 32768],
  ["sodo", "Signed 64-bit Odometer", "bignums", 0, 0, 0, 32768],
  ["metaball", "Type-Pun Metaballs", "rendering", 0, 0, 0, 32768],
  ["qsortviz", "qsort Sort Visualizer", "algorithms", 0, 0, 1, 32768],
  ["nrecip", "Newton Reciprocal Floor", "rendering", 0, 0, 0, 32768],
  ["lzdec", "LZ77 Decompress Reveal", "algorithms", 0, 0, 0, 32768],
  ["cgrade", "Many-Arg Color Grade", "rendering", 0, 0, 0, 32768],
  ["critters", "Protothread Critters", "classics", 0, 0, 0, 32768],
  ["disbits", "Cross-Byte Bitfields", "ciphers", 0, 0, 0, 32768],
  ["bitcensus", "Bit-Census Field", "ciphers", 0, 0, 0, 32768],
  ["funnelkal", "Funnel-Shift Kaleidoscope", "rendering", 0, 0, 0, 32768],
  ["bitshuffle", "Perfect-Shuffle Transition", "ciphers", 0, 0, 0, 32768],
  ["gf256", "GF(2⁸) Galois Field", "ciphers", 0, 0, 0, 32768],
  ["rotozoom", "Rotozoom", "rendering", 0, 0, 0, 32768],
  ["medfilt", "Median Denoiser", "rendering", 0, 0, 0, 32768],
  ["domcol", "Domain Colouring", "fractals", 0, 0, 0, 32768],
  ["cosmzoom", "Cosmic Zoom Ruler", "bignums", 0, 0, 0, 32768],
  ["multibase", "Multi-Base Clock", "bignums", 0, 0, 0, 32768],
  ["dhmix", "Diffie-Hellman Colour-Mixer", "bignums", 0, 0, 1, 32768],
  ["percol", "Union-Find Percolation", "cellular", 0, 0, 0, 32768],
  ["fenwick", "Fenwick Tree", "algorithms", 0, 0, 0, 32768],
  ["radix", "Radix Sort", "algorithms", 0, 0, 0, 32768],
  ["hull", "Convex Hull", "algorithms", 0, 0, 0, 32768],
  ["editdist", "Edit-Distance DP", "algorithms", 0, 0, 0, 32768],
  ["huffman", "Huffman Decode", "algorithms", 0, 0, 0, 32768],
  ["perlin", "Perlin Noise", "rendering", 0, 0, 0, 32768],
  ["gouraud", "Gouraud Triangle", "rendering", 0, 0, 0, 32768],
  ["dither", "Floyd-Steinberg Dither", "rendering", 0, 0, 0, 32768],
  ["msquares", "Marching Squares", "cellular", 0, 0, 0, 32768],
  ["grid3d", "3-D Grid Voxel Life", "cellular", 0, 0, 0, 32768],
  ["fabsridge", "Fabs Ridgeline", "rendering", 0, 0, 0, 32768],
  ["compass", "Copysign Compass", "motion", 0, 0, 0, 32768],
  ["speedcap", "Fmin/Fmax Speed Cap", "physics", 0, 0, 0, 32768],
  ["truncstair", "Truncation Staircase", "algorithms", 0, 0, 0, 32768],
  ["montorbit", "Montgomery Orbit", "ciphers", 0, 0, 0, 32768],
  ["ulam", "Ulam Prime Sieve", "algorithms", 0, 0, 0, 32768],
  ["rangecode", "Range Coder", "algorithms", 0, 0, 0, 32768],
  ["sobel", "Sobelscope", "rendering", 0, 0, 0, 32768],
  ["dctbloom", "DCT Bloom", "signals", 0, 0, 0, 32768],
  ["adpcm", "ADPCM Waverider", "signals", 0, 0, 0, 32768],
  ["scopeguard", "Scope-Guard Ripple Tank", "algorithms", 0, 0, 0, 32768],
  ["matcascade", "Matrix Cascade", "rendering", 0, 0, 0, 32768],
  ["plyoracle", "PlyOracle", "classics", 0, 0, 0, 32768],
  ["smulorbit", "Signed Multiply-Overflow Orbit", "motion", 0, 0, 0, 32768],
  ["satcomet", "Saturating Comet Trails", "motion", 0, 0, 0, 32768],
  ["rotkal", "Rotate-Register Kaleidoscope", "rendering", 0, 0, 0, 32768],
  ["satcast", "Saturating-Cast Kaleidoscope", "rendering", 0, 0, 0, 32768],
  ["sbitfld", "Signed-Bitfield Terrain", "algorithms", 0, 0, 0, 32768],
  ["mvscrl", "Memmove Scroll Slabs", "algorithms", 0, 0, 0, 32768],
  ["borrowlad", "Borrow-Ladder Odometer", "bignums", 0, 0, 0, 32768],
  ["mulov64", "64-bit Multiply-Overflow", "bignums", 0, 0, 0, 32768],
  ["modexp256", "256-bit Modular Exponentiation", "algorithms", 0, 0, 0, 32768],
  ["pcooker", "Pressure-Cooker Fixed-Point Evaluator", "algorithms", 0, 0, 0, 32768],
  ["oddmask", "Odd-Width Mask Sculptor", "algorithms", 0, 0, 0, 32768],
  ["keycmp64", "64-bit Multi-Key Record Sort", "algorithms", 0, 0, 0, 32768],
  ["trimerge", "Three-Way Merge Diff", "algorithms", 0, 0, 0, 32768],
  ["ucmprank", "Unsigned Rank Percentile Field", "algorithms", 0, 0, 0, 32768],
  ["ropeedit", "Gap-Buffer Rope Editor", "algorithms", 0, 0, 0, 32768],
  ["permscat", "Gather-Scatter Permutation", "algorithms", 0, 0, 0, 32768],
  ["rotslab", "In-Place Block Rotate", "algorithms", 0, 0, 0, 32768],
  ["ovmove", "Overlap-Move Mosaic", "algorithms", 0, 0, 0, 32768],
  ["spaceship", "Width-Sweep Sort Gallery", "algorithms", 0, 0, 0, 32768],
  ["uarteye", "Bit-Banged UART Eye", "ciphers", 0, 0, 0, 32768],
  ["bitweave", "Serial Bit-Reversal Weave", "ciphers", 0, 0, 0, 32768],
  ["lfsr2", "Dual-LFSR Scrambler", "ciphers", 0, 0, 0, 32768],
  ["crcwall", "Bit-Serial CRC Wall", "ciphers", 0, 0, 1, 32768],
  ["cpu6502", "6502 CPU Simulator", "classics", 0, 0, 0, 32768],
  ["mandel-oop", "Mode 7 Mandelbrot (OOP)", "fractals", 1, 0, 0, 32768],
  ["mandel-display", "Mode 7 Mandelbrot", "fractals", 1, 0, 0, 32768],
  ["lzss-gallery", "LZSS Mode 7 Gallery", "algorithms", 1, 0, 1, 1048576],
].map(([slug, title, category, mode7, interactive, compilerBug, size], order) => ({
  slug, filename: `${slug}.sfc`, title,
  desc: `${title}: published description.`,
  keys: interactive ? "D-pad steers" : "Self-running — no controls",
  compilerBug: !!compilerBug, interactive: !!interactive,
  category, categoryLabel: CATEGORY_LABELS[category],
  displayMode: mode7 ? 7 : null, order, size, card: `cards/${slug}.png`,
}));

// N records built from the published ones, like the plan's `?catalog=synthetic-N`.
// Past 152 the published list repeats with a numbered suffix so slugs stay unique.
export function synthetic(n) {
  return Array.from({ length: n }, (_, i) => {
    const base = PUBLISHED[i % PUBLISHED.length], lap = Math.floor(i / PUBLISHED.length);
    if (!lap) return { ...base };
    const slug = `${base.slug}-${lap + 1}`;
    return { ...base, slug, filename: `${slug}.sfc`, title: `${base.title} #${lap + 1}`, card: `cards/${slug}.png` };
  });
}

// N records, every one in a single category (Fractals).
export function singleCategory(n) {
  return synthetic(n).map((r) => ({ ...r, category: "fractals", categoryLabel: "Fractals" }));
}

export const bySlug = (...slugs) => slugs.map((s) => {
  const r = PUBLISHED.find((x) => x.slug === s);
  if (!r) throw new Error(`no published ROM ${s}`);
  return { ...r };
});

// playwright-core: an installed npm package if there is one, otherwise the copy
// bundled with the Python `playwright` package (its driver ships playwright-core
// for Node). PLAYWRIGHT_CORE may name the package directory explicitly.
export async function loadChromium() {
  const candidates = [];
  if (process.env.PLAYWRIGHT_CORE) candidates.push(path.join(process.env.PLAYWRIGHT_CORE, "index.mjs"));
  for (const name of ["playwright-core", "playwright"]) {
    try { return (await import(name)).chromium; } catch { /* try the next one */ }
  }
  try {
    const dir = execFileSync("python3", ["-c", "import os, playwright; print(os.path.dirname(playwright.__file__))"],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    candidates.push(path.join(dir, "driver", "package", "index.mjs"));
  } catch { /* no Python playwright */ }
  for (const file of candidates) {
    if (existsSync(file)) return (await import(pathToFileURL(file).href)).chromium;
  }
  throw new Error("playwright-core not found: install the npm package, or Python `playwright`, or set PLAYWRIGHT_CORE");
}

const PNG_1PX = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");

// Stands in for engine-adapter.js. It has the shape of web/app.js's BJGTV
// (currentRom included) and records every engine call in window.__calls.
// window.__playMode: "ok" (default) resolves true, "pending" never settles.
const ENGINE_STUB = `(function(){
  var current = "", calls = window.__calls = window.__calls || [];
  var api = {
    onReady: null, onBackground: null, onVerification: null, lastLoadFailure: null,
    isReady: function(){ return true; },
    hasRom: function(){ return !!current; },
    currentRom: function(){ return current; },
    canVerify: function(){ return false; },
    play: function(slug){
      calls.push(["play", slug]);
      if (window.__playMode === "pending") return new Promise(function(){});
      current = slug; return Promise.resolve(true);
    },
    pause: function(){ calls.push(["pause"]); },
    resume: function(){ calls.push(["resume", current]); },
    restart: function(){ calls.push(["restart"]); return Promise.resolve(true); },
    showLibrary: function(){}, verify: function(){}, cancelVerification: function(){}
  };
  window.BJGTV = api;
})();`;

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png" };

// Opens the real library page at 1920x1080 with `roms` as roms/library.json and
// `prefs` as what BjgAndroid.getPrefs() returns. Resolves once the catalog has
// rendered and the initial focus has been placed.
export async function openLibrary(browser, { roms, prefs = {}, playMode = "ok" } = {}) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.addInitScript(({ prefs, playMode }) => {
    window.__calls = [];
    window.__prefWrites = [];
    window.__playMode = playMode;
    window.BjgAndroid = {
      getPrefs: () => JSON.stringify(prefs),
      setPrefs: (json) => { window.__prefWrites.push(JSON.parse(json)); },
      getAppVersion: () => "0.0.0-test",
      exitApp: () => { window.__calls.push(["exitApp"]); },
      pauseGame() {}, resumeGame() {}, showLibrary() {},
    };
  }, { prefs, playMode });
  const catalog = JSON.stringify({ schemaVersion: 1, source: "library-ui.test.mjs", roms });
  await page.route(`${ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const rel = url.pathname === "/" ? "index.html" : decodeURIComponent(url.pathname.slice(1));
    if (rel === "roms/library.json") return route.fulfill({ contentType: "application/json", body: catalog });
    if (rel.startsWith("roms/cards/")) return route.fulfill({ contentType: "image/png", body: PNG_1PX });
    if (rel === "engine-adapter.js") return route.fulfill({ contentType: "text/javascript", body: ENGINE_STUB });
    const file = path.join(ASSETS, rel);
    if (!file.startsWith(ASSETS) || !existsSync(file)) return route.fulfill({ status: 404, body: "" });
    return route.fulfill({ contentType: TYPES[path.extname(file)] || "application/octet-stream", body: await readFile(file) });
  });
  await page.goto(`${ORIGIN}/index.html`);
  await page.waitForFunction(() => document.getElementById("catalog-count").textContent !== "");
  await settle(page);
  return { page, errors, close: () => context.close() };
}

// Two animation frames: library.js moves focus in requestAnimationFrame.
export const settle = (page) => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));

export async function press(page, key, times = 1) {
  for (let i = 0; i < times; i++) { await page.keyboard.press(key); await settle(page); }
}

// What the test needs to know about the page, in one round trip.
export const state = (page) => page.evaluate(() => {
  const a = document.activeElement, vis = (el) => !!el && el.checkVisibility();
  const rows = Array.from(document.querySelectorAll("#rom-list .rom"));
  return {
    focusId: a && a.id, focusClass: a && a.className, focusIndex: a && a.dataset ? a.dataset.index : undefined,
    focusText: a && a.textContent,
    rows: rows.length,
    rowTitles: rows.map((r) => r.querySelector("strong").textContent),
    rowTags: rows.map((r) => Array.from(r.querySelectorAll(".tag")).map((t) => t.textContent)),
    rowStars: rows.map((r) => !!r.querySelector(".star")),
    libraryVisible: vis(document.getElementById("library")),
    listVisible: vis(document.getElementById("rom-list")),
    previewVisible: vis(document.getElementById("preview")),
    filtersVisible: vis(document.getElementById("filters")),
    searchVisible: vis(document.getElementById("search")),
    luckyVisible: vis(document.getElementById("lucky")),
    luckyDisabled: document.getElementById("lucky").disabled,
    emptyVisible: vis(document.getElementById("empty")),
    emptyText: document.getElementById("empty").innerText,
    searchAllVisible: vis(document.getElementById("search-all")),
    searchAllText: document.getElementById("search-all").textContent,
    activeChip: document.querySelector("#filters .chip.active")?.dataset.key,
    chipCount: document.querySelectorAll("#filters .chip").length,
    playLabel: document.getElementById("play").textContent,
    title: document.getElementById("title").textContent,
    playing: document.body.classList.contains("playing"),
    calls: window.__calls.slice(),
    prefWrites: window.__prefWrites.slice(),
  };
});
