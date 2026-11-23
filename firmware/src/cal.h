#pragma once

#include <stdint.h>

#include "scale.h"

// Twelve channels: LC1..LC3, PT1..PT6, TC1..TC3, in that order.
static constexpr uint8_t CAL_CHANNELS = 12;
static constexpr uint8_t CAL_MAX_POINTS = 8;

struct ChannelCal {
    float slope;
    float offset;
    uint8_t nPoints;
    FitPoint points[CAL_MAX_POINTS];
    float tare;
    bool fromEeprom;
    bool dirty;
    bool hasZero;
    float zeroRaw;
};

inline float evalChannel(const ChannelCal& cal, float raw) {
    return applyFit(raw, cal.slope, cal.offset, cal.points, cal.nPoints, cal.tare);
}

// Untared value. CAL ZERO / the tare button capture this, not the displayed number.
inline float evalUntared(const ChannelCal& cal, float raw) {
    return applyFit(raw, cal.slope, cal.offset, cal.points, cal.nPoints, 0.0f);
}
