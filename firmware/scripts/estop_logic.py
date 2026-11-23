"""E-stop latch rules.

The mushroom cuts 12 V to the valves in hardware. The Teensy keeps
sampling and logging. Firmware latches the MOSFET gates off when the
sense line trips, and a reset is accepted only after that line has
released. src/estop.h is the same rule on the microcontroller.
"""

from __future__ import annotations


def next_latch(latched: bool, sense_tripped: bool, reset_edge: bool) -> bool:
    if sense_tripped:
        return True
    if latched and reset_edge:
        return False
    return latched


def display_mode(latched: bool, sense_tripped: bool) -> str:
    """What the 7-segment displays show. The CSV stream is unaffected."""
    if not latched:
        return "channels"
    if sense_tripped:
        return "stop"
    return "reset"
