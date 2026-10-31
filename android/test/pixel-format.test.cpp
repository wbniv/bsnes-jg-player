#include "../app/src/main/cpp/pixel-format.hpp"
#include <cassert>

int main() {
  const std::uint32_t colors[] = {0xff0000, 0x00ff00, 0x0000ff, 0x123456, 0, 0xffffff};
  const std::uint8_t expected[][4] = {
    {255, 0, 0, 255}, {0, 255, 0, 255}, {0, 0, 255, 255},
    {18, 52, 86, 255}, {0, 0, 0, 255}, {255, 255, 255, 255}
  };
  for (unsigned i = 0; i < 6; ++i) {
    std::uint8_t actual[4] = {};
    bjgRgba(colors[i], actual);
    for (unsigned channel = 0; channel < 4; ++channel)
      assert(actual[channel] == expected[i][channel]);
  }
}
