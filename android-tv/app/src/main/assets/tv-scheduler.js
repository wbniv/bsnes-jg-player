(function (root) {
  "use strict";

  function create(rateHz, maxSteps) {
    var rate = Number(rateHz);
    var cap = Number(maxSteps);
    if (!(rate > 0) || !(cap >= 1)) throw new Error("invalid frame scheduler configuration");
    var previous = null;
    var credit = 0;
    return {
      advance: function (timestampMs) {
        var now = Number(timestampMs);
        if (!Number.isFinite(now)) throw new Error("frame timestamp must be finite");
        var elapsed = previous === null ? 1000 / rate : Math.max(0, now - previous);
        previous = now;
        credit += elapsed * rate / 1000;
        var steps = Math.min(Math.floor(credit), cap);
        credit -= steps;
        return { steps: steps, pending: credit };
      },
      reset: function () { previous = null; credit = 0; },
      pending: function () { return credit; }
    };
  }

  root.BJGFrameScheduler = { create: create };
}(typeof globalThis !== "undefined" ? globalThis : this));
