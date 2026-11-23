#pragma once

#include <stdint.h>

void dispBegin();
// Render a value on display 0..2. Non-finite values show as "----".
void dispShow(uint8_t index, float value);
// Four characters. Used for the E-stop words STOP and RST.
void dispShowText(uint8_t index, const char text[4]);
void dispClear(uint8_t index);
