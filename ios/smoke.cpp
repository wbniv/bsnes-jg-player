#include "CoreHost.hpp"
#include "DemoConfig.h"
#include <cstdio>
int main(int argc, char** argv) {
    if (argc != 3 || !PlayerCore::load(argv[1], argv[2])) return 1;
    for (int i = 0; i < DEMO_FRAMES; ++i) PlayerCore::frame();
    int word = PlayerCore::wramWord(DEMO_OFFSET);
    bool lit = false;
    for (unsigned y = 0; y < PlayerCore::height(); ++y)
        for (unsigned x = 0; x < PlayerCore::width(); ++x)
            lit |= (PlayerCore::pixels()[y * PlayerCore::pitch() + x] & 0xffffff) != 0;
    printf("frames=%d WRAM=%04x expected=%04x video=%ux%u nonblack=%d\n",
           DEMO_FRAMES, word, DEMO_WANT, PlayerCore::width(), PlayerCore::height(), lit);
    PlayerCore::stop();
    return word == DEMO_WANT && lit ? 0 : 1;
}
