#include "hx711_bus.h"

#include <Arduino.h>

#include "pins.h"

static int32_t signExtend24(uint32_t word) {
    if (word & 0x800000u) {
        word |= 0xFF000000u;
    }
    return static_cast<int32_t>(word);
}

void hx711Read(int32_t raw[3], bool ready[3]) {
    uint32_t bits[3] = {0, 0, 0};
    for (int ch = 0; ch < 3; ++ch) {
        ready[ch] = digitalRead(PIN_LC_DOUT[ch]) == LOW;
    }

    // DOUT is valid while PD_SCK is high. Sample every data pin on that
    // same high time so the three chips stay locked to one clock.
    for (int i = 0; i < 24; ++i) {
        digitalWriteFast(PIN_LC_SCK, HIGH);
        delayMicroseconds(1);
        for (int ch = 0; ch < 3; ++ch) {
            bits[ch] = (bits[ch] << 1) | (digitalRead(PIN_LC_DOUT[ch]) ? 1u : 0u);
        }
        digitalWriteFast(PIN_LC_SCK, LOW);
        delayMicroseconds(1);
    }

    // 25th pulse: next conversion is channel A, gain 128.
    digitalWriteFast(PIN_LC_SCK, HIGH);
    delayMicroseconds(1);
    digitalWriteFast(PIN_LC_SCK, LOW);

    for (int ch = 0; ch < 3; ++ch) {
        raw[ch] = signExtend24(bits[ch]);
    }
}
