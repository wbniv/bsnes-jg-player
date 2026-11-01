#!/usr/bin/env bash
set -euo pipefail
# pingpong.sh -- build the libco switch microbenchmark for both backends into $OUT/builds/pp-{asyncify,jspi}
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then echo "usage: [OUT=dir] pingpong.sh -- build pp-asyncify and pp-jspi (default OUT /tmp/jspi-coro)"; exit 0; fi
T="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$T/../../../../.." && pwd)"
M=/home/will/bsnes-jg-player; S="${OUT:-/tmp/jspi-coro}"; E=$M/emsdk
export EM_CONFIG=$E/.emscripten EMSDK=$E PATH=$E/upstream/emscripten:$E/upstream/bin:$E/node/22.16.0_64bit/bin:$PATH
L=$M/vendor/bsnes-jg/deps/libco
mkdir -p "$S/builds/pp-asyncify" "$S/builds/pp-jspi"
COMMON=(-O3 -I"$L" -sMODULARIZE=1 -sEXPORT_NAME=BsnesJg -sENVIRONMENT=web -sEXPORTED_FUNCTIONS=_pp_run,_main)
emcc "${COMMON[@]}" "$T/pingpong.c" "$R/web/src/libco_emscripten.c" -sASYNCIFY=1 -sASYNCIFY_STACK_SIZE=131072 \
  -o "$S/builds/pp-asyncify/bsnes_jg.js"
emcc "${COMMON[@]}" "$T/pingpong.c" "$T/libco_jspi.c" -sJSPI=1 -sJSPI_EXPORTS="['pp_run','co_jspi_enter']" \
  -sEXPORTED_FUNCTIONS=_pp_run,_main,_co_jspi_enter -sEXPORTED_RUNTIME_METHODS=HEAPU32 --js-library "$T/libco_jspi.js" \
  -o "$S/builds/pp-jspi/bsnes_jg.js"
ls -l "$S"/builds/pp-*/bsnes_jg.wasm
