#pragma once
#include <cstdint>

struct ControllerInput {
    float x = 0, y = 0;
    bool up = false, down = false, left = false, right = false;
    bool south = false, east = false, west = false, north = false;
    bool l = false, r = false, start = false, select = false;
    uint16_t mask() const {
        // Map by physical SNES position: south=B, east=A, west=Y, north=X.
        return ((up || y > 0.25f) << 11) | ((down || y < -0.25f) << 10)
            | ((left || x < -0.25f) << 9) | ((right || x > 0.25f) << 8)
            | (south << 15) | (east << 7) | (west << 14) | (north << 6)
            | (l << 5) | (r << 4) | (start << 12) | (select << 13);
    }
};
