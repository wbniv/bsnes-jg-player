/*
 * bsnes-jg-player — Emscripten frontend for bsnes-jg 2.1.0 (jgemu/bsnes), the
 * exact cycle-accurate SNES core the llvm-mos-65816 differential gate trusts.
 *
 * This drives the Jolly Good C++ API the same way the gate's headless harness
 * (dev/jgxcheck.cpp) does — identical callbacks, identical setup order, the same
 * audio/video specs — so emulation is byte-for-byte the gate's. Reading WRAM via
 * getMemoryRaw(MainRAM) reproduces the gate's fidelity assert in a browser tab:
 * mandel-display's on-console image hash lands at $0580 == 0x9103, exactly as it
 * does headless.
 *
 * A tiny C ABI is exported to JS (web/app.js): load a ROM, run one frame, read
 * the framebuffer and WRAM, set controller state. No SDL, no libretro, no
 * EmulatorJS — just the core and a canvas.
 */
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include <bsnes.hpp>
#include <emscripten.h>

// The SNES game database (boards.bml, SuperFamicom.bml, ...) is embedded into
// the wasm MEMFS at link time (--embed-file Database@/bsnes/Database).
static const std::string datapath = "/bsnes/Database";

static std::vector<uint8_t> game;
static std::string gamepath = "rom.sfc";
static uint32_t* vbuf = nullptr;          // framebuffer, pixels are 0x00RRGGBB
static float inbuf[3200];                 // resampled audio sink (discarded)
static unsigned g_w = 0, g_h = 0, g_pitch = 0;   // geometry of the last frame
static uint16_t g_pad[2] = {0, 0};        // current controller masks (JOY_* bits)
static bool g_loaded = false;

// --- bsnes-jg callbacks (mirroring dev/jgxcheck.cpp) -------------------------

static void logCallback(void*, int level, std::string& t) {
  if(level) fprintf(stderr, "bsnes: %s\n", t.c_str());
}
static bool fileOpenS(void*, std::string name, std::stringstream& ss) {
  std::ifstream fs(datapath + "/" + name, std::ios::in | std::ios::binary);
  if(!fs.is_open()) { fprintf(stderr, "bsnes-jg: missing data file %s\n", name.c_str()); return false; }
  ss << fs.rdbuf();
  return true;
}
static bool fileOpenV(void*, std::string, std::vector<uint8_t>&) { return false; }   // no save.ram/rtc
static bool fileOpenMsu(void*, std::string, std::istream**) { return false; }
static void fileWrite(void*, std::string, const uint8_t*, unsigned) {}               // discard SRAM writes
static bool loadRom(void*, unsigned id) {
  if(id == Bsnes::GameType::SuperFamicom && game.size() >= 0x8000) {
    Bsnes::setRomSuperFamicom(game, gamepath);
    return true;
  }
  return false;
}
static void videoFrame(const void*, unsigned width, unsigned height, unsigned pitch) {
  g_w = width; g_h = height; g_pitch = pitch;   // pixels live in vbuf, stride = pitch (uint32 px)
}
static void audioFrame(const void*, size_t) {}                                       // headless audio: discard
static int pollInput(const void*, unsigned port, unsigned /*id*/) {
  return port < 2 ? (int)g_pad[port] : 0;
}

// --- C ABI exported to JS ----------------------------------------------------

extern "C" {

// Load a Super Famicom ROM (raw .sfc/.smc bytes). Resets any prior session.
// Returns 1 on success, 0 on failure.
EMSCRIPTEN_KEEPALIVE
int bjg_load(const uint8_t* rom, int len) {
  if(g_loaded) { Bsnes::unload(); g_loaded = false; }
  if(len < 0x8000) return 0;
  game.assign(rom, rom + len);

  if(!vbuf) vbuf = (uint32_t*)calloc(256 * (240 + 8) * 4, sizeof(uint32_t));

  Bsnes::setOpenFileCallback(nullptr, fileOpenV);
  Bsnes::setOpenStreamCallback(nullptr, fileOpenS);
  Bsnes::setOpenMsuCallback(nullptr, fileOpenMsu);
  Bsnes::setRomLoadCallback(nullptr, loadRom);
  Bsnes::setWriteCallback(nullptr, fileWrite);
  Bsnes::setLogCallback(nullptr, logCallback);
  Bsnes::setAudioSpec({48000.0, (48000 / 60) << 1, 0, inbuf, nullptr, &audioFrame});
  Bsnes::setVideoSpec({vbuf, nullptr, &videoFrame});

  if(!Bsnes::load()) return 0;
  // Attach pads before power so the first automatic joypad latch has a live
  // device and callback. Reattach after power as well: this is harmless for
  // bsnes-jg and keeps the frontend robust if core initialization reconnects
  // either controller port while powering the machine.
  Bsnes::setInputSpec({0, Bsnes::Input::Device::Gamepad, nullptr, pollInput});
  Bsnes::setInputSpec({1, Bsnes::Input::Device::Gamepad, nullptr, pollInput});
  Bsnes::power();
  Bsnes::setInputSpec({0, Bsnes::Input::Device::Gamepad, nullptr, pollInput});
  Bsnes::setInputSpec({1, Bsnes::Input::Device::Gamepad, nullptr, pollInput});
  g_loaded = true;
  return 1;
}

EMSCRIPTEN_KEEPALIVE void      bjg_run(void)         { if(g_loaded) Bsnes::run(); }
EMSCRIPTEN_KEEPALIVE void      bjg_reset(void)       { if(g_loaded) Bsnes::reset(); }
EMSCRIPTEN_KEEPALIVE uint32_t* bjg_video(void)       { return vbuf; }
EMSCRIPTEN_KEEPALIVE int       bjg_video_w(void)     { return (int)g_w; }
EMSCRIPTEN_KEEPALIVE int       bjg_video_h(void)     { return (int)g_h; }
EMSCRIPTEN_KEEPALIVE int       bjg_video_pitch(void) { return (int)g_pitch; }   // in uint32 px
EMSCRIPTEN_KEEPALIVE int       bjg_loaded(void)      { return g_loaded ? 1 : 0; }

EMSCRIPTEN_KEEPALIVE void bjg_set_input(int port, int buttons) {
  if(port >= 0 && port < 2) g_pad[port] = (uint16_t)buttons;
}

// Direct view into Main RAM (WRAM) — the same pointer the gate reads via
// getMemoryRaw(MainRAM). The fidelity self-check reads bytes here.
EMSCRIPTEN_KEEPALIVE uint8_t* bjg_wram(void) {
  std::pair<void*, unsigned> m = Bsnes::getMemoryRaw(Bsnes::Memory::MainRAM);
  return (uint8_t*)m.first;
}
EMSCRIPTEN_KEEPALIVE int bjg_wram_size(void) {
  std::pair<void*, unsigned> m = Bsnes::getMemoryRaw(Bsnes::Memory::MainRAM);
  return (int)m.second;
}

} // extern "C"

// Emscripten entry point; all real work is driven from JS after instantiation.
int main() { return 0; }
