#pragma once
#include <cstdint>
#include <string>

// Bootstrap adapter: one instance, all calls on the same thread (libco affinity).
namespace PlayerCore {
bool load(const std::string& rom, const std::string& database);
void frame();
void stop();
void buttons(uint16_t mask);
using AudioSink = void (*)(void*, const float*, size_t);
void audioSink(void* context, AudioSink sink);
uint16_t lastInput();
int wramWord(unsigned offset);
const uint32_t* pixels();
unsigned width();
unsigned height();
unsigned pitch();
}
