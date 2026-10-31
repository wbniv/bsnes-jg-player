#pragma once
#include <algorithm>
#include <cmath>

class PlayerTiming {
public:
    static constexpr double rate = 60.0988;
    void reset() { last_ = -1; credit_ = 0; }
    unsigned advance(double now) {
        if (last_ < 0) { last_ = now; return 0; }
        auto elapsed = std::max(0.0, now - last_);
        last_ = now;
        credit_ = std::min(credit_ + elapsed, 3.0 / rate);
        auto frames = static_cast<unsigned>(std::floor(credit_ * rate + 1e-9));
        credit_ -= frames / rate;
        return frames;
    }
private:
    double last_ = -1, credit_ = 0;
};
