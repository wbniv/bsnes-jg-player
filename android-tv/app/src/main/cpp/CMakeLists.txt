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
target_link_libraries(bjg android log)
