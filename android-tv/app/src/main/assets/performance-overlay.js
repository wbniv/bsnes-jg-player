(function () {
  "use strict";

  var visible = true;
  var latest = null;
  var overlay = document.createElement("aside");
  overlay.id = "performance-overlay";
  overlay.setAttribute("aria-label", "Live emulator performance");
  overlay.innerHTML = '<div class="perf-heading">PERFORMANCE</div>' +
    '<div class="perf-rate"><span>EMU FPS</span><strong id="perf-emu">—</strong><small>target 60.0988</small><svg class="perf-sparkline" viewBox="0 0 120 20" aria-label="Recent emulation FPS"><line class="perf-target" x1="0" y1="2" x2="120" y2="2"></line><polyline id="perf-emu-line"></polyline></svg></div>' +
    '<div class="perf-rate"><span>DRAW FPS</span><strong id="perf-draw">—</strong><small>app submissions</small><svg class="perf-sparkline" viewBox="0 0 120 20" aria-label="Recent draw FPS"><line class="perf-target" x1="0" y1="2" x2="120" y2="2"></line><polyline id="perf-draw-line"></polyline></svg></div>' +
    '<div class="perf-detail"><span>CORE</span><b id="perf-core">—</b><small>mean / p95 ms</small></div>' +
    '<div class="perf-detail"><span>DRAW</span><b id="perf-draw-time">—</b><small>mean / p95 ms</small></div>' +
    '<div class="perf-backlog">BACKLOG <b id="perf-backlog">—</b> frames</div>' +
    '<div class="perf-footnote">App-side rates · not panel FPS</div>';
  var gameSurface = document.getElementById("game");
  (gameSurface || document.body).appendChild(overlay);

  var toggle = document.getElementById("tv-performance");
  var emuHistory = [], drawHistory = [];
  function updateToggle() {
    if (!toggle) return;
    toggle.textContent = "Performance overlay · " + (visible ? "On" : "Off");
    toggle.setAttribute("aria-pressed", String(visible));
  }
  function setVisible(value, persist) {
    var wasVisible = visible;
    visible = !!value;
    overlay.hidden = !visible;
    updateToggle();
    if (persist !== false && window.BjgAndroid && window.BjgAndroid.setPerformanceOverlayEnabled) {
      window.BjgAndroid.setPerformanceOverlayEnabled(visible);
    }
    if (visible && !wasVisible) {
      // Start with a fresh history and wait for a new metric window. Samples
      // published while hidden are intentionally not retained for the UI.
      latest = null;
      emuHistory.length = 0;
      drawHistory.length = 0;
    }
  }
  function fixed(value) {
    return Number.isFinite(Number(value)) ? Number(value).toFixed(1) : "—";
  }
  function sparkline(id, values) {
    var line = document.getElementById(id);
    if (!line || !values.length) return;
    var max = Math.max(60, ...values) * 1.05;
    var points = values.map(function (value, index) {
      var x = values.length < 2 ? 120 : index * 120 / (values.length - 1);
      var y = 18 - Math.max(0, Math.min(max, value)) * 16 / max;
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    line.setAttribute("points", points.join(" "));
  }
  function render(sample) {
    document.getElementById("perf-emu").textContent = fixed(sample.emuFps);
    document.getElementById("perf-draw").textContent = fixed(sample.drawFps);
    document.getElementById("perf-core").textContent = fixed(sample.coreMeanMs) + " / " + fixed(sample.coreP95Ms);
    document.getElementById("perf-draw-time").textContent = fixed(sample.drawMeanMs) + " / " + fixed(sample.drawP95Ms);
    document.getElementById("perf-backlog").textContent = fixed(sample.backlogFrames);
    sparkline("perf-emu-line", emuHistory);
    sparkline("perf-draw-line", drawHistory);
  }
  if (toggle) toggle.addEventListener("click", function () { setVisible(!visible); });

  if (window.BjgAndroid && window.BjgAndroid.getPerformanceOverlayEnabled) {
    try { visible = !!window.BjgAndroid.getPerformanceOverlayEnabled(); } catch (_) { visible = true; }
  }
  setVisible(visible, false);

  window.BJGPerformance = {
    publish: function (sample) {
      if (!sample || typeof sample !== "object") return;
      if (!visible) return;
      latest = sample;
      emuHistory.push(Number(sample.emuFps) || 0);
      drawHistory.push(Number(sample.drawFps) || 0);
      if (emuHistory.length > 30) emuHistory.shift();
      if (drawHistory.length > 30) drawHistory.shift();
      if (visible) render(sample);
    },
    setVisible: setVisible,
    toggle: function () { setVisible(!visible); },
    isVisible: function () { return visible; }
  };
}());
