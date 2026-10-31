#pragma once
#include <cstdint>
#include <string>

// Bootstrap adapter: one instance, all calls on the same thread (libco affinity).
namespace PlayerCore {
bool load(const std::string& rom, const std::string& database);
void frame();
void stop();
void buttons(uint16_t mask);
int wramWord(unsigned offset);
const uint32_t* pixels();
unsigned width();
unsigned height();
unsigned pitch();
}
