#pragma once

// value = slope * raw + offset
//
// raw is HX711 counts, sensor volts before the divider, or the MAX31856
// degC, depending on the channel. A point table of at least two points
// replaces the line. Past either end, the end segment is extended.
//
// Keep this identical to firmware/scripts/scaling.py.

#include <stdint.h>

#include "pins.h"

struct FitPoint {
    float raw;
    float value;
};

inline float pinVoltsFromCounts(uint16_t counts) {
    return (static_cast<float>(counts) / static_cast<float>(ADC_MAX_COUNT)) * ADC_VREF;
}

// The 10k/20k divider: Vsensor = Vpin * (10k + 20k) / 20k.
inline float sensorVoltsFromCounts(uint16_t counts) {
    return pinVoltsFromCounts(counts) * PT_DIVIDER;
}

inline float applyLinear(float raw, float slope, float offset) {
    return slope * raw + offset;
}

inline float lerpSegment(float raw, float raw0, float value0, float raw1, float value1) {
    const float span = raw1 - raw0;
    if (span == 0.0f) {
        return value0;
    }
    return value0 + (raw - raw0) / span * (value1 - value0);
}

inline float piecewise(float raw, const FitPoint* points, uint8_t count) {
    if (count < 2) {
        return 0.0f;
    }
    if (raw <= points[0].raw) {
        return lerpSegment(raw, points[0].raw, points[0].value, points[1].raw, points[1].value);
    }
    const uint8_t last = static_cast<uint8_t>(count - 1);
    if (raw >= points[last].raw) {
        return lerpSegment(
            raw, points[last - 1].raw, points[last - 1].value, points[last].raw, points[last].value);
    }
    for (uint8_t i = 1; i < count; ++i) {
        if (raw <= points[i].raw) {
            return lerpSegment(
                raw, points[i - 1].raw, points[i - 1].value, points[i].raw, points[i].value);
        }
    }
    return points[last].value;
}

// Tare is subtracted after the line or the table. It is not stored.
inline float applyFit(float raw, float slope, float offset, const FitPoint* points, uint8_t count, float tare) {
    const float base = (count >= 2) ? piecewise(raw, points, count) : applyLinear(raw, slope, offset);
    return base - tare;
}
