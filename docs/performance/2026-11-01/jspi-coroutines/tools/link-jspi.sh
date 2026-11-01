#!/usr/bin/env bash
set -euo pipefail
# link-jspi.sh NAME [extra em++ flags...] -- build the JSPI libco backend, swap it into a scratch copy of
# libbsnes.a, and link the core with -sJSPI (no Asyncify pass) into $OUT/builds/NAME.
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then
  echo "usage: [OUT=dir] link-jspi.sh NAME [extra em++ flags] -- JSPI core into \$OUT/builds/NAME (default /tmp/jspi-coro)"; exit 0
fi
T="$(cd "$(dirname "$0")" && pwd)"
R="$(cd "$T/../../../../.." && pwd)"
M=/home/will/bsnes-jg-player            # main checkout: holds the built archive, vendor sources and emsdk
S="${OUT:-/tmp/jspi-coro}"; N=$1; shift
E=$M/emsdk
export EM_CONFIG=$E/.emscripten EMSDK=$E
export PATH=$E/upstream/emscripten:$E/upstream/bin:$E/node/22.16.0_64bit/bin:$PATH
mkdir -p "$S/builds/$N" "$S/obj"
# libco.o in the archive is deps/libco/libco.c, which #includes the selected backend; ours is self-contained.
emcc -O3 -c -I"$M/vendor/bsnes-jg/deps/libco" "$T/libco_jspi.c" -o "$S/obj/libco.o"
cp -f "$M/vendor/bsnes-jg/objs/libbsnes.a" "$S/obj/libbsnes-jspi.a"
emar r "$S/obj/libbsnes-jspi.a" "$S/obj/libco.o"
EXPORTS='_bjg_load,_bjg_run,_bjg_reset,_bjg_video,_bjg_video_w,_bjg_video_h,_bjg_video_pitch,_bjg_loaded,_bjg_set_input,_bjg_wram,_bjg_wram_size,_malloc,_free,_main,_co_jspi_enter'
em++ -O3 -std=c++11 -I"$M/vendor/bsnes-jg/src" "$R/web/src/main.cpp" "$S/obj/libbsnes-jspi.a" \
  -sJSPI=1 -sJSPI_EXPORTS="['bjg_run','co_jspi_enter']" --js-library "$T/libco_jspi.js" \
  -sMODULARIZE=1 -sEXPORT_NAME=BsnesJg -sALLOW_MEMORY_GROWTH=1 \
  -sINITIAL_MEMORY=67108864 -sEXPORTED_FUNCTIONS="$EXPORTS" -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,HEAPU8,HEAPU32 \
  -sENVIRONMENT=web --embed-file "$M/vendor/.embed/Database"@/bsnes/Database "$@" -o "$S/builds/$N/bsnes_jg.js"
stat -c %s "$S/builds/$N/bsnes_jg.wasm"; gzip -9c "$S/builds/$N/bsnes_jg.wasm" | wc -c
sha256sum "$S/builds/$N/bsnes_jg.wasm" "$S/builds/$N/bsnes_jg.js"
