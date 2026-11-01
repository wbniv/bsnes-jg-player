/*
 * libco backend for WebAssembly using JSPI (JavaScript Promise Integration).
 *
 * Experimental alternative to web/src/libco_emscripten.c. That backend uses
 * Emscripten fibers, which exist only under Asyncify (ASYNCIFY == 1); under
 * -sJSPI Emscripten 6.0.4 has no fiber implementation. Here every libco thread is
 * its own engine stack:
 *   - a new thread starts as a call of the promising export co_jspi_enter();
 *   - co_switch() calls the Suspending import co_jspi_switch(), which resolves the
 *     target thread's pending promise (or starts it) and returns a promise of its
 *     own, so the engine suspends the current stack until someone switches back.
 * No function is instrumented. JSPI does not switch Emscripten's linear-memory
 * stack (__stack_pointer), so each thread saves it before suspending and
 * restores it, with its limits, as soon as the import returns.
 *
 * Link: -sJSPI -sJSPI_EXPORTS=['bjg_run','co_jspi_enter'] --js-library libco_jspi.js
 * Build: compiled as libco.o and swapped into a copy of libbsnes.a.
 */
#define LIBCO_C
#include "libco.h"

#include <stdlib.h>
#include <stdint.h>
#include <emscripten.h>
#include <emscripten/stack.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef LIBCO_JSPI_CSTACK
#define LIBCO_JSPI_CSTACK (1u << 20)   /* 1 MiB linear-memory stack per thread */
#endif

/* Field offsets are read by libco_jspi.js: keep in sync (all 4-byte on wasm32). */
typedef struct {
  uintptr_t sp;            /* +0  saved __stack_pointer while suspended          */
  uintptr_t base;          /* +4  stack base (highest address)                   */
  uintptr_t limit;         /* +8  stack end (lowest address)                     */
  void (*entry)(void);     /* +12 thread entrypoint                              */
  unsigned char* cstack;   /* +16 owned stack memory (0 for the primary thread)  */
  uintptr_t started;       /* +20 1 once co_jspi_enter has run for this thread   */
} co_jspi;

/* JS side (libco_jspi.js). */
extern void co_jspi_switch(co_jspi* from, co_jspi* to);  /* Suspending import */
extern void co_jspi_forget(co_jspi* t);                  /* drop a pending resolver */
extern void _emscripten_stack_restore(uintptr_t sp);

static co_jspi co_primary;
static co_jspi* co_running = 0;

static void ensure_primary(void) {
  if(co_running) return;
  co_primary.base = emscripten_stack_get_base();
  co_primary.limit = emscripten_stack_get_end();
  co_primary.started = 1;
  co_running = &co_primary;
}

/* Promising export: the first activation of a thread. JS has already set the
 * stack pointer to t->sp (the top of t's stack). libco entrypoints never return. */
EMSCRIPTEN_KEEPALIVE void co_jspi_enter(co_jspi* t) {
  emscripten_stack_set_limits((void*)t->base, (void*)t->limit);
  t->entry();
  for(;;) co_switch((cothread_t)&co_primary);
}

static co_jspi* co_setup(co_jspi* t, unsigned int size, void (*entry)(void)) {
  unsigned int cs = size < LIBCO_JSPI_CSTACK ? LIBCO_JSPI_CSTACK : size;
  if(!t->cstack) t->cstack = (unsigned char*)malloc(cs);
  if(!t->cstack) return 0;
  co_jspi_forget(t);       /* an old suspended stack for this record is abandoned */
  t->entry = entry;
  t->limit = (uintptr_t)t->cstack;
  t->base = ((uintptr_t)t->cstack + cs) & ~(uintptr_t)15;
  t->sp = t->base;
  t->started = 0;
  return t;
}

cothread_t co_active(void) {
  ensure_primary();
  return (cothread_t)co_running;
}

cothread_t co_create(unsigned int size, void (*entry)(void)) {
  ensure_primary();
  co_jspi* t = (co_jspi*)calloc(1, sizeof(co_jspi));
  if(!t) return 0;
  if(!co_setup(t, size, entry)) { free(t); return 0; }
  return (cothread_t)t;
}

/* bsnes hands back a handle from a previous co_create to re-init it in place
 * (src/sfc.cpp Thread::create), as in libco_emscripten.c. */
cothread_t co_derive(void* memory, unsigned int size, void (*entry)(void)) {
  ensure_primary();
  if(!memory) return 0;
  return (cothread_t)co_setup((co_jspi*)memory, size, entry);
}

void co_delete(cothread_t handle) {
  co_jspi* t = (co_jspi*)handle;
  if(!t || t == &co_primary) return;
  co_jspi_forget(t);
  free(t->cstack);
  free(t);
}

void co_switch(cothread_t handle) {
  co_jspi* self = co_running;
  co_jspi* to = (co_jspi*)handle;
  if(to == self) return;
  co_running = to;
  self->sp = emscripten_stack_get_current();
  co_jspi_switch(self, to);
  /* resumed: our engine stack is back; put our linear-memory stack back too */
  _emscripten_stack_restore(self->sp);
  emscripten_stack_set_limits((void*)self->base, (void*)self->limit);
}

int co_serializable(void) {
  return 0;
}

#ifdef __cplusplus
}
#endif
