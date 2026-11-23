#pragma once

#include <stdint.h>

// Thermocouple type codes match the MAX31856 CR1 low nibble.
// B=0 E=1 J=2 K=3 N=4 R=5 S=6 T=7.
void tcBegin();
void tcConfigure(uint8_t index, uint8_t typeCode);
// Reads linearized temperature. Returns false when the fault register is
// non-zero or the part does not answer. `fault` is the SR byte (0xFF if mute).
bool tcRead(uint8_t index, float* celsius, uint8_t* fault);
