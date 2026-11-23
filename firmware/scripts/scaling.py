"""Pressure and load-cell scaling for DAQ Rev B.

The Teensy firmware copies these formulas in src/scale.h. Change both
together. The divider and the ADC constants are the Rev B front end:

  12-bit ADC, full-scale code 4095, 3.3 V reference
  10k series / 20k to ground, so Vsensor = Vpin * 1.5
  A 0.5-4.5 V ratiometric sensor therefore spans 0.333-3.0 V at the pin.

Worked pressure point, used by the tests:
  counts 2730 -> pin volts 2.2 -> sensor volts 3.3 -> 70 PSI
  on a 0.5 V / 4.5 V / 100 PSI channel.
"""

from __future__ import annotations

ADC_VREF = 3.3
ADC_MAX_COUNT = 4095
DIVIDER = 1.5  # (10k + 20k) / 20k


def pin_volts(counts: int) -> float:
    return (counts / ADC_MAX_COUNT) * ADC_VREF


def sensor_volts(counts: int) -> float:
    return pin_volts(counts) * DIVIDER


def pressure_psi(counts: int, zero_volts: float, full_scale_volts: float, full_scale_psi: float) -> float:
    span = full_scale_volts - zero_volts
    if span == 0:
        raise ZeroDivisionError("pressure span is zero")
    return (sensor_volts(counts) - zero_volts) / span * full_scale_psi


def load_eu(raw: int, tare: float, counts_per_unit: float) -> float:
    if counts_per_unit == 0:
        raise ZeroDivisionError("counts_per_unit is zero")
    return (raw - tare) / counts_per_unit
