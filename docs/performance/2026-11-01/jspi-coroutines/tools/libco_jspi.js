// JS half of the JSPI libco backend (libco_jspi.c). Link with --js-library.
// co_jspi_switch is a Suspending import (__async under -sJSPI): it returns a promise,
// so the engine suspends the calling wasm stack until another thread resolves it.
addToLibrary({
  $CoJspi: {
    pending: new Map(),   // co_jspi* -> {res, rej} for every suspended thread
    switches: 0,
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
    CoJspi.switches++;
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
        _co_jspi_enter(to).catch(CoJspi.fail);
      });
    } else {
      P.delete(from);
      throw new Error('co_jspi_switch: target ' + to + ' is neither suspended nor new');
    }
    return p;
  },
});
