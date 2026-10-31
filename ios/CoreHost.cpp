#include "CoreHost.hpp"
#include <bsnes.hpp>
#include <settings.hpp>
#include <fstream>
#include <sstream>
#include <iterator>
#include <cstdio>

namespace {
std::vector<uint8_t> rom;
std::string romPath, databasePath;
uint32_t videoBuffer[512 * 512]{};
float audioBuffer[3200]{};
unsigned frameWidth = 0, frameHeight = 0, framePitch = 0;
uint16_t pad = 0;
uint16_t lastObservedPad = 0;
PlayerCore::AudioSink sink = nullptr;
void* sinkContext = nullptr;
bool loaded = false;
bool stream(void*, std::string name, std::stringstream& out) {
    std::ifstream file(databasePath + "/" + name, std::ios::binary);
    if (!file) return false;
    out << file.rdbuf();
    return true;
}
bool file(void*, std::string, std::vector<uint8_t>&) { return false; }
bool msu(void*, std::string, std::istream**) { return false; }
void write(void*, std::string, const uint8_t*, unsigned) {}
void log(void*, int level, std::string& text) { if (level) fprintf(stderr, "%s\n", text.c_str()); }
bool loadRom(void*, unsigned id) {
    if (id != Bsnes::GameType::SuperFamicom) return false;
    Bsnes::setRomSuperFamicom(rom, romPath);
    return true;
}
void video(const void*, unsigned w, unsigned h, unsigned p) {
    if (w > 512 || h > 512 || p < w || p * h > 512 * 512) std::abort();
    frameWidth = w; frameHeight = h; framePitch = p;
}
void audio(const void*, size_t count) { if (sink) sink(sinkContext, audioBuffer, count); }
int input(const void*, unsigned port, unsigned) {
    if (port != 0) return 0;
    if (pad) lastObservedPad = pad;
    return pad;
}
void attach() {
    Bsnes::setAudioSpec({48000.0, 1600, 0, audioBuffer, nullptr, audio});
    Bsnes::setInputSpec({0, Bsnes::Input::Device::Gamepad, nullptr, input});
    Bsnes::setInputSpec({1, Bsnes::Input::Device::Gamepad, nullptr, input});
}
}
bool PlayerCore::load(const std::string& path, const std::string& database) {
    stop();
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    rom.assign(std::istreambuf_iterator<char>(in), {});
    if (rom.size() < 32768) return false;
    romPath = path; databasePath = database;
    frameWidth = frameHeight = framePitch = 0; pad = lastObservedPad = 0;
    Bsnes::setOpenFileCallback(nullptr, file);
    Bsnes::setOpenStreamCallback(nullptr, stream);
    Bsnes::setOpenMsuCallback(nullptr, msu);
    Bsnes::setWriteCallback(nullptr, write);
    Bsnes::setLogCallback(nullptr, log);
    Bsnes::setRomLoadCallback(nullptr, loadRom);
    Bsnes::setVideoSpec({videoBuffer, nullptr, video});
    // Match jgxcheck's deterministic picture/fidelity baseline.
    SuperFamicom::configuration.entropy = 0;
    attach();
    if (!Bsnes::load()) return false;
    loaded = true;
    Bsnes::power();
    attach();
    return true;
}
void PlayerCore::frame() { if (loaded) Bsnes::run(); }
void PlayerCore::stop() { if (loaded) Bsnes::unload(); loaded = false; pad = 0; }
void PlayerCore::buttons(uint16_t mask) { pad = mask; }
void PlayerCore::audioSink(void* context, AudioSink callback) { sinkContext = context; sink = callback; }
uint16_t PlayerCore::lastInput() { return lastObservedPad; }
int PlayerCore::wramWord(unsigned offset) {
    if (!loaded) return -1;
    auto m = Bsnes::getMemoryRaw(Bsnes::Memory::MainRAM);
    if (!m.first || m.second < 2 || offset >= m.second - 1) return -1;
    const auto* bytes = static_cast<const uint8_t*>(m.first);
    return bytes[offset] | (bytes[offset + 1] << 8);
}
const uint32_t* PlayerCore::pixels() { return videoBuffer; }
unsigned PlayerCore::width() { return frameWidth; }
unsigned PlayerCore::height() { return frameHeight; }
unsigned PlayerCore::pitch() { return framePitch; }
