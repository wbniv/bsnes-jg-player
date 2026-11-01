#!/usr/bin/env bash
set -euo pipefail
# link.sh NAME [extra em++ flags...] -- relink the bsnes-jg wasm from the existing archive into scratch
if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then echo "usage: [OUT=dir] link.sh NAME [extra em++ flags] -- relink core into \$OUT/builds/NAME (default /tmp/asyncify-trim); serve \$OUT with bench.html, pair.html and a roms/ symlink"; exit 0; fi
R="${REPO:-$(cd "$(dirname "$0")/../../../../.." && pwd)}"; S="${OUT:-/tmp/asyncify-trim}"; N=$1; shift
source $R/emsdk/emsdk_env.sh >/dev/null 2>&1
mkdir -p $S/builds/$N
EXPORTS='_bjg_load,_bjg_run,_bjg_reset,_bjg_video,_bjg_video_w,_bjg_video_h,_bjg_video_pitch,_bjg_loaded,_bjg_set_input,_bjg_wram,_bjg_wram_size,_malloc,_free,_main'
cd $R
em++ -O3 -std=c++11 -I"$R/vendor/bsnes-jg/src" "$R/web/src/main.cpp" "$R/vendor/bsnes-jg/objs/libbsnes.a" \
  -sASYNCIFY=1 -sASYNCIFY_STACK_SIZE=131072 -sMODULARIZE=1 -sEXPORT_NAME=BsnesJg -sALLOW_MEMORY_GROWTH=1 \
  -sINITIAL_MEMORY=67108864 -sEXPORTED_FUNCTIONS="$EXPORTS" -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,HEAPU8,HEAPU32 \
  -sENVIRONMENT=web --embed-file "$R/vendor/.embed/Database"@/bsnes/Database "$@" -o $S/builds/$N/bsnes_jg.js
ls -l $S/builds/$N/bsnes_jg.wasm | awk '{print $5}'; gzip -9c $S/builds/$N/bsnes_jg.wasm | wc -c; sha256sum $S/builds/$N/bsnes_jg.wasm $S/builds/$N/bsnes_jg.js
