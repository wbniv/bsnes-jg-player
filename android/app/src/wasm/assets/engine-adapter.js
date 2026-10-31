(function () {
  "use strict";
  window.BJG_ENGINE = "wasm";
  document.querySelectorAll("[data-engine-label]").forEach(function (node) { node.textContent = "WASM"; });
  var script = document.createElement("script");
  script.src = "app.js";
  script.onerror = function () {
    var status = document.getElementById("status");
    if (status) status.textContent = "WASM engine could not load";
  };
  document.body.appendChild(script);
}());
