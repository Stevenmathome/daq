#include "tm1637.h"

#include <Arduino.h>
#include <math.h>
#include <stdio.h>

#include "pins.h"

static const uint8_t kDigits[10] = {
    0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f};

static void dioLow(uint8_t pin) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
}

static void dioRelease(uint8_t pin) {
    // Released line idles through the module pullup, or the Teensy pullup
    // if the module has none. See the wiring note in the README: a display
    // whose pullups go to +5V will present 5 V to this pin.
    pinMode(pin, INPUT_PULLUP);
}

static void clkLow(uint8_t pin) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
}

static void clkRelease(uint8_t pin) {
    pinMode(pin, INPUT_PULLUP);
}

static void start(uint8_t clk, uint8_t dio) {
    dioRelease(dio);
    clkRelease(clk);
    delayMicroseconds(3);
    dioLow(dio);
    delayMicroseconds(3);
    clkLow(clk);
}

static void stop(uint8_t clk, uint8_t dio) {
    dioLow(dio);
    delayMicroseconds(3);
    clkRelease(clk);
    delayMicroseconds(3);
    dioRelease(dio);
}

static void writeByte(uint8_t clk, uint8_t dio, uint8_t data) {
    for (int i = 0; i < 8; ++i) {
        clkLow(clk);
        if (data & 0x01) {
            dioRelease(dio);
        } else {
            dioLow(dio);
        }
        delayMicroseconds(3);
        clkRelease(clk);
        delayMicroseconds(3);
        data >>= 1;
    }
    clkLow(clk);
    dioRelease(dio);
    delayMicroseconds(3);
    clkRelease(clk);
    delayMicroseconds(3);
    clkLow(clk);
}

static void writeCmd(uint8_t index, uint8_t cmd) {
    const uint8_t clk = PIN_DISP_CLK[index];
    const uint8_t dio = PIN_DISP_DIO[index];
    start(clk, dio);
    writeByte(clk, dio, cmd);
    stop(clk, dio);
}

static void writeDigits(uint8_t index, const uint8_t segs[4]) {
    const uint8_t clk = PIN_DISP_CLK[index];
    const uint8_t dio = PIN_DISP_DIO[index];
    writeCmd(index, 0x40);
    start(clk, dio);
    writeByte(clk, dio, 0xC0);
    for (int i = 0; i < 4; ++i) {
        writeByte(clk, dio, segs[i]);
    }
    stop(clk, dio);
    writeCmd(index, 0x8C); // display on, brightness 4
}

void dispBegin() {
    for (int i = 0; i < 3; ++i) {
        dioRelease(PIN_DISP_DIO[i]);
        clkRelease(PIN_DISP_CLK[i]);
        dispClear(i);
    }
}

void dispClear(uint8_t index) {
    const uint8_t blank[4] = {0, 0, 0, 0};
    writeDigits(index, blank);
}

static uint8_t segFromChar(char c) {
    switch (c) {
    case 'O':
        return 0x3f;
    case 'P':
        return 0x73;
    case 'R':
        return 0x50;
    case 'S':
        return 0x6d;
    case 'T':
        return 0x78;
    case ' ':
        return 0x00;
    default:
        return 0x00;
    }
}

void dispShowText(uint8_t index, const char text[4]) {
    uint8_t segs[4];
    for (int i = 0; i < 4; ++i) {
        char c = text[i];
        if (c >= 'a' && c <= 'z') {
            c = static_cast<char>(c - 'a' + 'A');
        }
        segs[i] = segFromChar(c);
    }
    writeDigits(index, segs);
}

static uint8_t segFor(char c) {
    if (c >= '0' && c <= '9') {
        return kDigits[c - '0'];
    }
    if (c == '-') {
        return 0x40;
    }
    return 0x00;
}

void dispShow(uint8_t index, float value) {
    uint8_t segs[4] = {0x40, 0x40, 0x40, 0x40}; // "----"
    if (index > 2 || !isfinite(value)) {
        writeDigits(index, segs);
        return;
    }

    // Four character positions. Pick a decimal so the reading fits,
    // including a leading minus.
    int decimals = 0;
    float absv = fabsf(value);
    if (absv < 10.0f) {
        decimals = 2;
    } else if (absv < 100.0f) {
        decimals = 1;
    }
    if (value < 0 && absv >= 100.0f) {
        decimals = 0;
    }

    float scaled = value;
    for (int i = 0; i < decimals; ++i) {
        scaled *= 10.0f;
    }
    int shown = static_cast<int>(lroundf(scaled));
    const int limit = (shown < 0) ? 999 : 9999;
    if (shown > 9999 || shown < -999) {
        const uint8_t hi[4] = {0x00, 0x76, 0x30, 0x00}; // " HI "
        const uint8_t lo[4] = {0x00, 0x38, 0x3f, 0x00}; // " LO "
        writeDigits(index, shown > 0 ? hi : lo);
        return;
    }
    (void)limit;

    char text[8];
    if (decimals == 0) {
        snprintf(text, sizeof(text), "%4d", shown);
    } else {
        // Build digits ourselves so the decimal point lands on a segment.
        int mag = shown < 0 ? -shown : shown;
        int places = decimals + 1;
        int tmp = mag;
        int digits = 1;
        while (tmp >= 10) {
            tmp /= 10;
            ++digits;
        }
        if (digits < places) {
            digits = places;
        }
        if (shown < 0) {
            ++digits;
        }
        if (digits > 4) {
            decimals = 0;
            shown = static_cast<int>(lroundf(value));
            snprintf(text, sizeof(text), "%4d", shown);
            for (int i = 0; i < 4; ++i) {
                segs[i] = segFor(text[i]);
            }
            writeDigits(index, segs);
            return;
        }
        char raw[5] = {' ', ' ', ' ', ' ', 0};
        int pos = 3;
        int pointAt = 3 - decimals;
        int m = mag;
        for (int d = 0; d < places || m > 0; ++d) {
            if (pos < 0) {
                break;
            }
            raw[pos] = static_cast<char>('0' + (m % 10));
            m /= 10;
            --pos;
        }
        if (shown < 0 && pos >= 0) {
            raw[pos] = '-';
        }
        for (int i = 0; i < 4; ++i) {
            segs[i] = segFor(raw[i]);
        }
        if (pointAt >= 0 && pointAt < 4) {
            segs[pointAt] |= 0x80;
        }
        writeDigits(index, segs);
        return;
    }

    for (int i = 0; i < 4; ++i) {
        segs[i] = segFor(text[i]);
    }
    writeDigits(index, segs);
}
