#include "AudioRing.hpp"
#include "ControllerInput.hpp"
#include "PlayerTiming.hpp"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <thread>
#include <vector>

int main() {
    AudioRing ring;
    float in[] = {0.25f, -0.5f, 0.75f, -1.0f};
    float l[4], r[4];
    ring.push(in, 4); ring.render(l, r, 4);
    assert(l[0] == 0.25f && r[1] == -1 && l[2] == 0 && r[3] == 0);
    assert(ring.underrun == 2 && ring.rendered == 2);
    std::vector<float> full((AudioRing::capacity + 4) * 2, 0.5f);
    ring.push(full.data(), full.size());
    assert(ring.queued() == AudioRing::capacity && ring.dropped == 4);
    ring.clear(); ring.muted = true; ring.push(in, 4); ring.render(l, r, 2);
    assert(l[0] == 0 && r[1] == 0 && ring.queued() == 0);
    ring.muted = false;
    // Exercise wraparound and acquire/release publication with independent threads.
    constexpr unsigned count = 200000;
    std::thread producer([&] {
        for (unsigned i = 0; i < count;) {
            float pair[] = {float(i), -float(i)};
            if (ring.push(pair, 2)) ++i; else std::this_thread::yield();
        }
    });
    for (unsigned i = 0; i < count;) {
        if (!ring.queued()) { std::this_thread::yield(); continue; }
        ring.render(l, r, 1); assert(l[0] == float(i) && r[0] == -float(i)); ++i;
    }
    producer.join();
    for (unsigned hz : {60, 120}) {
        PlayerTiming clock;
        unsigned frames = 0;
        for (unsigned i = 0; i <= 10 * hz; ++i) frames += clock.advance(double(i) / hz);
        assert(frames == 600);
        assert(clock.advance(100) <= 3); // bounded after a stall
        clock.reset(); assert(clock.advance(200) == 0); // pause/resume discards debt
        assert(clock.advance(200 + 1.0/60) <= 1);
    }
    ControllerInput pad;
    pad.x = .2f; pad.y = -.2f; assert(pad.mask() == 0);
    pad.x = .8f; pad.y = .8f; assert(pad.mask() == ((1 << 8) | (1 << 11)));
    pad = {}; pad.south = pad.east = pad.north = pad.west = true;
    assert(pad.mask() == ((1 << 15) | (1 << 7) | (1 << 6) | (1 << 14)));
    pad = {}; pad.l = pad.r = pad.start = pad.select = true;
    assert(pad.mask() == ((1 << 5) | (1 << 4) | (1 << 12) | (1 << 13)));
    puts("PASS: audio stereo/underflow/overflow/mute/concurrency, controller mapping, 60/120 Hz timing and resume");
}
