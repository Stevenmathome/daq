#pragma once

#include <stdint.h>

// Pin map for DAQ Rev B, checked against the KiCad schematic
// (DAQ Rev B.kicad_sch, KiCad 9.0.2) and the Rev B change report.
// Numbers are Arduino pin numbers on the Teensy 4.1.

// HX711 load cells. One shared PD_SCK, one DOUT each.
// U3 DOUT = LC1 = pin 3, U4 DOUT = LC2 = pin 0, U5 DOUT = LC3 = pin 1.
// RATE (pin 15 of each HX711) is tied to GND, so the chips run at 10 SPS.
// RATE is not on a Teensy pin; 80 SPS is not selectable in software.
constexpr uint8_t PIN_LC_SCK = 2;
constexpr uint8_t PIN_LC_DOUT[3] = {3, 0, 1};

// Four-pin display headers J29, J30, J31 (TM1637-style).
// Header pin 1 = +5V, 2 = GND, 3 = CLK, 4 = DIO.
constexpr uint8_t PIN_DISP_CLK[3] = {4, 6, 8};
constexpr uint8_t PIN_DISP_DIO[3] = {5, 7, 9};

// MAX31856 thermocouples on the hardware SPI bus.
// DRDY and FAULT are no-connects; the firmware polls the status register.
// U6 CS = TC1 = pin 23, U7 CS = TC2 = pin 22, U8 CS = TC3 = pin 21.
constexpr uint8_t PIN_TC_MOSI = 11;
constexpr uint8_t PIN_TC_MISO = 12;
constexpr uint8_t PIN_TC_SCK = 13;
constexpr uint8_t PIN_TC_CS[3] = {23, 22, 21};

// Pressure transducers PD_1..PD_6 on A6..A1.
// 10k series / 20k to GND, 100 nF at the pin. 4.5 V at the sensor is 3.0 V here.
constexpr uint8_t PIN_PT[6] = {20, 19, 18, 17, 16, 15};

// Low-side AO3400A outputs. HIGH turns the MOSFET on.
// Valves 1..6 are pins 24..29. Pin 30 is the extra 12 V output (Q7).
constexpr uint8_t PIN_VALVE[7] = {24, 25, 26, 27, 28, 29, 30};

// Digital inputs. The schematic does not wire these in DI-number order.
// DI1=38, DI2=37, DI3=36, DI4=35, DI5=34, DI6=33, DI7=31, DI8=32.
// Each input has a 10k pulldown to GND and is switched to +3V3. HIGH = closed.
constexpr uint8_t PIN_DI[8] = {38, 37, 36, 35, 34, 33, 31, 32};

// GPIOs the Rev B schematic leaves unused. The E-stop sense pin is not one
// of these by law: config.yaml chooses it. These are the ones that do not
// already belong to a sensor, a display, or a valve.
//   10, 14 (A0), 39, 40, 41

constexpr float ADC_VREF = 3.3f;
constexpr int ADC_MAX_COUNT = 4095;
// Vsensor = Vpin * (10k + 20k) / 20k.
constexpr float PT_DIVIDER = 1.5f;
constexpr float PT_ZERO_V = 0.5f;
constexpr float PT_FS_V = 4.5f;
constexpr float PT_FS_PSI = 100.0f;

// Hardware conversion rate. See the RATE-pin note above.
constexpr int LC_SPS = 10;
