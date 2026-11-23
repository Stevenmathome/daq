#include "max31856.h"

#include <Arduino.h>
#include <SPI.h>

#include "pins.h"

static const SPISettings kSpi(1000000, MSBFIRST, SPI_MODE1);

static void csHighAll() {
    for (uint8_t cs : PIN_TC_CS) {
        digitalWrite(cs, HIGH);
    }
}

static uint8_t xfer(uint8_t cs, uint8_t reg, const uint8_t* tx, uint8_t* rx, uint8_t n, bool write) {
    SPI.beginTransaction(kSpi);
    digitalWrite(cs, LOW);
    SPI.transfer(write ? (reg | 0x80) : (reg & 0x7F));
    for (uint8_t i = 0; i < n; ++i) {
        uint8_t in = SPI.transfer(tx ? tx[i] : 0);
        if (rx) {
            rx[i] = in;
        }
    }
    digitalWrite(cs, HIGH);
    SPI.endTransaction();
    return n;
}

static void writeReg(uint8_t cs, uint8_t reg, uint8_t value) {
    xfer(cs, reg, &value, nullptr, 1, true);
}

static uint8_t readReg(uint8_t cs, uint8_t reg) {
    uint8_t value = 0;
    xfer(cs, reg, nullptr, &value, 1, false);
    return value;
}

void tcBegin() {
    for (uint8_t cs : PIN_TC_CS) {
        pinMode(cs, OUTPUT);
        digitalWrite(cs, HIGH);
    }
    SPI.begin();
    csHighAll();
}

void tcConfigure(uint8_t index, uint8_t typeCode) {
    if (index > 2) {
        return;
    }
    const uint8_t cs = PIN_TC_CS[index];
    // Fault clear is self-clearing. OCFAULT0 enables open-circuit detection.
    writeReg(cs, 0x00, 0x82);
    // Auto-conversion, 60 Hz filter, open-circuit fault enabled.
    writeReg(cs, 0x00, 0x90);
    writeReg(cs, 0x01, typeCode & 0x0F);
}

bool tcRead(uint8_t index, float* celsius, uint8_t* fault) {
    if (index > 2) {
        return false;
    }
    const uint8_t cs = PIN_TC_CS[index];
    const uint8_t sr = readReg(cs, 0x0F);
    if (fault) {
        *fault = sr;
    }
    uint8_t buf[3] = {0, 0, 0};
    xfer(cs, 0x0C, nullptr, buf, 3, false);

    if (sr == 0xFF && buf[0] == 0xFF && buf[1] == 0xFF && buf[2] == 0xFF) {
        *celsius = NAN;
        return false;
    }
    // 19-bit signed temperature, left-aligned in 24 bits, 1/128 °C per LSB
    // after the unused low 5 bits are shifted off.
    uint32_t word = (uint32_t)buf[0] << 16 | (uint32_t)buf[1] << 8 | buf[2];
    int32_t temp = static_cast<int32_t>(word);
    if (temp & 0x800000) {
        temp |= 0xFF000000;
    }
    temp >>= 5;
    *celsius = static_cast<float>(temp) * 0.0078125f;
    return sr == 0;
}
