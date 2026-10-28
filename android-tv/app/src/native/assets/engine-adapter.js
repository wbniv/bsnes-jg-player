(function () {
  "use strict";
  window.BJG_ENGINE = "native";
  document.querySelectorAll("[data-engine-label]").forEach(function (node) { node.textContent = "NATIVE C++"; });
  document.documentElement.classList.add("native-engine");
  var currentRom = "";
  var nextId = 1;
  var pending = new Map();
  var status = document.getElementById("status");
  if (status) status.textContent = "Ready";

  function request(method, args) {
    return new Promise(function (resolve) {
      var id = nextId++;
      pending.set(id, resolve);
      window.BjgAndroid[method].apply(window.BjgAndroid, (args || []).concat([id]));
    });
  }
  window.__bjgNativeResolve = function (id, result) {
    var resolve = pending.get(id);
    if (!resolve) return;
    pending.delete(id);
    resolve(result);
  };
  window.__bjgNativeVerification = function (state, done, total) {
    if (window.BJGTV && window.BJGTV.onVerification) window.BJGTV.onVerification(state, done, total);
  };
  var api = {
    onReady: null,
    onVerification: null,
    onBackground: null,
    isReady: function () { return true; },
    hasRom: function () { return !!currentRom; },
    canVerify: function (slug) { return slug === "mandel-display"; },
    background: function () { api.pause(); if (api.hasRom() && api.onBackground) api.onBackground(); },
    play: function (slug) {
      currentRom = slug;
      if (window.BJGTVLoading) window.BJGTVLoading.show("Loading " + slug + "…");
      document.documentElement.classList.add("game-active");
      if (status) status.textContent = "Starting native core…";
      return request("playRom", [slug]).then(function (ok) {
        if (window.BJGTVLoading) window.BJGTVLoading.hide();
        if (!ok) { currentRom = ""; document.documentElement.classList.remove("game-active"); }
        if (status) status.textContent = ok ? slug : "Native core failed to load";
        return ok;
      });
    },
    pause: function () { window.BjgAndroid.pauseGame(); },
    resume: function () { window.BjgAndroid.resumeGame(); },
    showLibrary: function () {
      window.BjgAndroid.showLibrary();
      document.documentElement.classList.remove("game-active");
    },
    restart: function () { return request("restartGame", []); },
    verify: function () {
      if (!api.canVerify(currentRom)) return;
      if (api.onVerification) api.onVerification("starting", 0, 5800);
      request("verifyGame", []).then(function (result) {
        window.__bjgNativeVerification(result === true ? "pass" : result === "cancelled" ? "cancelled" : "fail", 5800, 5800);
      });
    },
    cancelVerification: function () { window.BjgAndroid.cancelVerify(); }
  };
  window.BJGTV = api;
}());
