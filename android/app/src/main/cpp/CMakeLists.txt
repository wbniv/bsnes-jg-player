cmake_minimum_required(VERSION 3.22.1)
project(bjg_native LANGUAGES C CXX)
set(CORE "${CMAKE_CURRENT_LIST_DIR}/../../../../../vendor/bsnes-jg")
file(GLOB_RECURSE CORE_CPP CONFIGURE_DEPENDS "${CORE}/src/*.cpp" "${CORE}/deps/byuuML/*.cpp")
list(FILTER CORE_CPP EXCLUDE REGEX "/src/expansion/21fx\\.cpp$")
set(CORE_C
  ${CORE}/deps/gb/apu.c ${CORE}/deps/gb/camera.c ${CORE}/deps/gb/display.c
  ${CORE}/deps/gb/gb.c ${CORE}/deps/gb/joypad.c ${CORE}/deps/gb/mbc.c
  ${CORE}/deps/gb/memory.c ${CORE}/deps/gb/printer.c ${CORE}/deps/gb/random.c
  ${CORE}/deps/gb/rumble.c ${CORE}/deps/gb/save_state.c ${CORE}/deps/gb/sgb.c
  ${CORE}/deps/gb/sm83_cpu.c ${CORE}/deps/gb/timing.c ${CORE}/deps/gb/workboy.c
  ${CORE}/deps/libco/libco.c ${CORE}/deps/snes_spc/spc_dsp.c
  ${CORE}/deps/libsamplerate/samplerate.c ${CORE}/deps/libsamplerate/src_linear.c
  ${CORE}/deps/libsamplerate/src_sinc.c ${CORE}/deps/libsamplerate/src_zoh.c)
add_library(bjg SHARED jni.cpp ${CORE_CPP} ${CORE_C})
target_include_directories(bjg PRIVATE "${CORE}/src" "${CORE}/deps" "${CORE}/deps/libsamplerate")
target_compile_definitions(bjg PRIVATE GB_INTERNAL GB_DISABLE_CHEATS GB_DISABLE_CHEAT_SEARCH GB_DISABLE_DEBUGGER GB_DISABLE_REWIND _GNU_SOURCE GB_VERSION=\"1.0.2\")
target_compile_options(bjg PRIVATE -Wno-unused-parameter -Wno-multichar -fvisibility=hidden)
# Measured on Chromecast HD (Cortex-A35, 32-bit), frame-5800 job, 2026-10-31:
# adding -O3 and/or -flto=thin made the core 0.64x as fast (100 ms vs 64 ms per
# frame); -march=armv8-a -mfpu=neon-fp-armv8 alone changed nothing (0.996x).
# Do not add them without re-running that job.
# docs/performance/2026-10-31/cast1-armv7-tuning/report.md
# NDK r26 defaults ELF load segments to 4 KB; Pixel's 16 KB page-size check
# requires each native LOAD segment to use 16 KB alignment.
target_link_options(bjg PRIVATE "-Wl,-z,max-page-size=16384" "-Wl,-z,common-page-size=16384")
# libco's ARM backend restores the new coroutine entry point with an ARM
# `ldmia ... {pc}` instruction. That form does not switch from ARM to Thumb
# state on entry, so Thumb-compiled core callbacks fault on ARMv7. Compile the
# native library in ARM state for 32-bit Android; arm64 is unaffected.
if(ANDROID_ABI STREQUAL "armeabi-v7a")
  target_compile_options(bjg PRIVATE -marm)
endif()
target_link_libraries(bjg android log)
