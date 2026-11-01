/* pingpong.c -- cost of one libco switch, on whichever backend it is linked against.
 * pp_run(n) bounces host -> A -> host ... n times (2n switches) and returns.
 * Built twice by pingpong.sh: Asyncify fibers (web/src/libco_emscripten.c) and JSPI (libco_jspi.c). */
#include <emscripten.h>
#include "libco.h"
static cothread_t host, a;
static volatile int counter;
static void entry(void) { for(;;) { counter++; co_switch(host); } }
EMSCRIPTEN_KEEPALIVE int pp_run(int n) {
  host = co_active();
  if(!a) a = co_create(65536, entry);
  for(int i = 0; i < n; i++) co_switch(a);
  return counter;
}
int main(void) { return 0; }
