(function () {
  "use strict";
  var pause = document.getElementById("pause-menu");
  var appVersion = window.BjgAndroid && window.BjgAndroid.getAppVersion ? window.BjgAndroid.getAppVersion() : "";
  document.querySelectorAll("[data-app-version]").forEach(function (element) { element.textContent = appVersion ? "v" + appVersion : ""; });
  var subtitle = document.getElementById("pause-subtitle");
  var resume = document.getElementById("tv-resume");
  var verify = document.getElementById("tv-verify");
  var cancel = document.getElementById("tv-cancel");
  var status = document.getElementById("status");
  var nativeStartRequested = false;

  function hide() {
    pause.hidden = true;
    document.body.classList.add("playing");
    window.BJGTV.resume();
  }
  function show() {
    if (!window.BJGTV || !window.BJGTV.hasRom()) return;
    window.BJGTV.pause();
    pause.hidden = false;
    subtitle.textContent = "Paused · Mandelbrot";
    resume.focus();
  }
  function begin() {
    document.body.classList.add("playing");
  }
  function attach() {
    var api = window.BJGTV;
    if (!api) { setTimeout(attach, 50); return; }
    api.onBackground = function () { if (api.hasRom()) show(); };
    api.onVerification = function (state, done, total) {
      pause.hidden = false;
      subtitle.textContent = state === "running" ? "Verifying frame " + done + " of " + total : "Verification " + state;
      var active = state === "running" || state === "starting";
      verify.hidden = active;
      cancel.hidden = !active;
      if (active && document.activeElement === verify) cancel.focus();
      else if (!active && document.activeElement === cancel) verify.focus();
      var result = document.getElementById("checkresult");
      if (result) result.textContent = state === "pass" ? "PASS" : state === "fail" ? "MISMATCH" : "";
    };

    if (window.BJG_ENGINE === "native") {
      if (!nativeStartRequested && api.isReady()) {
        nativeStartRequested = true;
        api.play(window.BJG_DEFAULT_ROM || "mandel-display").then(function (ok) {
          if (ok) begin();
          else if (status) status.textContent = "Could not start mandel-display";
        });
      }
      return;
    }

    if (api.hasRom()) begin();
    else setTimeout(attach, 50);
  }

  window.bjgTvBack = function () {
    if (pause.hidden) show(); else hide();
  };
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" || event.key === "BrowserBack") {
      event.preventDefault();
      window.bjgTvBack();
    }
  }, true);
  resume.addEventListener("click", hide);
  document.getElementById("tv-restart").addEventListener("click", function () {
    window.BJGTV.restart().then(function (ok) { if (ok) hide(); });
  });
  verify.addEventListener("click", function () {
    window.BJGTV.verify();
  });
  cancel.addEventListener("click", function () {
    window.BJGTV.cancelVerification();
  });
  document.getElementById("tv-exit").addEventListener("click", function () {
    window.BjgAndroid.exitApp();
  });
  attach();
}());
