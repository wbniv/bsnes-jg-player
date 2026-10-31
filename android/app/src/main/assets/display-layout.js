(function () {
  "use strict";

  var aspect = 4 / 3;
  var gap = 12;
  var canvas = document.getElementById("screen");
  var hud = document.getElementById("hud");
  var performancePanel = document.getElementById("performance-overlay");
  var queued = false;
  var safeProbe = document.createElement("div");
  safeProbe.setAttribute("aria-hidden", "true");
  safeProbe.style.cssText = "position:fixed;left:0;top:0;width:0;height:0;visibility:hidden;pointer-events:none;padding-top:env(safe-area-inset-top);padding-right:env(safe-area-inset-right);padding-bottom:env(safe-area-inset-bottom);padding-left:env(safe-area-inset-left)";
  document.body.appendChild(safeProbe);

  function number(value) {
    var parsed = parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function rect(element, box) {
    element.style.position = "absolute";
    element.style.transform = "none";
    element.style.left = box.x + "px";
    element.style.right = "auto";
    element.style.top = box.y + "px";
    element.style.bottom = "auto";
    element.style.width = Math.max(0, box.width) + "px";
    element.style.height = Math.max(0, box.height) + "px";
  }

  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () {
      queued = false;
      layout();
    });
  }

  function layout() {
    if (!canvas || !hud || !performancePanel) return;
    var viewportWidth = document.documentElement.clientWidth || window.innerWidth;
    var viewportHeight = document.documentElement.clientHeight || window.innerHeight;
    var inset = getComputedStyle(safeProbe);
    var safe = {
      left: number(inset.paddingLeft),
      top: number(inset.paddingTop),
      right: number(inset.paddingRight),
      bottom: number(inset.paddingBottom)
    };
    var width = Math.max(1, viewportWidth - safe.left - safe.right);
    var height = Math.max(1, viewportHeight - safe.top - safe.bottom);
    var game;
    var metadata;
    var performance;
    var portrait = height > width;

    if (portrait) {
      var metadataWidth = Math.max(0, width - gap * 2);
      hud.style.left = safe.left + gap + "px";
      hud.style.top = safe.top + gap + "px";
      hud.style.width = metadataWidth + "px";
      hud.style.height = "auto";
      var metadataContentHeight = document.body.classList.contains("playing") ? hud.scrollHeight : 44;
      var metadataHeight = Math.min(height * 0.32, Math.max(72, metadataContentHeight + gap));

      var performanceWidth = metadataWidth;
      performancePanel.style.left = safe.left + gap + "px";
      performancePanel.style.top = safe.top + "px";
      performancePanel.style.width = performanceWidth + "px";
      performancePanel.style.height = "auto";
      performancePanel.style.maxHeight = "none";
      performancePanel.style.overflowY = "visible";
      var showPerformance = !performancePanel.hidden && document.body.classList.contains("playing");
      var performanceContentHeight = showPerformance ? performancePanel.scrollHeight : 0;
      var performanceHeight = showPerformance
        ? Math.min(height * 0.36, Math.max(120, performanceContentHeight + gap))
        : 0;

      var imageAreaHeight = Math.max(1, height - metadataHeight - performanceHeight - gap * 2);
      var imageWidth = Math.min(width, aspect * imageAreaHeight);
      var imageHeight = imageWidth / aspect;
      game = {
        x: safe.left + (width - imageWidth) / 2,
        y: safe.top + metadataHeight + gap + (imageAreaHeight - imageHeight) / 2,
        width: imageWidth,
        height: imageHeight
      };
      metadata = { x: safe.left, y: safe.top, width: width, height: metadataHeight };
      performance = {
        x: safe.left,
        y: viewportHeight - safe.bottom - performanceHeight,
        width: width,
        height: performanceHeight
      };
      hud.style.padding = "6px 10px";
      performancePanel.style.overflowY = "auto";
    } else {
      var maxWidth = Math.min(width, aspect * height);
      var maxHeight = maxWidth / aspect;
      var naturalGutter = (width - maxWidth) / 2;
      var metadataMinimum = Math.max(80, Math.min(96, width * 0.10));
      var performanceMinimum = Math.max(96, Math.min(108, width * 0.11));
      var twoRails = naturalGutter >= metadataMinimum + gap &&
        naturalGutter >= performanceMinimum + gap;

      if (twoRails) {
        game = {
          x: safe.left + naturalGutter,
          y: safe.top + (height - maxHeight) / 2,
          width: maxWidth,
          height: maxHeight
        };
        metadata = { x: safe.left, y: safe.top, width: naturalGutter, height: height };
        performance = {
          x: safe.left + naturalGutter + maxWidth,
          y: safe.top,
          width: naturalGutter,
          height: height
        };
      } else {
        var railWidth = Math.max(metadataMinimum, performanceMinimum) + gap * 2;
        var gameAreaWidth = Math.max(1, width - railWidth);
        var railGameWidth = Math.min(maxWidth, gameAreaWidth);
        var railGameHeight = railGameWidth / aspect;
        var railX = safe.left + width - railWidth;
        game = {
          x: safe.left + (gameAreaWidth - railGameWidth) / 2,
          y: safe.top + (height - railGameHeight) / 2,
          width: railGameWidth,
          height: railGameHeight
        };
        metadata = { x: railX, y: safe.top + gap, width: railWidth, height: height * 0.46 };
        performance = {
          x: railX,
          y: safe.top + height * 0.48,
          width: railWidth,
          height: height * 0.52 - gap
        };
      }
      hud.style.padding = "8px";
      performancePanel.style.overflowY = "auto";
    }

    rect(canvas, game);
    rect(hud, metadata);
    rect(performancePanel, performance);
    performancePanel.style.maxHeight = Math.max(0, performance.height) + "px";
    document.documentElement.dataset.displayLayout = portrait ? "portrait" :
      (metadata.x > game.x ? "combined-rail" :
        (metadata.x + metadata.width <= game.x ? "two-rails" : "combined-rail"));

    if (window.BjgAndroid && typeof window.BjgAndroid.setGameRect === "function") {
      window.BjgAndroid.setGameRect(
        game.x / viewportWidth,
        game.y / viewportHeight,
        game.width / viewportWidth,
        game.height / viewportHeight
      );
    }
  }

  var observer = new MutationObserver(schedule);
  observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
  observer.observe(performancePanel, { attributes: true, attributeFilter: ["hidden"] });
  window.addEventListener("resize", schedule, { passive: true });
  window.addEventListener("orientationchange", schedule, { passive: true });
  if (window.visualViewport) window.visualViewport.addEventListener("resize", schedule, { passive: true });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(schedule);
  schedule();
}());
