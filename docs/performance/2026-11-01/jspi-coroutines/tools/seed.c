/* seed.c -- link-time override of libc clock() for fidelity builds only.
 * bsnes seeds power-on RAM from clock() (vendor/bsnes-jg/src/random.cpp:46), so whole-WRAM hashes differ
 * between any two runs of the same build. Linking this object into both the baseline and the candidate makes
 * the seed a constant, so WRAM hashes become comparable at every checkpoint. Never shipped. */
#include <time.h>
clock_t clock(void) { return 0; }
