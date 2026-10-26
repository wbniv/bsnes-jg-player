(function () {
  "use strict";

  var visible = true;
  var latest = null;
  var overlay = document.createElement("aside");
  overlay.id = "performance-overlay";
  overlay.setAttribute("aria-label", "Live emulator performance");
  overlay.innerHTML = '<div class="perf-heading">PERFORMANCE</div>' +
    '<div class="perf-rate"><span>EMU FPS</span><strong id="perf-emu">—</strong><small>target 60.0988</small></div>' +
    '<div class="perf-rate"><span>DRAW FPS</span><strong id="perf-draw">—</strong><small>app submissions</small></div>' +
    '<div class="perf-detail"><span>CORE</span><b id="perf-core">—</b><small>mean / p95 ms</small></div>' +
    '<div class="perf-detail"><span>DRAW</span><b id="perf-draw-time">—</b><small>mean / p95 ms</small></div>' +
    '<div class="perf-backlog">BACKLOG <b id="perf-backlog">—</b> frames</div>' +
    '<div class="perf-footnote">App-side rates · not panel FPS</div>';
  document.body.appendChild(overlay);

  var toggle = document.getElementById("tv-performance");
  function updateToggle() {
    if (!toggle) return;
    toggle.textContent = "Performance overlay · " + (visible ? "On" : "Off");
    toggle.setAttribute("aria-pressed", String(visible));
  }
  function setVisible(value, persist) {
    visible = !!value;
    overlay.hidden = !visible;
    updateToggle();
    if (persist !== false && window.BjgAndroid && window.BjgAndroid.setPerformanceOverlayEnabled) {
      window.BjgAndroid.setPerformanceOverlayEnabled(visible);
    }
    if (visible && latest) render(latest);
  }
  function fixed(value) {
    return Number.isFinite(Number(value)) ? Number(value).toFixed(1) : "—";
  }
  function render(sample) {
    document.getElementById("perf-emu").textContent = fixed(sample.emuFps);
    document.getElementById("perf-draw").textContent = fixed(sample.drawFps);
    document.getElementById("perf-core").textContent = fixed(sample.coreMeanMs) + " / " + fixed(sample.coreP95Ms);
    document.getElementById("perf-draw-time").textContent = fixed(sample.drawMeanMs) + " / " + fixed(sample.drawP95Ms);
    document.getElementById("perf-backlog").textContent = fixed(sample.backlogFrames);
  }
  if (toggle) toggle.addEventListener("click", function () { setVisible(!visible); });

  if (window.BjgAndroid && window.BjgAndroid.getPerformanceOverlayEnabled) {
    try { visible = !!window.BjgAndroid.getPerformanceOverlayEnabled(); } catch (_) { visible = true; }
  }
  setVisible(visible, false);

  window.BJGPerformance = {
    publish: function (sample) {
      if (!sample || typeof sample !== "object") return;
      latest = sample;
      if (visible) render(sample);
    },
    setVisible: setVisible,
    toggle: function () { setVisible(!visible); },
    isVisible: function () { return visible; }
  };
}());
