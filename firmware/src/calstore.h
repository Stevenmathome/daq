#pragma once

#include "cal.h"

// EEPROM record of slope, offset, and points. A channel with its override
// flag set replaces the config.yaml line at boot. Tare is not in the record.
// Returns false when the record is missing or the CRC does not match;
// cals[] is left as the caller filled it from the config.
bool calStoreLoad(ChannelCal cals[CAL_CHANNELS]);

// Writes every channel that is dirty or already from EEPROM. Clears dirty
// and marks those channels from EEPROM.
void calStoreSave(ChannelCal cals[CAL_CHANNELS]);
