#pragma once
#include <cstdint>

// bsnes emits packed 0x00RRGGBB, independently of host byte order.
inline void bjgRgba(std::uint32_t pixel, std::uint8_t* output) {
  output[0] = (pixel >> 16) & 255;
  output[1] = (pixel >> 8) & 255;
  output[2] = pixel & 255;
  output[3] = 255;
}
