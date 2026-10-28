(function () {
  "use strict";

  var actions = document.getElementById("tv-actions");
  var exit = document.getElementById("tv-exit");
  if (!actions || !exit || document.getElementById("tv-share")) return;

  var button = document.createElement("button");
  button.id = "tv-share";
  button.innerHTML = '<svg class="menu-icon" viewBox="0 0 24 24" aria-hidden="true">' +
    '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>' +
    '<circle cx="18" cy="19" r="3"/><path d="m8.7 10.6 6.6-4.2M8.7 13.4l6.6 4.2"/>' +
    '</svg><span>Share app APK</span>';
  button.addEventListener("click", function () {
    if (window.BjgAndroid && window.BjgAndroid.shareApk) window.BjgAndroid.shareApk();
  });
  var beforeShare = document.createElement("div");
  beforeShare.className = "menu-divider";
  beforeShare.setAttribute("role", "separator");
  var beforeExit = document.createElement("div");
  beforeExit.className = "menu-divider";
  beforeExit.setAttribute("role", "separator");
  actions.insertBefore(beforeShare, exit);
  actions.insertBefore(button, exit);
  actions.insertBefore(beforeExit, exit);
}());
