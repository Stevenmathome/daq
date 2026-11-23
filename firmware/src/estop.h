#pragma once

#include <stdint.h>

// E-stop latch. The mushroom already removes 12 V from the valves in
// hardware. This latch is the firmware half: hold every MOSFET gate off
// until a person asks, and ignore that request while the sense still says
// the mushroom is in.
//
// Truth table (latched, sense tripped, reset edge) -> next latch.
// Keep this identical to firmware/scripts/estop_logic.py.
//
//   0 0 0 -> 0
//   0 0 1 -> 0     reset when nothing is latched
//   0 1 0 -> 1     sense trips
//   0 1 1 -> 1     reset is ignored while the sense is still tripped
//   1 0 0 -> 1     released, waiting for an explicit reset
//   1 0 1 -> 0     reset after release
//   1 1 0 -> 1
//   1 1 1 -> 1     still tripped, reset ignored

inline bool estopNextLatch(bool latched, bool senseTripped, bool resetEdge) {
    if (senseTripped) {
        return true;
    }
    if (latched && resetEdge) {
        return false;
    }
    return latched;
}

enum EstopDisplay : uint8_t {
    ESTOP_SHOW_CHANNELS = 0,
    ESTOP_SHOW_STOP = 1,
    ESTOP_SHOW_RESET = 2,
};

// What the 7-segment displays should say. Sensors and the CSV stream do
// not use this; they keep running through both latched states.
inline EstopDisplay estopDisplay(bool latched, bool senseTripped) {
    if (!latched) {
        return ESTOP_SHOW_CHANNELS;
    }
    if (senseTripped) {
        return ESTOP_SHOW_STOP;
    }
    return ESTOP_SHOW_RESET;
}
