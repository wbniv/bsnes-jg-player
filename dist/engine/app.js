/*
 * bsnes-jg-wasm loader — drives our Emscripten build of bsnes-jg 2.1.0 (the exact
 * core the llvm-mos-65816 differential gate trusts). Boots a .sfc, renders the
 * core's framebuffer to a <canvas>, maps the keyboard to an SNES pad, and runs an
 * in-browser fidelity self-check that reproduces the gate's headless WRAM assert.
 *
 * The core module (web/cores/bsnes_jg.js) is built by ./build.sh. No libretro,
 * no EmulatorJS — just Module._bjg_* calls.
 */
(function () {
  "use strict";

  // An embedding page (e.g. the indri.studio inline embed) can point the loader
  // at assets under a base path and pick the boot ROM; defaults reproduce the
  // standalone page (relative paths, the zoom demo).
  var BASE = (window.BJG_BASE || "");
  var DEFAULT_ROM = (window.BJG_DEFAULT_ROM || "mandel-display");

  // Content-hash cache-busting. The page (fresh HTML) injects window.BJG_BUST: a map of
  // relative asset path -> short SHA of that file's bytes. bust() appends "?v=<sha>" so each
  // asset can be cached immutably forever, yet a re-synced file (same filename, new content =
  // new sha) gets a NEW url and is re-fetched — no stale ROM after a deploy. Absent map (older
  // embed) -> plain path, so it still works.
  function bust(path) {
    var b = window.BJG_BUST;
    return BASE + path + (b && b[path] ? "?v=" + b[path] : "");
  }

  // SNES controller bits — must match Bsnes::Input::Gamepad in src/bsnes.hpp.
  var JOY = {
    B: 1 << 15, Y: 1 << 14, Select: 1 << 13, Start: 1 << 12,
    Up: 1 << 11, Down: 1 << 10, Left: 1 << 9, Right: 1 << 8,
    A: 1 << 7, X: 1 << 6, L: 1 << 5, R: 1 << 4
  };
  // Keyboard -> pad. Z/X = B/A, A/S = Y/X (the common SNES-on-keyboard layout).
  var KEYMAP = {
    ArrowUp: JOY.Up, ArrowDown: JOY.Down, ArrowLeft: JOY.Left, ArrowRight: JOY.Right,
    KeyZ: JOY.B, KeyX: JOY.A, KeyA: JOY.Y, KeyS: JOY.X,
    Enter: JOY.Start, ShiftRight: JOY.Select, ShiftLeft: JOY.Select,
    KeyQ: JOY.L, KeyW: JOY.R
  };

  var Module = null;       // the instantiated Emscripten module
  var manifest = null;     // roms/manifest.json
  var current = null;      // current rom id
  var pad = 0;             // port-0 button mask
  var touchRelease = 0;    // timer for a manifest-driven synthetic D-pad tap
  var touchNavPressed = 0; // synthetic bit currently owned by that timer
  var running = false;     // RAF loop active
  var rafId = 0;
  var verification = null; // active, cancellable fidelity run
  var imageData = null;
  var runLabel = "";       // status prefix for the running ROM
  var dimsShown = false;   // whether status already carries WxH
  var revealed = false;    // true once the first non-black live frame has been drawn
                           //  (until then the baked preview stays on the canvas)
  var tvMetrics = {
    bootAt: performance.now(), lastRafAt: null,
    core: [], canvas: [], draw: [], raf: [], drawSubmissions: 0, frames: 0, romFrames: 0,
    firstLiveFrame: false, fidelityReady: false, romRun: 0,
    frameCallbacks: 0, windowStartAt: performance.now(), maxBacklog: 0, lastBacklogReport: 0
  };
  // SNES NTSC frame rate. Advance by elapsed monotonic time instead of assuming
  // that every TV display refresh is exactly 60 Hz.
  var EMULATION_HZ = 60.0988;
  var MAX_STEPS_PER_CALLBACK = 4;
  var emulationCredit = 0;
  var lastEmulationTimestamp = null;
  var tvFrameClock = window.BJG_TV_MODE && window.BJGFrameScheduler ?
    window.BJGFrameScheduler.create(EMULATION_HZ, MAX_STEPS_PER_CALLBACK) : null;

  var canvas = document.getElementById("screen");
  var ctx = canvas.getContext("2d", { alpha: false });
  var statusEl = document.getElementById("status");
  var checkEl = document.getElementById("checkresult");
  var bannerEl = document.getElementById("banner");

  function status(msg) { if (statusEl) statusEl.textContent = msg; }
  function setLoading(show, message) {
    if (!window.BJGTVLoading) return;
    if (show) window.BJGTVLoading.show(message || "Loading SNES frame…");
    else window.BJGTVLoading.hide();
  }

  // TV runs emit compact one-second summaries through WebView's console. The
  // Android wrapper records them with a dedicated log tag. Canvas submission
  // is deliberately separate from display presentation: WebView exposes no
  // compositor presentation timestamps here.
  function tvMetric(event, values) {
    if (!window.BJG_TV_MODE || !window.console || !console.info) return;
    var record = Object.assign({ event: event, t_ms: Math.round(performance.now() - tvMetrics.bootAt), rom_run: tvMetrics.romRun }, values || {});
    console.info("BJG_TV_METRIC " + JSON.stringify(record));
  }

  function percentile(samples, fraction) {
    if (!samples.length) return 0;
    var sorted = samples.slice().sort(function (a, b) { return a - b; });
    return sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * fraction) - 1)];
  }

  function summarize(samples) {
    var sum = samples.reduce(function (total, value) { return total + value; }, 0);
    return {
      mean_ms: Number((sum / Math.max(1, samples.length)).toFixed(3)),
      p95_ms: Number(percentile(samples, 0.95).toFixed(3)),
      max_ms: Number(Math.max.apply(Math, samples.concat([0])).toFixed(3))
    };
  }

  function clearTouchNav() {
    clearTimeout(touchRelease);
    touchRelease = 0;
    if (touchNavPressed) pad &= ~touchNavPressed;
    touchNavPressed = 0;
  }

  // --- core module loading ---------------------------------------------------

  function loadCoreScript() {
    return new Promise(function (resolve, reject) {
      if (window.BsnesJg) return resolve(window.BsnesJg);
      var s = document.createElement("script");
      s.src = bust("cores/bsnes_jg.js");
      s.onload = function () { resolve(window.BsnesJg); };
      s.onerror = function () { reject(new Error("core not built")); };
      document.body.appendChild(s);
    });
  }

  // --- rendering -------------------------------------------------------------

  function present() {
    var w = Module._bjg_video_w(), h = Module._bjg_video_h(), pitch = Module._bjg_video_pitch();
    if (!w || !h) return false;
    // bsnes hands us a 512-wide buffer for lores content (256 logical px doubled)
    // and ~240 scanlines incl. overscan. Collapse the 2x horizontal doubling and
    // crop to the 224 visible NTSC lines — the true 256x224 logical frame, square
    // pixels at the SNES 8:7 sample-grid aspect (matches the gate's jgxcheck PNG). Without
    // this the picture is stretched 2x wide.
    var step = w >= 512 ? 2 : 1;
    var ow = (w / step) | 0;
    // Skip the top NTSC overscan when the core hands us a tall buffer. Measured
    // per-row on this build (2026-07-27, deterministic frames after _bjg_reset):
    // the 512x240 buffer carries content in rows [8,232) — yoff=0 would add an
    // 8px black band and crop the bottom rows instead. A 224-line buffer (h<232)
    // is already flush, so the offset degrades to 0. Supersedes aaacbae, whose
    // "flush at buffer top" rationale described the headless jgxcheck capture.
    var yoff = h >= 232 ? 8 : 0;
    var avail = h - yoff;
    var oh = avail < 224 ? avail : 224;
    var heap = Module.HEAPU32;               // re-fetch each frame (may grow)
    var base = Module._bjg_video() >>> 2;    // uint32 index
    // Keep the selected ROM card up while the core is booting or the first video
    // frames contain only a few lit pixels. Slow devices can take a long time to
    // reach a useful title/game frame; switching on the first pixel reads as a
    // broken black screen. Once at least 1% of a 4px sampling grid is lit, hand
    // over to the live framebuffer. The frame cap prevents a deliberately dark
    // game from keeping its poster forever.
    if (!revealed) {
      var lit = 0, samples = 0;
      for (var sy = yoff; sy < yoff + oh; sy += 4) {
        var sb = base + sy * pitch;
        for (var sx = 0; sx < ow; sx += 4) {
          samples++;
          if (heap[sb + sx * step] & 0xffffff) lit++;
        }
      }
      if (lit < Math.max(12, Math.ceil(samples * 0.01)) && tvMetrics.romFrames < 600) return false;
      revealed = true;
      setLoading(false);
    }
    if (!imageData || canvas.width !== ow || canvas.height !== oh) {
      canvas.width = ow; canvas.height = oh;
      imageData = ctx.createImageData(ow, oh);
    }
    if (!dimsShown && runLabel) { status(runLabel + " · " + ow + "×" + oh); dimsShown = true; }
    var out = imageData.data;
    var di = 0;
    for (var y = 0; y < oh; y++) {
      var si = base + (y + yoff) * pitch;
      for (var x = 0; x < ow; x++) {
        var px = heap[si + x * step];        // 0x00RRGGBB
        out[di++] = (px >>> 16) & 0xff;      // R
        out[di++] = (px >>> 8) & 0xff;       // G
        out[di++] = px & 0xff;               // B
        out[di++] = 255;                     // A
      }
    }
    ctx.putImageData(imageData, 0, 0);
    if (window.BJG_TV_MODE && !tvMetrics.firstLiveFrame) {
      tvMetrics.firstLiveFrame = true;
      tvMetric("first_live_frame", { width: ow, height: oh, image_ratio: "8:7" });
    }
    return true;
  }

  function frame(timestamp) {
    if (!running) return;
    var entered = performance.now();
    if (window.BJG_TV_MODE && tvMetrics.lastRafAt !== null) tvMetrics.raf.push(entered - tvMetrics.lastRafAt);
    tvMetrics.lastRafAt = entered;
    var frameTime = Number.isFinite(timestamp) ? timestamp : entered;
    var dueSteps;
    if (window.BJG_TV_MODE) {
      lastEmulationTimestamp = frameTime;
      var scheduled = tvFrameClock ? tvFrameClock.advance(frameTime) : { steps: 1, pending: 0 };
      emulationCredit = scheduled.pending;
      dueSteps = scheduled.steps;
    } else {
      // Preserve the established one-core-frame-per-display-callback browser behavior.
      emulationCredit = 1;
      dueSteps = 1;
    }
    var steps = 0;
    var coreEnd = performance.now();
    while (steps < dueSteps && steps < MAX_STEPS_PER_CALLBACK) {
      Module._bjg_set_input(0, pad);
      var coreStart = performance.now();
      Module._bjg_run();
      coreEnd = performance.now();
      if (!tvFrameClock) emulationCredit -= 1;
      steps++;
      if (window.BJG_TV_MODE) {
        tvMetrics.romFrames++;
        tvMetrics.core.push(coreEnd - coreStart);
        if (!tvMetrics.fidelityReady) {
          var meta = romMeta(current), sc = meta && meta.selfcheck;
          if (sc && sc.mode !== "live-record") {
            var wram = Module._bjg_wram() >>> 0, off = Number(sc.off), got = 0;
            for (var i = 0; i < sc.len; i++) got |= Module.HEAPU8[wram + off + i] << (8 * i);
            if (tvMetrics.romFrames >= Number(sc.frames) && (got >>> 0) === (Number(sc.want) >>> 0)) {
              tvMetrics.fidelityReady = true;
              tvMetric("reference_ready", { rom: current, frame: tvMetrics.romFrames, value: "0x" + (got >>> 0).toString(16).toUpperCase() });
            }
          }
        }
      }
    }
    var drawStart = performance.now();
    var submitted = present();
    var canvasEnd = performance.now();
    if (window.BJG_TV_MODE) {
      tvMetrics.canvas.push(canvasEnd - coreEnd);
      if (submitted) {
        tvMetrics.draw.push(canvasEnd - drawStart);
        tvMetrics.drawSubmissions++;
      }
      tvMetrics.frames += steps;
      tvMetrics.frameCallbacks++;
      tvMetrics.maxBacklog = Math.max(tvMetrics.maxBacklog, emulationCredit);
      if (emulationCredit >= MAX_STEPS_PER_CALLBACK && emulationCredit >= tvMetrics.lastBacklogReport + MAX_STEPS_PER_CALLBACK) {
        tvMetrics.lastBacklogReport = emulationCredit;
        tvMetric("emulation_backlog", { pending_frames: Number(emulationCredit.toFixed(2)), max_steps_per_callback: MAX_STEPS_PER_CALLBACK });
      }
      // Sample by elapsed monotonic time so slower engines still publish an
      // approximately one-second window instead of stretching each sample to
      // 60 completed frames.
      if (entered - tvMetrics.windowStartAt >= 1000 && (tvMetrics.core.length || tvMetrics.drawSubmissions)) {
        var windowMs = Math.max(1, entered - tvMetrics.windowStartAt);
        var core = summarize(tvMetrics.core), canvas = summarize(tvMetrics.canvas), draw = summarize(tvMetrics.draw), raf = summarize(tvMetrics.raf);
        var perfSample = {
          emuFps: tvMetrics.core.length * 1000 / windowMs,
          drawFps: tvMetrics.drawSubmissions * 1000 / windowMs,
          coreMeanMs: core.mean_ms, coreP95Ms: core.p95_ms,
          drawMeanMs: draw.mean_ms, drawP95Ms: draw.p95_ms,
          backlogFrames: Number(emulationCredit.toFixed(2)), windowMs: Number(windowMs.toFixed(1))
        };
        if (window.BJGPerformance) window.BJGPerformance.publish(perfSample);
        tvMetric("playback_window", {
          frames: tvMetrics.frames, rom_frames: tvMetrics.romFrames,
          target_hz: EMULATION_HZ,
          sample_frames: tvMetrics.core.length, canvas_callbacks: tvMetrics.frameCallbacks,
          draw_submissions: tvMetrics.drawSubmissions,
          emu_fps: Number(perfSample.emuFps.toFixed(2)), draw_fps: Number(perfSample.drawFps.toFixed(2)),
          core_mean_ms: core.mean_ms, core_p95_ms: core.p95_ms,
          draw_mean_ms: draw.mean_ms, draw_p95_ms: draw.p95_ms,
          window_ms: Math.round(windowMs),
          core_mean_ms: core.mean_ms, core_p95_ms: core.p95_ms, core_max_ms: core.max_ms,
          canvas_submit_mean_ms: canvas.mean_ms, canvas_submit_p95_ms: canvas.p95_ms,
          canvas_submit_max_ms: canvas.max_ms, raf_interval_p95_ms: raf.p95_ms,
          raf_interval_max_ms: raf.max_ms, emulation_backlog_frames: Number(emulationCredit.toFixed(2)),
          peak_backlog_frames: Number(tvMetrics.maxBacklog.toFixed(2))
        });
        tvMetrics.core.length = 0; tvMetrics.canvas.length = 0; tvMetrics.draw.length = 0; tvMetrics.raf.length = 0;
        tvMetrics.drawSubmissions = 0;
        tvMetrics.frameCallbacks = 0; tvMetrics.windowStartAt = performance.now(); tvMetrics.maxBacklog = emulationCredit;
        tvMetrics.lastBacklogReport = Math.max(0, emulationCredit - (emulationCredit % MAX_STEPS_PER_CALLBACK));
      }
    }
    rafId = requestAnimationFrame(frame);
  }

  function startLoop() {
    if (running) return;
    if (window.BJG_TV_MODE) {
      tvMetrics.core.length = 0; tvMetrics.canvas.length = 0; tvMetrics.draw.length = 0; tvMetrics.raf.length = 0;
      tvMetrics.drawSubmissions = 0;
      tvMetrics.lastRafAt = null;
      tvMetrics.frameCallbacks = 0;
      tvMetrics.windowStartAt = performance.now();
      tvMetrics.maxBacklog = 0;
      tvMetrics.lastBacklogReport = 0;
      lastEmulationTimestamp = null;
      emulationCredit = 0;
      if (tvFrameClock) tvFrameClock.reset();
    }
    running = true;
    rafId = requestAnimationFrame(frame);
  }
  function stopLoop() {
    running = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
    clearTouchNav();
    tvMetrics.core.length = 0; tvMetrics.canvas.length = 0; tvMetrics.draw.length = 0; tvMetrics.raf.length = 0;
    tvMetrics.drawSubmissions = 0;
    tvMetrics.lastRafAt = null;
    lastEmulationTimestamp = null;
    emulationCredit = 0;
    if (tvFrameClock) tvFrameClock.reset();
    tvMetrics.frameCallbacks = 0;
    tvMetrics.windowStartAt = performance.now();
    tvMetrics.maxBacklog = 0;
    tvMetrics.lastBacklogReport = 0;
  }

  // --- ROM loading -----------------------------------------------------------

  function loadRomBytes(bytes) {
    var ptr = Module._malloc(bytes.length);
    Module.HEAPU8.set(bytes, ptr);
    var ok = Module._bjg_load(ptr, bytes.length);
    Module._free(ptr);
    // Select a fresh poster for this ROM. `present()` replaces it when the game
    // has produced a useful live frame (or after a bounded 600-frame dark-ROM
    // fallback); clearing it here makes long boot/title sequences look broken.
    if (ok === 1 && ctx) {
      revealed = false;
      tvMetric("rom_loaded", { rom: current || DEFAULT_ROM, bytes: bytes.length });
    }
    return ok === 1;
  }

  function playUrl(id) {
    var previous = current;
    var previousLabel = runLabel;
    var failurePhase = "fetch";
    if (window.BJG_TV_MODE) {
      tvMetrics.romRun++;
      tvMetrics.romFrames = 0;
      tvMetrics.firstLiveFrame = false;
      tvMetrics.fidelityReady = false;
    }
    stopLoop();
    badge(null, "");
    paintPreview(id);
    setLoading(true, "Loading " + id + "…");
    status("loading " + id + ".sfc…");
    return fetch(bust("roms/" + id + ".sfc"))
      .then(function (r) { if (!r.ok) throw new Error("fetch " + id); return r.arrayBuffer(); })
      .then(function (buf) {
        failurePhase = "core";
        current = id;
        if (!loadRomBytes(new Uint8Array(buf))) {
          current = previous;
          throw new Error("core rejected ROM");
        }
        runLabel = "running " + id + ".sfc"; dimsShown = false;
        status(runLabel);
        markActive(id);
        startLoop();
        updateCheckButton(id);
        // ?verify=1 auto-runs the fidelity self-check once the ROM is up — the
        // hook CI's headless gate drives (poll #checkresult for PASS/MISMATCH).
        if (new URLSearchParams(location.search).get("verify") === "1" && !window.__bjgAutoVerified) {
          window.__bjgAutoVerified = true;
          setTimeout(verify, 0);
        }
        return true;
      })
      .catch(function (e) {
        setLoading(false);
        window.BJGTV.lastLoadFailure = { rom: id, phase: failurePhase, message: e.message, previous: previous || "" };
        current = failurePhase === "core" ? null : previous;
        runLabel = failurePhase === "core" ? "" : previousLabel;
        status("error: " + e.message);
        tvMetric("rom_load_error", { rom: id, error: e.message });
        if (previous && failurePhase !== "core") { status(previousLabel); startLoop(); }
        return false;
      });
  }

  function playFile(file) {
    current = null;
    stopLoop();
    badge(null, "");
    document.querySelectorAll("#picker button[data-rom]").forEach(function (b) {
      b.removeAttribute("aria-current");
    });
    status("loading " + file.name + "…");
    file.arrayBuffer().then(function (buf) {
      if (!loadRomBytes(new Uint8Array(buf))) { status("error: core rejected " + file.name); return; }
      runLabel = "running " + file.name; dimsShown = false;
      status(runLabel);
      startLoop();
      updateCheckButton(null);
    });
  }

  // --- fidelity self-check (mirrors dev/jgxcheck.cpp) ------------------------

  function romMeta(id) {
    if (!manifest || !id) return null;
    return manifest.roms.find(function (r) { return r.id === id; }) || null;
  }

  function updateCheckButton(id) {
    var btn = document.getElementById("verify");
    if (!btn) return;
    var meta = romMeta(id);
    if (meta && meta.selfcheck) {
      btn.disabled = false;
      btn.title = "Reproduce the gate's headless assert in this tab";
    } else {
      btn.disabled = true;
      btn.title = "No gate reference for this ROM";
    }
  }

  // The host page owns the badge element's base class and matches its CSS on
  // `.<base>.<state>` — `rp-badge` in astro/SnesPlayer.astro and embed/snippet.html,
  // plain `badge` in web/index.html. So the state is swapped with classList rather
  // than assigned through .className, which would drop that base class and leave
  // every `.rp-badge.pass` / `.badge.warn` rule unmatched.
  function badgeState(cls) {
    if (!checkEl) return;
    checkEl.classList.remove("running", "pass", "fail", "warn");
    if (cls) checkEl.classList.add(cls);
  }

  function badge(cls, text) {
    if (!checkEl) return;
    badgeState(cls);
    checkEl.textContent = text;
  }

  // Poll the machine that is already running, instead of power-cycling: a demo whose "displayed"
  // state is meaningful (e.g. the gallery's browsing cursor) would have that state destroyed by a
  // reload before anything could be read. sc.record gives byte offsets from sc.off; sc.state
  // reaches sc.ready only once every field describes the same, coherent verdict — the ROM's
  // publication barrier (see "What the ROM publishes" / "The player / manifest contract" in
  // docs/plans/2026-07-28-gallery-per-image-selfcheck.md, llvm-mos-65816). Deliberately does NOT
  // stopLoop(): the live rAF loop keeps applying the visitor's keyboard/touch input every frame
  // (see frame()), which is what lets navigation during the check be observed at all (step 5).
  function verifyLiveRecord(sc) {
    var rec = sc.record, poll = sc.poll || 120, total = sc.frames, done = 0;
    var target = null, retargets = 0;
    badge("running", "verifying…");
    (function chunk() {
      for (var i = 0; i < poll; i++) Module._bjg_run();
      done += poll;
      present();
      var wram = Module._bjg_wram() >>> 0, u8 = Module.HEAPU8, base = wram + Number(sc.off);
      var state = u8[base + rec.state];
      var work = state ? u8[base + rec.work] : null;   // ignore every field while state==0
      var name = (sc.titles && work != null) ? sc.titles[work] : (work != null ? "work " + work : null);
      if (work != null && target != null && work !== target) {
        // the visitor navigated mid-check
        if (++retargets > 1) {
          badge("fail", "navigation kept restarting the check — hold on one artwork and try again");
          return;
        }
        target = work; done = 0;
        badge("running", "following your navigation to " + name);
        setTimeout(chunk, 0);
        return;
      }
      if (work != null && target == null) target = work;
      if (state !== sc.ready) {
        if (done >= total) {
          badge("warn", "⏱ still verifying " + (name || "…") + " — not finished within " + total + " frames");
          return;
        }
        badge("running", name ? ("verifying " + name + "… " + done + "/" + total) : "verifying… " + done + "/" + total);
        setTimeout(chunk, 0);
        return;
      }
      var z = u8[base + rec.z[0]] | (u8[base + rec.z[0] + 1] << 8);
      var ok = u8[base + rec.ok];
      var want = sc.oracle[work];
      if (ok === 1 && z === want) {
        badge("pass", "✓ FIDELITY " + name + " — repacked on-SNES to " + z + " B == host oracle");
      } else if (ok !== 1) {
        badge("fail", "✗ FAILED " + name + " — the ROM's own byte-compare rejected its repack");
      } else {
        badge("fail", "✗ MISMATCH " + name + " got " + z + " want " + want);
      }
      // no startLoop(): the live loop was never stopped, so it is already resuming on its own —
      // the visitor's browsing position was never touched by this check.
    })();
  }

  // Power on, run `frames` frames, then read WRAM and compare — exactly what the
  // gate's jgxcheck does. Runs in chunks so the tab stays responsive.
  function verify() {
    if (verification) return;
    var meta = romMeta(current);
    if (!meta || !meta.selfcheck) return;
    var sc = meta.selfcheck;
    if (sc.mode === "live-record") { verifyLiveRecord(sc); return; }
    var off = Number(sc.off), len = sc.len, want = Number(sc.want), total = sc.frames;

    stopLoop();
    var task = { cancelled: false };
    verification = task;
    var verifyStarted = performance.now();
    tvMetric("verification_started", { rom: current, frames: total, expected: want, offset: off });
    if (window.BJGTV && window.BJGTV.onVerification) window.BJGTV.onVerification("starting");
    // re-load this ROM to power on cleanly, like the gate's harness.
    fetch(bust("roms/" + current + ".sfc"))
      .then(function (r) { return r.arrayBuffer(); })
      .then(function (buf) {
        if (verification !== task || task.cancelled) return;
        if (!loadRomBytes(new Uint8Array(buf))) throw new Error("core rejected ROM during verification");
        badgeState("running");
        var done = 0;
        function chunk() {
          if (verification !== task || task.cancelled) {
            if (verification === task) verification = null;
            badge("warn", "verification cancelled");
            if (window.BJGTV && window.BJGTV.onVerification) window.BJGTV.onVerification("cancelled");
            tvMetric("verification_cancelled", {
              rom: current, frames: done, total_frames: total,
              duration_ms: Number((performance.now() - verifyStarted).toFixed(1))
            });
            return;
          }
          // Bound each uninterrupted call so a TV remote can cancel or resume even
          // on slower WebViews. One unusually slow frame can exceed the budget.
          var started = performance.now();
          do {
            Module._bjg_run();
            done++;
          } while (done < total && performance.now() - started < 8);
          badge("running", "verifying… " + done + "/" + total + " frames");
          present();
          if (window.BJGTV && window.BJGTV.onVerification) window.BJGTV.onVerification("running", done, total);
          if (done < total) { setTimeout(chunk, 0); return; }
          // read `len` little-endian bytes of WRAM at `off`
          var wram = Module._bjg_wram() >>> 0;
          var u8 = Module.HEAPU8;
          var got = 0;
          for (var k = 0; k < len; k++) got |= u8[wram + off + k] << (8 * k);
          got >>>= 0;
          var hexGot = "0x" + got.toString(16).toUpperCase();
          var hexWant = "0x" + (want >>> 0).toString(16).toUpperCase();
          if (got === want) {
            badge("pass", "✓ FIDELITY " + hexGot + " == gate (" + sc.label + ", " + total + " frames)");
          } else {
            badge("fail", "✗ MISMATCH got " + hexGot + " want " + hexWant);
          }
          if (verification === task) verification = null;
          if (window.BJGTV && window.BJGTV.onVerification) window.BJGTV.onVerification(got === want ? "pass" : "fail", done, total);
          tvMetric("verification_finished", {
            rom: current, frames: done, duration_ms: Number((performance.now() - verifyStarted).toFixed(1)),
            expected: want, actual: got, result: got === want ? "pass" : "fail"
          });
          // Browser embeds retain their historical behavior; the TV app leaves
          // the verified result paused until the user selects Resume.
          if (!window.BJG_TV_MODE) startLoop();
        }
        setTimeout(chunk, 0);
      })
      .catch(function (e) {
        if (verification !== task) return;
        verification = null;
        badge("fail", "verification error: " + e.message);
        if (window.BJGTV && window.BJGTV.onVerification) window.BJGTV.onVerification("error", 0, total);
        tvMetric("verification_error", { rom: current, error: e.message });
      });
  }

  // --- input -----------------------------------------------------------------

  function onKey(down) {
    return function (e) {
      if (window.BJG_TV_MODE) return;
      var bit = KEYMAP[e.code];
      if (bit === undefined) return;
      e.preventDefault();
      if (down) pad |= bit; else pad &= ~bit;
    };
  }

  // --- UI wiring -------------------------------------------------------------

  function markActive(id) {
    document.querySelectorAll("#picker button[data-rom]").forEach(function (b) {
      b.setAttribute("aria-current", b.dataset.rom === id ? "true" : "false");
    });
  }

  function showProvenance() {
    fetch(bust("cores/PROVENANCE.json"))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (p) {
        if (!p || !bannerEl) return;
        var emver = (String(p.emscripten || "").match(/\d+\.\d+\.\d+/) || ["?"])[0];
        bannerEl.innerHTML =
          "Running <b>" + p.core + " " + p.version + "</b> — the exact cycle-accurate core " +
          "the differential gate trusts (sha256 <code>" + String(p.sha256).slice(0, 12) +
          "…</code>, emscripten " + emver + "). Hit <b>Verify fidelity</b> to reproduce the " +
          "gate's headless WRAM assert in this tab.";
      })
      .catch(function () {});
  }

  // Pause the run loop when the canvas scrolls out of view (resume on return),
  // so an embedded demo doesn't burn a CPU core while the reader is elsewhere.
  function observeVisibility() {
    var target = document.getElementById("game") || canvas;
    if (!target || typeof IntersectionObserver === "undefined") return;
    new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) {
        if (Module && Module._bjg_loaded && Module._bjg_loaded()) startLoop();
      } else {
        stopLoop();
      }
    }, { threshold: 0.05 }).observe(target);
  }

  // Paint the baked preview onto the canvas as a loading poster. Keep it visible
  // through blank boot frames until the game has produced a meaningful live image.
  function paintPreview(id) {
    if (!id || !ctx) return;
    var img = new Image();
    img.onload = function () {
      if (revealed) return;                  // live already took over
      ctx.imageSmoothingEnabled = false;     // crisp nearest-neighbour upscale (the SNES look)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.src = bust((window.BJG_LIBRARY_MODE ? "roms/cards/" : "preview/") + id + ".png");
  }

  function init() {
    window.BJGTV = {
      pause: function () { stopLoop(); },
      resume: function () { if (!verification && Module && current) startLoop(); },
      restart: function () { if (verification) verification.cancelled = true; verification = null; return playUrl(current || DEFAULT_ROM); },
      play: playUrl,
      lastLoadFailure: null,
      currentRom: function () { return current; },
      isReady: function () { return !!Module; },
      hasRom: function () { return !!current; },
      canVerify: function (id) { return !!manifest && manifest.roms.some(function (rom) { return rom.id === id && !!rom.selfcheck; }); },
      showLibrary: function () { stopLoop(); },
      verify: verify,
      benchmark: function (totalFrames) {
        if (!window.BJG_TV_MODE || !tvMetrics.fidelityReady || !Module) return Promise.reject(new Error("benchmark requires a TV run with the reference gate complete"));
        var wasRunning = running, done = 0, coreNs = 0, started = performance.now();
        stopLoop(); totalFrames = Math.max(1, Math.min(6000, Number(totalFrames) || 600));
        return new Promise(function (resolve) {
          function chunk() {
            var until = Math.min(totalFrames, done + 60);
            while (done < until) {
              Module._bjg_set_input(0, pad);
              var t = performance.now(); Module._bjg_run(); coreNs += (performance.now() - t) * 1e6; done++;
            }
            if (done < totalFrames) { setTimeout(chunk, 0); return; }
            var elapsedNs = Math.round((performance.now() - started) * 1e6);
            var result = { schema: "bjg-profile-v1", engine: "wasm", phase: "unpaced-core", frames: done,
              elapsedNs: elapsedNs, coreNs: Math.round(coreNs), throughputWallFps: done * 1e9 / elapsedNs,
              throughputCoreFps: done * 1e9 / coreNs, instrumentation: "on", wram0580: "0x" + (Module.HEAPU8[(Module._bjg_wram() >>> 0) + 0x580] | (Module.HEAPU8[(Module._bjg_wram() >>> 0) + 0x581] << 8)).toString(16).toUpperCase() };
            console.info("BJG_TV_METRIC " + JSON.stringify(result));
            if (wasRunning) startLoop(); resolve(result);
          }
          setTimeout(chunk, 0);
        });
      },
      cancelVerification: function () { if (verification) verification.cancelled = true; },
      background: function () {
        stopLoop();
        if (verification) verification.cancelled = true;
        tvMetric("backgrounded", { frames: tvMetrics.frames });
        if (window.BJG_TV_MODE && window.BJGTV.onBackground) window.BJGTV.onBackground();
      },
      isVerifying: function () { return !!verification; },
      onVerification: null,
      onBackground: null
    };

    // The picker, file input, verify button and drag-drop target are all
    // optional — an embed may render just the canvas + status. Guard each.
    var shareAppEl = document.getElementById("share-app");
    var shareStatusEl = document.getElementById("share-status");
    function shareStatus(message) {
      if (!shareStatusEl) return;
      shareStatusEl.textContent = message;
      clearTimeout(shareStatusEl._clearTimer);
      shareStatusEl._clearTimer = setTimeout(function () { shareStatusEl.textContent = ""; }, 3500);
    }
    function copyAppUrl() {
      var url = window.location.href;
      if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(url).then(function () {
          shareStatus("Web app link copied.");
        });
      }
      var field = document.createElement("textarea");
      field.value = url;
      field.setAttribute("readonly", "");
      field.style.position = "fixed";
      field.style.opacity = "0";
      document.body.appendChild(field);
      field.select();
      var copied = false;
      try { copied = document.execCommand("copy"); } catch (_) {}
      field.remove();
      if (copied) shareStatus("Web app link copied.");
      else {
        window.prompt("Copy this web app link:", url);
        shareStatus("Web app link ready to copy.");
      }
      return Promise.resolve();
    }
    if (shareAppEl) shareAppEl.addEventListener("click", function () {
      if (navigator.share) {
        navigator.share({ title: document.title, text: "SNES homebrew library", url: window.location.href })
          .then(function () { shareStatus("Web app link shared."); })
          .catch(function (error) {
            if (error && error.name === "AbortError") return;
            copyAppUrl().catch(function () { shareStatus("Could not copy the web app link."); });
          });
      } else {
        copyAppUrl().catch(function () { shareStatus("Could not copy the web app link."); });
      }
    });
    document.querySelectorAll("#picker button[data-rom]").forEach(function (b) {
      b.addEventListener("click", function () { playUrl(b.dataset.rom); });
    });
    var fileEl = document.getElementById("file");
    if (fileEl) fileEl.addEventListener("change", function (e) {
      if (e.target.files[0]) playFile(e.target.files[0]);
    });
    var verifyEl = document.getElementById("verify");
    if (verifyEl) verifyEl.addEventListener("click", verify);

    // BEGIN SHARED FULLSCREEN CONTROLLER — canonical copy lives in bsnes-jg-wasm;
    // sites vendor this file verbatim via `bsnes-jg-player sync`, never edit a site copy.
    (function () {
      if (window.__bjgFullscreenCleanup) window.__bjgFullscreenCleanup();

      var fsEl = document.getElementById("fullscreen");
      var wrap = canvas && canvas.parentElement;
      if (!fsEl || !wrap) return;

      var request = wrap.requestFullscreen || wrap.webkitRequestFullscreen;
      if (!request) { fsEl.style.display = "none"; return; }

      var fitRaf = 0;
      var settleRaf = 0;
      function activeElement() {
        return document.fullscreenElement || document.webkitFullscreenElement;
      }
      function px(value) {
        var n = parseFloat(value);
        return Number.isFinite(n) ? n : 0;
      }
      function fitFullscreenCanvas() {
        fitRaf = 0;
        if (activeElement() !== wrap) return;
        var style = getComputedStyle(wrap);
        var padW = px(style.paddingLeft) + px(style.paddingRight);
        var padH = px(style.paddingTop) + px(style.paddingBottom);
        var availW = wrap.clientWidth - padW;
        var availH = wrap.clientHeight - padH;
        // Mobile landscape fullscreen can leave the layout viewport larger than
        // the actually visible viewport while browser chrome/orientation settles.
        // Never size against a box larger than the pixels the user can see.
        if (window.visualViewport) {
          availW = Math.min(availW, window.visualViewport.width - padW);
          availH = Math.min(availH, window.visualViewport.height - padH);
        }
        // Leave one CSS pixel on every edge. This absorbs fractional safe-area
        // values and device-pixel rounding instead of letting a limiting edge crop.
        availW = Math.max(0, Math.floor(availW) - 2);
        availH = Math.max(0, Math.floor(availH) - 2);
        // The core's backing buffer can switch to a native 512x240 frame. That is storage
        // resolution, not the intended SNES display shape; use the shared 4:3 display geometry.
        var displayW = 4;
        var displayH = 3;
        var scale = Math.min(availW / displayW, availH / displayH);
        if (!(scale > 0)) return;
        wrap.style.setProperty("--bjg-fs-width", Math.max(1, Math.floor(displayW * scale)) + "px");
        wrap.style.setProperty("--bjg-fs-height", Math.max(1, Math.floor(displayH * scale)) + "px");
      }
      function scheduleFullscreenFit() {
        if (fitRaf) cancelAnimationFrame(fitRaf);
        fitRaf = requestAnimationFrame(fitFullscreenCanvas);
      }
      function settleFullscreenFit() {
        scheduleFullscreenFit();
        if (settleRaf) cancelAnimationFrame(settleRaf);
        settleRaf = requestAnimationFrame(function () {
          scheduleFullscreenFit();
          settleRaf = requestAnimationFrame(scheduleFullscreenFit);
        });
      }
      function onFullscreenChange() {
        var active = activeElement() === wrap;
        fsEl.textContent = active ? "Exit full" : "Fullscreen";
        if (active) settleFullscreenFit();
        else {
          wrap.style.removeProperty("--bjg-fs-width");
          wrap.style.removeProperty("--bjg-fs-height");
        }
      }
      function onFullscreenResize() {
        if (activeElement() === wrap) settleFullscreenFit();
      }
      function onFullscreenClick() {
        if (activeElement()) {
          var exit = document.exitFullscreen || document.webkitExitFullscreen;
          if (exit) Promise.resolve(exit.call(document)).catch(onFullscreenChange);
        } else {
          Promise.resolve(request.call(wrap)).then(settleFullscreenFit).catch(onFullscreenChange);
        }
      }

      fsEl.addEventListener("click", onFullscreenClick);
      document.addEventListener("fullscreenchange", onFullscreenChange);
      document.addEventListener("webkitfullscreenchange", onFullscreenChange);
      window.addEventListener("resize", onFullscreenResize);
      window.addEventListener("orientationchange", onFullscreenResize);
      if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", onFullscreenResize);
        window.visualViewport.addEventListener("scroll", onFullscreenResize);
      }

      var oldStyle = document.getElementById("bjg-fullscreen-style");
      if (oldStyle) oldStyle.remove();
      var styleEl = document.createElement("style");
      styleEl.id = "bjg-fullscreen-style";
      styleEl.textContent =
        ".rp-screen:-webkit-full-screen,.rp-screen:fullscreen{" +
          "box-sizing:border-box;display:grid;place-items:center;width:100%;height:100%;margin:0;" +
          "padding:env(safe-area-inset-top,0px) env(safe-area-inset-right,0px) " +
                  "env(safe-area-inset-bottom,0px) env(safe-area-inset-left,0px);" +
          "overflow:hidden;background:#000;border:0;border-radius:0;line-height:0;" +
        "}" +
        ".rp-screen:-webkit-full-screen canvas,.rp-screen:fullscreen canvas{" +
          "display:block;width:var(--bjg-fs-width,auto);height:var(--bjg-fs-height,auto);" +
          "max-width:100%;max-height:100%;aspect-ratio:4/3;image-rendering:pixelated;" +
        "}";
      document.head.appendChild(styleEl);

      window.__bjgFullscreenCleanup = function () {
        if (fitRaf) cancelAnimationFrame(fitRaf);
        if (settleRaf) cancelAnimationFrame(settleRaf);
        fsEl.removeEventListener("click", onFullscreenClick);
        document.removeEventListener("fullscreenchange", onFullscreenChange);
        document.removeEventListener("webkitfullscreenchange", onFullscreenChange);
        window.removeEventListener("resize", onFullscreenResize);
        window.removeEventListener("orientationchange", onFullscreenResize);
        if (window.visualViewport) {
          window.visualViewport.removeEventListener("resize", onFullscreenResize);
          window.visualViewport.removeEventListener("scroll", onFullscreenResize);
        }
        wrap.style.removeProperty("--bjg-fs-width");
        wrap.style.removeProperty("--bjg-fs-height");
      };
    }());
    // END SHARED FULLSCREEN CONTROLLER

    window.addEventListener("keydown", onKey(true));
    window.addEventListener("keyup", onKey(false));
    // In-ROM touch controls (e.g. a gallery's sprite chevrons — not DOM
    // controls). A ROM opts in via its manifest entry:
    //   "touchNav": { "left": [x, y, w, h], "right": [x, y, w, h] }
    // in logical canvas pixels; taps inside a rect press that pad button for
    // one tap-length. Taps elsewhere stay inert. (Was hardcoded to the
    // lzss-gallery slug; the rects moved into roms/manifest.json.)
    function touchNavBits() {
      var meta = romMeta(current);
      return meta && meta.touchNav ? meta.touchNav : null;
    }
    function touchNavBitAt(tn, x, y) {
      function hit(r) { return r && x >= r[0] && x < r[0] + r[2] && y >= r[1] && y < r[1] + r[3]; }
      if (hit(tn.left)) return JOY.Left;
      if (hit(tn.right)) return JOY.Right;
      return 0;
    }
    canvas.addEventListener("pointerdown", function (e) {
      var tn = touchNavBits();
      if (!tn) return;
      var r = canvas.getBoundingClientRect();
      if (!r.width || !r.height) return;
      var x = (e.clientX - r.left) * canvas.width / r.width;
      var y = (e.clientY - r.top) * canvas.height / r.height;
      var bit = touchNavBitAt(tn, x, y);
      if (!bit) return;
      e.preventDefault();
      clearTouchNav();
      touchNavPressed = bit;
      pad |= bit;
      touchRelease = setTimeout(clearTouchNav, 120);
    }, { passive: false });
    /* Do not clear on pointerup: a quick click can otherwise begin and end
       between emulated input samples.  An accepted tap is a full 120 ms pulse. */
    canvas.addEventListener("pointercancel", clearTouchNav);
    window.addEventListener("blur", clearTouchNav);
    var game = document.getElementById("game");
    if (game) {
      ["dragover", "drop"].forEach(function (ev) {
        game.addEventListener(ev, function (e) { e.preventDefault(); });
      });
      game.addEventListener("drop", function (e) {
        if (e.dataTransfer.files[0]) playFile(e.dataTransfer.files[0]);
      });
    }

    // Show the baked preview before anything loads (covers the core download + ROM boot).
    var bootRom = new URLSearchParams(location.search).get("rom") || DEFAULT_ROM;
    paintPreview(bootRom);
    var directRom = new URLSearchParams(location.search).has("rom");
    setLoading(directRom || !window.BJG_LIBRARY_MODE, "Starting emulator…");

    status("loading core…");
    Promise.all([
      loadCoreScript().then(function (factory) {
        return factory({ locateFile: function (p) {           // bust the wasm Emscripten loads
          return (p && p.slice(-5) === ".wasm") ? bust("cores/" + p) : p;
        }});
      }),
      fetch(bust("roms/manifest.json")).then(function (r) { return r.json(); })
    ]).then(function (res) {
      Module = res[0];
      window.__bjg = Module;     // exposed for debugging / automated checks
      manifest = res[1];
      tvMetric("core_ready", { core: "bsnes-jg", version: "2.1.0", runtime: "wasm" });
      showProvenance();
      observeVisibility();
      if (window.BJG_TV_MODE) {
        if (window.BJG_LIBRARY_MODE && !directRom) setLoading(false);
        if (window.BJGTV.onReady) window.BJGTV.onReady();
        // In the TV library build, library.js owns direct-ROM startup so it can
        // wait for both the core and the ROM catalog. Starting here as well
        // races its play() call and can reset/unload the same core twice.
        if (new URLSearchParams(location.search).has("rom") && !window.BJG_LIBRARY_MODE) playUrl(bootRom);
      } else {
        playUrl(bootRom);
      }
    }).catch(function (e) {
      setLoading(false);
      status("");
      tvMetric("startup_error", { error: e.message });
      if (bannerEl) {
        bannerEl.innerHTML =
          "<b>Core not built.</b> Run <code>build.sh</code> to compile " +
          "<code>bsnes_jg.{js,wasm}</code>, then reload. (" + e.message + ")";
        bannerEl.className = "banner warn";
      }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
