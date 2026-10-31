// libco v20 AArch64 context switch, byuu (ISC), assembled into signed code.
.text
.p2align 2
.globl _bjg_co_swap
_bjg_co_swap:
    mov x16, sp
    stp x16, x30, [x1]
    ldp x16, x30, [x0]
    mov sp, x16
    stp x19, x20, [x1, #16]
    ldp x19, x20, [x0, #16]
    stp x21, x22, [x1, #32]
    ldp x21, x22, [x0, #32]
    stp x23, x24, [x1, #48]
    ldp x23, x24, [x0, #48]
    stp x25, x26, [x1, #64]
    ldp x25, x26, [x0, #64]
    stp x27, x28, [x1, #80]
    ldp x27, x28, [x0, #80]
    str x29, [x1, #96]
    ldr x29, [x0, #96]
    stp d8, d9, [x1, #112]
    ldp d8, d9, [x0, #112]
    stp d10, d11, [x1, #128]
    ldp d10, d11, [x0, #128]
    stp d12, d13, [x1, #144]
    ldp d12, d13, [x0, #144]
    stp d14, d15, [x1, #160]
    ldp d14, d15, [x0, #160]
    br x30
