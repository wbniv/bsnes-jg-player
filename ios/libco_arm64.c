/* iOS adaptation of libco v20's AArch64 backend (byuu, ISC license).
 * Single owner thread. Context layout matches the upstream backend exactly.
 * The switch routine is compiled into signed __TEXT, never generated/mprotect'd.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "libco/libco.h"

extern void bjg_co_swap(void *next, void *previous);
static _Thread_local uintptr_t host[64];
static _Thread_local cothread_t active;

cothread_t co_active(void) { return active ? active : (active = host); }
cothread_t co_derive(void *memory, unsigned size, void (*entry)(void)) {
    if (!memory || size < 1024) return NULL;
    uintptr_t *context = memory;
    memset(context, 0, 176);
    uintptr_t top = ((uintptr_t)memory + size) & ~(uintptr_t)15;
    context[0] = top;
    context[1] = (uintptr_t)entry;
    context[12] = top;
    return memory;
}
cothread_t co_create(unsigned size, void (*entry)(void)) {
    if (size < 1024) return NULL;
    return co_derive(malloc(size), size, entry);
}
void co_delete(cothread_t handle) { free(handle); }
void co_switch(cothread_t next) {
    cothread_t previous = co_active();
    active = next;
    bjg_co_swap(next, previous);
}
int co_serializable(void) { return 1; }
