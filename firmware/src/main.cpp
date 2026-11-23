#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "config_gen.h"
#include "estop.h"
#include "hx711_bus.h"
#include "max31856.h"
#include "pins.h"
#include "scale.h"
#include "tm1637.h"

// DAQ Rev B panel firmware.
//
// The operator is the sheet-metal panel, not a laptop. Buttons and switches
// on the input headers select valves, tare, and display pages. Three
// TM1637 displays show the page, or the E-stop state when that overrides.
// USB serial is a CSV log plus a few commands. It is not required for the
// panel to run.
//
// Safety:
//   Valve gates are driven low before anything else, and again on every
//   boot. The hardware E-stop removes 12 V from the valve coils only, so
//   the Teensy, the sensors, and this log stay up. The sense GPIO (chosen
//   in config.yaml) latches those gates off. A configured reset input
//   clears the latch only after the sense line has released. Opening the
//   USB port reboots a Teensy, which also drops the valves.

static constexpr char FW_VERSION[] = "1.0.0";

static int32_t gLcRaw[3];
static float gTare[3];
static bool gLcFresh[3];
static uint16_t gPtCounts[6];
static float gTcC[3];
static bool gTcOk[3];
static bool gValve[7];
static uint8_t gDriven;
static bool gLatch;
static bool gSenseRaw;
static bool gSenseTripped;
static uint32_t gSenseMs;
static uint8_t gPage;
static uint16_t gStreamHz;
static uint32_t gLastRowMs;

struct InputState {
    bool raw;
    bool stable;
    bool active;
    uint32_t changeMs;
};

static InputState gIn[8];

static char gLine[96];
static uint8_t gLineLen;

static void forceValvePinsOff() {
    for (uint8_t pin : PIN_VALVE) {
        digitalWrite(pin, LOW);
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
    }
}

// Runs before setup(), so a slow init cannot leave a gate floating high.
struct ValveBoot {
    ValveBoot() { forceValvePinsOff(); }
};
static ValveBoot gValveBoot;

static bool same(const char* a, const char* b) {
    return strcasecmp(a, b) == 0;
}

static bool parseLong(const char* text, long* out) {
    char* end = nullptr;
    long value = strtol(text, &end, 10);
    if (end == text || *end != '\0') {
        return false;
    }
    *out = value;
    return true;
}

static int tokenize(char* line, char** tok, int maxTok) {
    int count = 0;
    while (*line && count < maxTok) {
        while (*line == ' ') {
            ++line;
        }
        if (*line == '\0') {
            break;
        }
        tok[count++] = line;
        while (*line && *line != ' ') {
            ++line;
        }
        if (*line) {
            *line = '\0';
            ++line;
        }
    }
    return count;
}

static bool rawTripped() {
    const bool high = digitalRead(CFG_ESTOP_PIN) == HIGH;
    return CFG_ESTOP_ACTIVE_HIGH ? high : !high;
}

static void configureSensePin() {
    uint8_t mode = INPUT;
    if (CFG_ESTOP_PULL == CFG_PULL_DOWN) {
        mode = INPUT_PULLDOWN;
    } else if (CFG_ESTOP_PULL == CFG_PULL_UP) {
        mode = INPUT_PULLUP;
    }
    pinMode(CFG_ESTOP_PIN, mode);
}

static bool valveAllowed(uint8_t valve) {
    for (uint8_t i = 0; i < CFG_N_LOCKS; ++i) {
        if (CFG_LOCKS[i].valve != valve) {
            continue;
        }
        if (!gIn[CFG_LOCKS[i].armInput].active) {
            return false;
        }
    }
    return true;
}

static void driveValves() {
    // The hardware E-stop may already have removed coil power. Holding the
    // gates low means the coils stay off when that 12 V comes back.
    gDriven = 0;
    for (uint8_t valve = 0; valve < 7; ++valve) {
        const bool permit = !gLatch && valveAllowed(static_cast<uint8_t>(valve + 1));
        if (!permit) {
            gValve[valve] = false;
        }
        const bool on = gValve[valve] && permit;
        digitalWrite(PIN_VALVE[valve], on ? HIGH : LOW);
        if (on) {
            gDriven = static_cast<uint8_t>(gDriven | (1u << valve));
        }
    }
}

static uint8_t inputBits() {
    uint8_t bits = 0;
    for (uint8_t i = 0; i < 8; ++i) {
        if (gIn[i].stable) {
            bits = static_cast<uint8_t>(bits | (1u << i));
        }
    }
    return bits;
}

static uint8_t armColumn() {
    bool any = false;
    bool all = true;
    for (uint8_t i = 0; i < 8; ++i) {
        if (CFG_INPUTS[i].action != CFG_ARM) {
            continue;
        }
        any = true;
        if (!gIn[i].active) {
            all = false;
        }
    }
    if (!any) {
        return 0;
    }
    return all ? 1 : 0;
}

static float channelValue(uint8_t channel) {
    if (channel < 3) {
        if (!gLcFresh[channel]) {
            return NAN;
        }
        return loadEu(gLcRaw[channel], gTare[channel], CFG_LC[channel].countsPerUnit);
    }
    if (channel < 9) {
        const uint8_t index = static_cast<uint8_t>(channel - 3);
        return pressurePsi(
            gPtCounts[index],
            CFG_PT[index].zeroVolts,
            CFG_PT[index].fullScaleVolts,
            CFG_PT[index].fullScalePsi);
    }
    const uint8_t index = static_cast<uint8_t>(channel - 9);
    if (!gTcOk[index]) {
        return NAN;
    }
    return gTcC[index];
}

static void printDirectory() {
    Serial.print("# csv: ");
    Serial.println(CFG_CSV_HEADER);
    Serial.println("# inputs and valves are bit masks, bit 0 = DI1 / valve 1.");
    Serial.println("# arm is 1 when every arm switch is active.");
    Serial.println("# estop_sense is 1 when the sense line is tripped.");
    Serial.println("# estop_latch is 1 until reset, after the sense has released.");
    Serial.println("# page is the display page index, starting at 0.");
    for (uint8_t i = 0; i < 3; ++i) {
        Serial.print("# ");
        Serial.print(CFG_LC[i].id);
        Serial.print(" ");
        Serial.print(CFG_LC[i].name);
        Serial.print(" ");
        Serial.println(CFG_LC[i].unit);
    }
    for (uint8_t i = 0; i < 6; ++i) {
        Serial.print("# ");
        Serial.print(CFG_PT[i].id);
        Serial.print(" ");
        Serial.print(CFG_PT[i].name);
        Serial.println(" psi");
    }
    for (uint8_t i = 0; i < 3; ++i) {
        Serial.print("# ");
        Serial.print(CFG_TC[i].id);
        Serial.print(" ");
        Serial.print(CFG_TC[i].name);
        Serial.print(" type ");
        Serial.println(CFG_TC[i].typeLetter);
    }
    for (uint8_t i = 0; i < CFG_N_PAGES; ++i) {
        Serial.print("# page ");
        Serial.print(i);
        Serial.print(" ");
        Serial.println(CFG_PAGES[i].name);
    }
}

static void printBanner() {
    Serial.print("# DAQ Rev B firmware ");
    Serial.println(FW_VERSION);
    Serial.println("# Opening USB serial reboots the board and forces the valves off.");
    Serial.print("# estop pin ");
    Serial.print(CFG_ESTOP_PIN);
    Serial.print(CFG_ESTOP_ACTIVE_HIGH ? " active high, pull " : " active low, pull ");
    if (CFG_ESTOP_PULL == CFG_PULL_DOWN) {
        Serial.print("down");
    } else if (CFG_ESTOP_PULL == CFG_PULL_UP) {
        Serial.print("up");
    } else {
        Serial.print("none");
    }
    Serial.print(", reset ");
    Serial.println(CFG_INPUTS[CFG_ESTOP_RESET_INPUT].name);
    printDirectory();
}

static void announcePage() {
    Serial.print("# PAGE ");
    Serial.print(gPage);
    Serial.print(' ');
    Serial.println(CFG_PAGES[gPage].name);
}

static void doTare(uint8_t mask) {
    bool any = false;
    for (uint8_t i = 0; i < 3; ++i) {
        if ((mask & (1u << i)) == 0) {
            continue;
        }
        if (!gLcFresh[i]) {
            continue;
        }
        gTare[i] = static_cast<float>(gLcRaw[i]);
        any = true;
    }
    Serial.println(any ? "# OK tare" : "# ERR no load-cell sample");
}

static void advancePage() {
    gPage = static_cast<uint8_t>((gPage + 1) % CFG_N_PAGES);
    announcePage();
}

static void onPress(uint8_t index, bool* resetEdge) {
    const CfgInput& input = CFG_INPUTS[index];
    switch (input.action) {
    case CFG_RESET:
        *resetEdge = true;
        break;
    case CFG_TOGGLE: {
        if (gLatch) {
            Serial.println("# ERR estop latched");
            break;
        }
        if (!valveAllowed(input.valve)) {
            Serial.print("# ERR interlock valve ");
            Serial.println(input.valve);
            break;
        }
        gValve[input.valve - 1] = !gValve[input.valve - 1];
        break;
    }
    case CFG_TARE:
        doTare(input.tareMask);
        break;
    case CFG_PAGE:
        advancePage();
        break;
    default:
        break;
    }
}

static void serviceInputs(bool* resetEdge) {
    const uint32_t now = millis();
    *resetEdge = false;
    for (uint8_t i = 0; i < 8; ++i) {
        const bool high = digitalRead(PIN_DI[i]) == HIGH;
        if (high != gIn[i].raw) {
            gIn[i].raw = high;
            gIn[i].changeMs = now;
            continue;
        }
        if ((now - gIn[i].changeMs) < CFG_DEBOUNCE_MS || high == gIn[i].stable) {
            continue;
        }
        gIn[i].stable = high;
        const bool active = CFG_INPUTS[i].activeHigh ? high : !high;
        const bool was = gIn[i].active;
        gIn[i].active = active;
        if (active && !was) {
            onPress(i, resetEdge);
        }
    }
}

static void serviceMomentary() {
    bool held[7] = {};
    bool momentary[7] = {};
    for (uint8_t i = 0; i < 8; ++i) {
        if (CFG_INPUTS[i].action != CFG_MOMENTARY) {
            continue;
        }
        const uint8_t valve = static_cast<uint8_t>(CFG_INPUTS[i].valve - 1);
        momentary[valve] = true;
        if (gIn[i].active) {
            held[valve] = true;
        }
    }
    for (uint8_t valve = 0; valve < 7; ++valve) {
        if (momentary[valve]) {
            gValve[valve] = held[valve];
        }
    }
}

static void serviceSenseDebounce() {
    const bool raw = rawTripped();
    const uint32_t now = millis();
    if (raw != gSenseRaw) {
        gSenseRaw = raw;
        gSenseMs = now;
        return;
    }
    if ((now - gSenseMs) >= CFG_DEBOUNCE_MS) {
        gSenseTripped = raw;
    }
}

static void applyLatch(bool resetEdge, bool fromSerial) {
    const bool before = gLatch;
    gLatch = estopNextLatch(gLatch, gSenseTripped, resetEdge);
    if (gLatch && !before) {
        Serial.println("# ESTOP");
    } else if (!gLatch && before) {
        Serial.println("# RESET");
    } else if (fromSerial && resetEdge && gLatch && gSenseTripped) {
        Serial.println("# ERR estop active");
    } else if (fromSerial && resetEdge && !before) {
        Serial.println("# ERR not latched");
    }
    if (gLatch) {
        for (bool& valve : gValve) {
            valve = false;
        }
    }
}

static void seedInputs() {
    const uint32_t now = millis();
    for (uint8_t i = 0; i < 8; ++i) {
        const bool high = digitalRead(PIN_DI[i]) == HIGH;
        gIn[i].raw = high;
        gIn[i].stable = high;
        gIn[i].active = CFG_INPUTS[i].activeHigh ? high : !high;
        gIn[i].changeMs = now;
    }
}

static void seedSense() {
    gSenseRaw = rawTripped();
    gSenseTripped = gSenseRaw;
    gSenseMs = millis();
    gLatch = gSenseTripped;
}

static void commandValve(const char* valveText, const char* stateText) {
    long valve = 0;
    long state = 0;
    if (!parseLong(valveText, &valve) || !parseLong(stateText, &state) || valve < 1 || valve > 7 ||
        (state != 0 && state != 1)) {
        Serial.println("# ERR valve");
        return;
    }
    if (gLatch && state == 1) {
        Serial.println("# ERR estop latched");
        return;
    }
    if (state == 1 && !valveAllowed(static_cast<uint8_t>(valve))) {
        Serial.print("# ERR interlock valve ");
        Serial.println(valve);
        return;
    }
    gValve[valve - 1] = state == 1;
    Serial.println("# OK valve");
}

static void commandTare(const char* which) {
    if (same(which, "ALL")) {
        doTare(0x7);
        return;
    }
    if (same(which, "LC1")) {
        doTare(0x1);
        return;
    }
    if (same(which, "LC2")) {
        doTare(0x2);
        return;
    }
    if (same(which, "LC3")) {
        doTare(0x4);
        return;
    }
    Serial.println("# ERR tare");
}

static void handleLine(char* line, bool* serialReset) {
    char* tok[6];
    const int count = tokenize(line, tok, 6);
    if (count == 0) {
        return;
    }
    if (same(tok[0], "PING")) {
        Serial.print("# PONG ");
        Serial.println(millis());
        return;
    }
    if (same(tok[0], "HELP")) {
        Serial.println("# PING");
        Serial.println("# INFO");
        Serial.println("# STREAM <0-50>");
        Serial.println("# VALVE <1-7> <0|1>");
        Serial.println("# ALLOFF");
        Serial.println("# TARE <LC1|LC2|LC3|ALL>");
        Serial.println("# PAGE");
        Serial.println("# RESET");
        return;
    }
    if (same(tok[0], "INFO")) {
        printBanner();
        Serial.print("# sense ");
        Serial.print(gSenseTripped ? 1 : 0);
        Serial.print(" latch ");
        Serial.print(gLatch ? 1 : 0);
        Serial.print(" stream ");
        Serial.println(gStreamHz);
        return;
    }
    if (same(tok[0], "STREAM") && count == 2) {
        long hz = 0;
        if (!parseLong(tok[1], &hz) || hz < 0 || hz > 50) {
            Serial.println("# ERR stream");
            return;
        }
        gStreamHz = static_cast<uint16_t>(hz);
        Serial.println("# OK stream");
        return;
    }
    if (same(tok[0], "VALVE") && count == 3) {
        commandValve(tok[1], tok[2]);
        return;
    }
    if (same(tok[0], "ALLOFF")) {
        for (bool& valve : gValve) {
            valve = false;
        }
        Serial.println("# OK alloff");
        return;
    }
    if (same(tok[0], "TARE") && count == 2) {
        commandTare(tok[1]);
        return;
    }
    if (same(tok[0], "PAGE")) {
        advancePage();
        return;
    }
    if (same(tok[0], "RESET")) {
        *serialReset = true;
        return;
    }
    Serial.println("# ERR command");
}

static void serviceSerial(bool* serialReset) {
    *serialReset = false;
    while (Serial.available() > 0) {
        const char letter = static_cast<char>(Serial.read());
        if (letter == '\r') {
            continue;
        }
        if (letter != '\n') {
            if (gLineLen < sizeof(gLine) - 1) {
                gLine[gLineLen++] = letter;
            } else {
                gLineLen = 0;
            }
            continue;
        }
        gLine[gLineLen] = '\0';
        gLineLen = 0;
        handleLine(gLine, serialReset);
    }
}

static void serviceLoadCells() {
    static uint32_t notReadySince = 0;
    bool allReady = true;
    for (uint8_t i = 0; i < 3; ++i) {
        if (digitalRead(PIN_LC_DOUT[i]) != LOW) {
            allReady = false;
        }
    }
    if (!allReady) {
        if (notReadySince == 0) {
            notReadySince = millis();
        }
        if ((millis() - notReadySince) < 200) {
            return;
        }
    }
    int32_t raw[3];
    bool ready[3];
    hx711Read(raw, ready);
    for (uint8_t i = 0; i < 3; ++i) {
        if (ready[i]) {
            gLcRaw[i] = raw[i];
            gLcFresh[i] = true;
        }
    }
    notReadySince = 0;
}

static void servicePressure() {
    static uint32_t last = 0;
    if ((millis() - last) < 20) {
        return;
    }
    last = millis();
    for (uint8_t i = 0; i < 6; ++i) {
        gPtCounts[i] = static_cast<uint16_t>(analogRead(PIN_PT[i]));
    }
}

static void serviceThermocouples() {
    static uint32_t last = 0;
    static uint8_t index = 0;
    if ((millis() - last) < 50) {
        return;
    }
    last = millis();
    float celsius = 0.0f;
    uint8_t fault = 0;
    const bool ok = tcRead(index, &celsius, &fault);
    gTcC[index] = celsius;
    gTcOk[index] = ok && fault == 0;
    index = static_cast<uint8_t>((index + 1) % 3);
}

static void serviceDisplays() {
    static uint32_t last = 0;
    if ((millis() - last) < 100) {
        return;
    }
    last = millis();
    const EstopDisplay mode = estopDisplay(gLatch, gSenseTripped);
    if (mode != ESTOP_SHOW_CHANNELS) {
        const bool lit = ((millis() / 400) % 2) == 0;
        const char* text = mode == ESTOP_SHOW_STOP ? "STOP" : "RST ";
        for (uint8_t i = 0; i < 3; ++i) {
            if (lit) {
                dispShowText(i, text);
            } else {
                dispClear(i);
            }
        }
        return;
    }
    const CfgPage& page = CFG_PAGES[gPage];
    for (uint8_t i = 0; i < 3; ++i) {
        dispShow(i, channelValue(page.show[i]));
    }
}

static void printFloat(float value, int decimals, bool ok) {
    if (!ok) {
        Serial.print("nan");
        return;
    }
    Serial.print(value, decimals);
}

// csv columns: t_us,LC1,LC2,LC3,LC1_raw,LC2_raw,LC3_raw,PT1,PT2,PT3,PT4,PT5,PT6,PT1_counts,PT2_counts,PT3_counts,PT4_counts,PT5_counts,PT6_counts,TC1,TC2,TC3,tc_fault,valves,inputs,arm,estop_sense,estop_latch,page
static void printRow() {
    Serial.print(micros());
    for (uint8_t i = 0; i < 3; ++i) {
        Serial.print(',');
        printFloat(loadEu(gLcRaw[i], gTare[i], CFG_LC[i].countsPerUnit), 3, gLcFresh[i]);
    }
    for (uint8_t i = 0; i < 3; ++i) {
        Serial.print(',');
        if (gLcFresh[i]) {
            Serial.print(gLcRaw[i]);
        } else {
            Serial.print("nan");
        }
    }
    for (uint8_t i = 0; i < 6; ++i) {
        Serial.print(',');
        printFloat(
            pressurePsi(gPtCounts[i], CFG_PT[i].zeroVolts, CFG_PT[i].fullScaleVolts, CFG_PT[i].fullScalePsi),
            2,
            true);
    }
    for (uint8_t i = 0; i < 6; ++i) {
        Serial.print(',');
        Serial.print(gPtCounts[i]);
    }
    uint8_t fault = 0;
    for (uint8_t i = 0; i < 3; ++i) {
        Serial.print(',');
        printFloat(gTcC[i], 2, gTcOk[i]);
        if (!gTcOk[i]) {
            fault = static_cast<uint8_t>(fault | (1u << i));
        }
    }
    Serial.print(',');
    Serial.print(fault);
    Serial.print(',');
    Serial.print(gDriven);
    Serial.print(',');
    Serial.print(inputBits());
    Serial.print(',');
    Serial.print(armColumn());
    Serial.print(',');
    Serial.print(gSenseTripped ? 1 : 0);
    Serial.print(',');
    Serial.print(gLatch ? 1 : 0);
    Serial.print(',');
    Serial.println(gPage);
}

static void serviceStream() {
    if (gStreamHz == 0) {
        return;
    }
    const uint32_t interval = 1000UL / gStreamHz;
    if ((millis() - gLastRowMs) < interval) {
        return;
    }
    gLastRowMs = millis();
    printRow();
}

void setup() {
    forceValvePinsOff();
    Serial.begin(115200);

    pinMode(PIN_LC_SCK, OUTPUT);
    digitalWrite(PIN_LC_SCK, LOW);
    for (uint8_t pin : PIN_LC_DOUT) {
        pinMode(pin, INPUT_PULLUP);
    }
    for (uint8_t pin : PIN_DI) {
        pinMode(pin, INPUT);
    }
    configureSensePin();

    analogReadResolution(12);
    analogReadAveraging(4);

    tcBegin();
    for (uint8_t i = 0; i < 3; ++i) {
        gTare[i] = CFG_LC[i].tare;
        tcConfigure(i, CFG_TC[i].typeCode);
        gPtCounts[i] = static_cast<uint16_t>(analogRead(PIN_PT[i]));
    }
    for (uint8_t i = 3; i < 6; ++i) {
        gPtCounts[i] = static_cast<uint16_t>(analogRead(PIN_PT[i]));
    }
    dispBegin();
    (void)gValveBoot;

    seedInputs();
    seedSense();
    gStreamHz = CFG_STREAM_HZ;
    gPage = 0;

    printBanner();
    if (gLatch) {
        Serial.println("# ESTOP");
    }
    announcePage();
    driveValves();
}

void loop() {
    bool buttonReset = false;
    bool serialReset = false;
    serviceInputs(&buttonReset);
    serviceMomentary();
    serviceSenseDebounce();
    serviceSerial(&serialReset);
    applyLatch(buttonReset || serialReset, serialReset);
    driveValves();
    serviceLoadCells();
    servicePressure();
    serviceThermocouples();
    serviceDisplays();
    serviceStream();
}
