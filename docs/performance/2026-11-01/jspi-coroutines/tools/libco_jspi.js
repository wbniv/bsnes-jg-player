// JS half of the JSPI libco backend (libco_jspi.c). Link with --js-library.
// co_jspi_switch is a Suspending import (__async under -sJSPI): it returns a promise,
// so the engine suspends the calling wasm stack until another thread resolves it.
addToLibrary({
  $CoJspi: {
    pending: new Map(),   // co_jspi* -> {res, rej} for every suspended thread
    switches: 0,
    t0: 0,
    // Diagnostics for device runs: one BJG_TV_METRIC line at switch 1, 2, 4, 8, ... (about 23 per 5800 frames),
    // sent from inside the microtask chain, so a run that never returns from a frame still shows progress.
    log(event, extra) {
      if (!globalThis.BJG_TV_MODE || !globalThis.console) return;
      var now = (globalThis.performance ? performance.now() : 0);
      console.info('BJG_TV_METRIC ' + JSON.stringify(Object.assign({event: event, switches: CoJspi.switches,
        pending: CoJspi.pending.size, since_first_switch_ms: Math.round(now - CoJspi.t0)}, extra || {})));
    },
    fail(e) {
      // A trap on any thread stack: reject every waiter, so the host's bjg_run
      // promise rejects instead of hanging.
      var P = CoJspi.pending; CoJspi.pending = new Map();
      for (var w of P.values()) w.rej(e);
    },
  },
  co_jspi_forget__deps: ['$CoJspi'],
  co_jspi_forget: (t) => { CoJspi.pending.delete(t); },
  co_jspi_switch__deps: ['$CoJspi', 'co_jspi_enter', '$stackRestore'],
  co_jspi_switch__async: true,
  co_jspi_switch: (from, to) => {
    var P = CoJspi.pending;
    var n = ++CoJspi.switches;
    if (n === 1) CoJspi.t0 = globalThis.performance ? performance.now() : 0;
    if ((n & (n - 1)) === 0) CoJspi.log('jspi_progress', {from: from, to: to});
    var p = new Promise((res, rej) => P.set(from, {res, rej}));
    var w = P.get(to);
    if (w) {
      P.delete(to);
      w.res();
    } else if (!HEAPU32[(to + 20) >> 2]) {
      // First activation: run on a fresh engine stack with its own C stack.
      HEAPU32[(to + 20) >> 2] = 1;
      queueMicrotask(() => {
        stackRestore(HEAPU32[to >> 2]);
        CoJspi.log('jspi_thread_start', {thread: to});
        _co_jspi_enter(to).catch((e) => { CoJspi.log('jspi_error', {message: String(e && e.stack || e).slice(0, 1500)}); CoJspi.fail(e); });
      });
    } else {
      P.delete(from);
      throw new Error('co_jspi_switch: target ' + to + ' is neither suspended nor new');
    }
    return p;
  },
});
