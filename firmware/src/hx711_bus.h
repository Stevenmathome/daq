#pragma once

#include <stdint.h>

// Read three HX711s that share PD_SCK.
// `ready` is sampled before the first clock. A channel whose DOUT was still
// high is marked not ready; its word is still clocked (the shared clock
// cannot skip a chip) but the caller should ignore it.
// Exactly 25 clocks are issued: 24 data bits, then one extra so the next
// conversion stays on channel A, gain 128.
void hx711Read(int32_t raw[3], bool ready[3]);
