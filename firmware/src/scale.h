#pragma once

// Engineering-unit conversions for the Rev B front end.
// Keep the arithmetic identical to firmware/scripts/scaling.py.
// tests/test_scaling.py locks the numbers.

#include <stdint.h>

#include "pins.h"

inline float pinVoltsFromCounts(uint16_t counts) {
    return (static_cast<float>(counts) / static_cast<float>(ADC_MAX_COUNT)) * ADC_VREF;
}

// The 10k/20k divider: Vsensor = Vpin * (10k + 20k) / 20k.
inline float sensorVoltsFromCounts(uint16_t counts) {
    return pinVoltsFromCounts(counts) * PT_DIVIDER;
}

// zeroVolts and fullScaleVolts are sensor volts, before the divider.
inline float pressurePsi(uint16_t counts, float zeroVolts, float fullScaleVolts, float fullScalePsi) {
    const float span = fullScaleVolts - zeroVolts;
    if (span == 0.0f) {
        return 0.0f;
    }
    const float sensor = sensorVoltsFromCounts(counts);
    return (sensor - zeroVolts) / span * fullScalePsi;
}

// countsPerUnit is HX711 counts per engineering unit, after tare.
// A negative factor flips a cell whose green/white pair is swapped.
inline float loadEu(int32_t raw, float tare, float countsPerUnit) {
    if (countsPerUnit == 0.0f) {
        return 0.0f;
    }
    return (static_cast<float>(raw) - tare) / countsPerUnit;
}
