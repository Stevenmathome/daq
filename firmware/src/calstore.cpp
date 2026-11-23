#include "calstore.h"

#include <EEPROM.h>
#include <string.h>

static constexpr uint32_t CAL_MAGIC = 0x43414C31u; // 'CAL1'
static constexpr uint16_t CAL_VERSION = 1;

struct __attribute__((packed)) EePoint {
    float raw;
    float value;
};

struct __attribute__((packed)) EeChan {
    float slope;
    float offset;
    uint8_t nPoints;
    uint8_t overrideOn;
    EePoint points[CAL_MAX_POINTS];
};

struct __attribute__((packed)) EeRecord {
    uint32_t magic;
    uint16_t version;
    EeChan ch[CAL_CHANNELS];
    uint16_t crc;
};

static_assert(sizeof(EeRecord) < 2000, "calibration record fits in Teensy EEPROM");

static uint16_t crc16(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFFu;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; ++bit) {
            if (crc & 1u) {
                crc = static_cast<uint16_t>((crc >> 1) ^ 0xA001u);
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

static void copyIn(ChannelCal& dest, const EeChan& src) {
    dest.slope = src.slope;
    dest.offset = src.offset;
    dest.nPoints = src.nPoints > CAL_MAX_POINTS ? CAL_MAX_POINTS : src.nPoints;
    for (uint8_t i = 0; i < dest.nPoints; ++i) {
        dest.points[i].raw = src.points[i].raw;
        dest.points[i].value = src.points[i].value;
    }
    dest.fromEeprom = true;
    dest.dirty = false;
    dest.tare = 0.0f;
    dest.hasZero = false;
}

bool calStoreLoad(ChannelCal cals[CAL_CHANNELS]) {
    EeRecord rec;
    EEPROM.get(0, rec);
    const uint16_t expect = crc16(reinterpret_cast<uint8_t*>(&rec), sizeof(EeRecord) - sizeof(rec.crc));
    if (rec.magic != CAL_MAGIC || rec.version != CAL_VERSION || rec.crc != expect) {
        return false;
    }
    for (uint8_t i = 0; i < CAL_CHANNELS; ++i) {
        if (rec.ch[i].overrideOn) {
            copyIn(cals[i], rec.ch[i]);
        }
    }
    return true;
}

void calStoreSave(ChannelCal cals[CAL_CHANNELS]) {
    EeRecord rec;
    memset(&rec, 0, sizeof(rec));
    rec.magic = CAL_MAGIC;
    rec.version = CAL_VERSION;
    for (uint8_t i = 0; i < CAL_CHANNELS; ++i) {
        const bool keep = cals[i].dirty || cals[i].fromEeprom;
        rec.ch[i].slope = cals[i].slope;
        rec.ch[i].offset = cals[i].offset;
        rec.ch[i].overrideOn = keep ? 1 : 0;
        rec.ch[i].nPoints = keep ? cals[i].nPoints : 0;
        if (keep) {
            for (uint8_t p = 0; p < cals[i].nPoints && p < CAL_MAX_POINTS; ++p) {
                rec.ch[i].points[p].raw = cals[i].points[p].raw;
                rec.ch[i].points[p].value = cals[i].points[p].value;
            }
        }
    }
    rec.crc = crc16(reinterpret_cast<uint8_t*>(&rec), sizeof(EeRecord) - sizeof(rec.crc));
    EEPROM.put(0, rec);
    for (uint8_t i = 0; i < CAL_CHANNELS; ++i) {
        if (cals[i].dirty || cals[i].fromEeprom) {
            cals[i].dirty = false;
            cals[i].fromEeprom = rec.ch[i].overrideOn != 0;
        }
    }
}
