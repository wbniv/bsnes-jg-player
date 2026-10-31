cmake_minimum_required(VERSION 3.24)
project(BsnesPlayer LANGUAGES C CXX)
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
  enable_language(OBJCXX ASM)
endif()
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CORE "${CMAKE_CURRENT_SOURCE_DIR}/generated/bsnes-2.1.0")
file(GLOB_RECURSE CORE_CPP CONFIGURE_DEPENDS "${CORE}/src/*.cpp" "${CORE}/deps/byuuML/*.cpp")
list(FILTER CORE_CPP EXCLUDE REGEX "/src/expansion/21fx\\.cpp$")
set(CORE_C
  ${CORE}/deps/gb/apu.c ${CORE}/deps/gb/camera.c ${CORE}/deps/gb/display.c
  ${CORE}/deps/gb/gb.c ${CORE}/deps/gb/joypad.c ${CORE}/deps/gb/mbc.c
  ${CORE}/deps/gb/memory.c ${CORE}/deps/gb/printer.c ${CORE}/deps/gb/random.c
  ${CORE}/deps/gb/rumble.c ${CORE}/deps/gb/save_state.c ${CORE}/deps/gb/sgb.c
  ${CORE}/deps/gb/sm83_cpu.c ${CORE}/deps/gb/timing.c ${CORE}/deps/gb/workboy.c
   ${CORE}/deps/snes_spc/spc_dsp.c
  ${CORE}/deps/libsamplerate/samplerate.c ${CORE}/deps/libsamplerate/src_linear.c
  ${CORE}/deps/libsamplerate/src_sinc.c ${CORE}/deps/libsamplerate/src_zoh.c)

add_library(core STATIC CoreHost.cpp ${CORE_CPP} ${CORE_C})
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
  target_sources(core PRIVATE libco_arm64.c libco_arm64.S)
else()
  target_sources(core PRIVATE ${CORE}/deps/libco/libco.c)
endif()
target_include_directories(core PRIVATE "${CORE}/src" "${CORE}/deps" "${CORE}/deps/libsamplerate")
target_compile_definitions(core PRIVATE GB_INTERNAL GB_DISABLE_CHEATS GB_DISABLE_CHEAT_SEARCH GB_DISABLE_DEBUGGER GB_DISABLE_REWIND _GNU_SOURCE GB_VERSION="1.0.2")
target_compile_options(core PRIVATE -Wno-multichar -Wno-unused-parameter)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "iOS")
  add_executable(core-smoke smoke.cpp)
  target_include_directories(core-smoke PRIVATE generated)
  target_link_libraries(core-smoke PRIVATE core)
  return()
endif()
file(GLOB DATABASE "${CORE}/Database/*.bml")
set_source_files_properties(${DATABASE} PROPERTIES MACOSX_PACKAGE_LOCATION Resources/Database)
set(RESOURCES generated/demo.sfc generated/demo-rom.json generated/LICENSE.txt generated/NOTICE.txt libco-LICENSE.txt)
set_source_files_properties(${RESOURCES} PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
add_executable(BsnesPlayer MACOSX_BUNDLE Player.mm ${RESOURCES} ${DATABASE})
target_include_directories(BsnesPlayer PRIVATE generated)
target_compile_options(BsnesPlayer PRIVATE -fobjc-arc)
target_link_libraries(BsnesPlayer PRIVATE core "-framework Foundation" "-framework UIKit" "-framework CoreGraphics" "-framework MetalKit" "-framework Metal" "-framework QuartzCore")
set_target_properties(BsnesPlayer PROPERTIES
  MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist"
  XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER org.bsnesjg.player.ios
  XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1,2"
  XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED NO
  XCODE_ATTRIBUTE_ENABLE_BITCODE NO
  XCODE_GENERATE_SCHEME TRUE)
