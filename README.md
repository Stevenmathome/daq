# DAQ Rev B

Firmware for the Teensy 4.1 on the DAQ Rev B board. The operator interface is the panel: switches, a button, three 7-segment displays, and an E-stop on an L-shaped bracket, wired to the board's input and display headers. The other face of the bracket carries the connectors out to the stand. A laptop is optional. USB serial is a CSV log and a few commands, not a control GUI.

The pin numbers below were checked against the Rev B schematic (KiCad 9.0.2) and the Rev B change report. Two places differ from a naive reading of "pins 24–30 and 31–38", and the HX711 rate is strapped in hardware. Those are called out in the pin map.

## Safety

Valve gates are driven low before `setup()` does anything else, and again on every boot. HIGH turns a MOSFET on.

The hardware E-stop removes 12 V from the valve coils only. Logic and sensors stay powered, so sampling, the displays, and the CSV continue through a trip. The firmware's job on that trip is to latch every valve output off, show it, and keep the gates off after coil power returns.

The sense pin is not fixed on the schematic. `estop.pin` in `firmware/config.yaml` chooses it. On the sense line going active the latch sets. The displays blink `STOP` while the line is still tripped, and blink `RST` after it releases, until the configured reset input. Reset is ignored while the sense is still tripped, including a reset that was already held. Press it again after release. Sensors are not stopped.

Arm is a permissive. A valve listed under `interlocks` stays off unless that arm input is active. Dropping arm clears a toggle, so re-arming does not turn the valve back on. A momentary output comes back only if the button is still held. The E-stop latch overrides arm.

Opening the USB serial port reboots a Teensy. The reboot drops the valves. Connect the logger before a run, not during one.

## Edit the configuration

`firmware/config.yaml` is the file the build uses, and it is the worked example. Change it in place, or keep a copy beside it and point the build at it by replacing that file.

A PlatformIO pre-build step runs `firmware/scripts/gen_config.py`, checks the file, and writes `firmware/include/config_gen.h`. The Teensy never parses YAML. Do not edit the header.

Check it without compiling:

```bash
cd firmware
python3 -m pip install -r requirements.txt
python3 scripts/gen_config.py config.yaml include/config_gen.h
```

Errors name the key. The build stops on the first failed check and prints every problem it found, not just the first.

What you set:

| Block | What it does |
|---|---|
| `load_cells` | Name, boot tare, and counts per engineering unit for LC1–LC3. `eu = (raw - tare) / counts_per_unit`. A negative factor flips a cell whose green and white wires are swapped. |
| `pressures` | Name and the sensor's 0 PSI volts, full-scale volts, and full-scale PSI. Volts are at the sensor, before the 10k/20k divider. |
| `thermocouples` | Name and MAX31856 type. Quote the letter: `type: "T"`. |
| `pages` | Each page is the three channels the displays show, display 1 then 2 then 3. The page input cycles the list. |
| `inputs` | DI1–DI8, each exactly once. `action` is `arm`, `reset`, `toggle_valve`, `momentary_valve`, `tare`, `display_page`, or `none`. |
| `estop` | Sense GPIO, `active`, `pull`, and which input is the reset button. |
| `interlocks` | `valve` N requires an input whose action is `arm`. |

A toggle already ON when the board boots does not energize. Cycle it. That is deliberate: boot forces the valves off, and a toggle is an edge, not a level.

The tare button replaces the boot tare until power cycle. It does not rewrite `config.yaml`. To keep a tare, read `LC1_raw` from the CSV with the cell unloaded and put that number in `tare`.

`counts_per_unit` is `(raw - tare) / known_load` from a reading taken with a known load applied. Pressure full scale is the sensor's rating (`100` for a 0–100 PSI, 0.5–4.5 V part). The worked example in the tests: ADC code 2730 on a default pressure channel is 2.2 V at the pin, 3.3 V at the sensor, 70 PSI.

### E-stop sense

```yaml
estop:
  pin: 10          # change this to the GPIO you wire
  active: low
  pull: down
  reset: DI7
```

Free GPIOs on this board: **10, 14, 39, 40, 41**. Any other pin belongs to a load cell, a display, SPI, a thermocouple chip select, a pressure input, or a valve, and the check rejects it.

A digital-input header can be the sense line only if that input's `action` is `none`. Those headers already have a 10k pulldown, so `pull` must be `none` or the firmware would fight the resistor.

The example uses pin 10, internal pulldown, active low. Wire a normally-closed contact from the pin to +3.3 V. Pressed, or the wire falls off, the pin goes low and the latch sets. An unwired pin 10 therefore reads tripped and the valves stay latched. That is the safe state on the bench. Tie the pin to +3.3 V if you need the valves before the switch exists, and do not leave it that way on the stand.

`reset` must name the one input whose action is `reset`. The example uses DI7, active high: a normally-open button to +3.3 V on that header.

## Build and upload

PlatformIO, board `teensy41`, Arduino framework. On a Mac:

```bash
python3 -m pip install -r firmware/requirements.txt
# PlatformIO CLI: https://platformio.org/install/cli
cd firmware
pytest tests
pio run -e teensy41
pio run -e teensy41 -t upload
```

The Teensy VIN–VUSB pad has to be cut (PJRC documents the pads on the back of the board). After the cut, USB does not power the Teensy. J16 needs 12 V for the board to run, including during upload. Do not put the E-stop in series with J16. That would kill the logger along with the valves.

`pytest` covers the config checks, the pressure and load-cell math, the E-stop latch rules, and that the CSV column list in the firmware matches the generator.

## Serial log

The port is the Teensy USB serial device. Tools ask for 115200 baud; USB CDC ignores it. On macOS the device is `/dev/cu.usbmodem…`.

```bash
pio device monitor -b 115200
```

Connecting resets the board. The first lines are comments (`#`). Data rows follow at `stream_hz` (10 Hz in the example). Load cells only convert at 10 Hz, because the HX711 RATE pin is tied to ground; a faster stream repeats the latest sample.

```
t_us,LC1,LC2,LC3,LC1_raw,LC2_raw,LC3_raw,PT1,PT2,PT3,PT4,PT5,PT6,PT1_counts,PT2_counts,PT3_counts,PT4_counts,PT5_counts,PT6_counts,TC1,TC2,TC3,tc_fault,valves,inputs,arm,estop_sense,estop_latch,page
```

| Column | Meaning |
|---|---|
| `t_us` | `micros()` since boot. It wraps. |
| `LC*` | Engineering units from the config. `nan` until that cell has produced a sample. |
| `LC*_raw` | Signed HX711 counts. |
| `PT*` | PSI from the config. |
| `PT*_counts` | 12-bit ADC code, 0–4095, 3.3 V full scale. |
| `TC*` | Degrees C. `nan` on a fault or before the first read. |
| `tc_fault` | Bit 0 TC1, bit 1 TC2, bit 2 TC3. |
| `valves` | Outputs actually driven. Bit 0 is valve 1. Zero while the E-stop latch is set. |
| `inputs` | Raw pin level, not the active-high/low setting. Bit 0 is DI1. 1 means the pin is HIGH. |
| `arm` | 1 when every input with action `arm` is in its active state. |
| `estop_sense` | 1 when the sense line is tripped. |
| `estop_latch` | 1 from the trip until a valid reset. |
| `page` | Display page index, starting at 0. |

`# ESTOP` is printed when the latch sets. `# RESET` is printed when it clears. Those lines are not CSV. `grep -v '^#'` keeps the rows.

Commands, one per line:

| Command | Effect |
|---|---|
| `PING` | `# PONG <ms>` |
| `INFO` | Banner, sense, latch, stream rate. |
| `HELP` | The command list. |
| `STREAM <0-50>` | Row rate. 0 pauses rows. Does not touch the valves. |
| `VALVE <1-7> <0\|1>` | Same rules as a panel toggle: rejected while latched or disarmed. |
| `ALLOFF` | Clears every valve request. |
| `TARE <LC1\|LC2\|LC3\|ALL>` | Captures the current raw count as tare. |
| `PAGE` | Next display page. |
| `RESET` | Clears the latch only if the sense line is released. |

A rejected valve answers `# ERR estop latched` or `# ERR interlock valve N`.

## Pin map

Arduino pin numbers on the Teensy 4.1.

| Function | Connector | Teensy pin | Notes |
|---|---|---|---|
| LC1 DOUT | U3, J17 | 3 | HX711 data |
| LC2 DOUT | U4, J18 | 0 | |
| LC3 DOUT | U5, J19 | 1 | |
| LC shared SCK | U3–U5 | 2 | One clock for all three. Read them together. |
| Display 1 CLK / DIO | J29 | 4 / 5 | Header: 1 +5 V, 2 GND, 3 CLK, 4 DIO |
| Display 2 CLK / DIO | J30 | 6 / 7 | |
| Display 3 CLK / DIO | J31 | 8 / 9 | |
| TC MOSI / MISO / SCK | — | 11 / 12 / 13 | MAX31856. Pin 13 is also the onboard LED. |
| TC1 CS | U6, J20 | 23 | DRDY and FAULT are not wired. The firmware polls SPI. |
| TC2 CS | U7, J21 | 22 | |
| TC3 CS | U8, J22 | 21 | |
| PT1 … PT6 | J23 … J28 | 20, 19, 18, 17, 16, 15 | A6 … A1 |
| Valve 1 … 6 | J1 … J6 | 24 … 29 | Low-side AO3400A. HIGH = on. |
| Extra 12 V | J7 | 30 | Valve 7 in the config. |
| DI1 | J12 | 38 | Not pin 31. See below. |
| DI2 | J13 | 37 | |
| DI3 | J14 | 36 | |
| DI4 | J10 | 35 | |
| DI5 | J11 | 34 | |
| DI6 | J9 | 33 | |
| DI7 | J8 | 31 | |
| DI8 | J15 | 32 | |
| E-stop sense | chosen in config | example: 10 | Not a schematic net. Free: 10, 14, 39, 40, 41. |
| Unused | — | 14, 39, 40, 41 | Left free besides the sense pin you pick. |

Checked against the schematic, and where it disagrees with the obvious guess:

- **HX711 RATE is tied to GND** on U3, U4, and U5. The converters run at 10 samples/s. 80 samples/s would need RATE high, and that pin does not come to the Teensy. The firmware waits for DOUT and clocks all three chips from pin 2. It cannot select the rate.
- **Digital inputs are not DI1 = pin 31 through DI8 = pin 38.** The schematic and the change report wire them as DI7, DI8, DI6, DI5, DI4, DI3, DI2, DI1 on pins 31–38. The table above is that wiring. The config talks about DI1–DI8, and the firmware maps those names onto these pins.
- **Valve pins 24–30 match** the original plan: valves 1–6, then the extra 12 V output.
- **Display CLK/DIO pairs are pins 4/5, 6/7, and 8/9.** The report's "4–9" is these three pairs, in that order.
- **Thermocouple terminals are labeled pin 1 blue, pin 2 red.** That is the ANSI type T color code (blue positive, red negative). The example config selects type T. If the junction is type K, set `type: "K"` even if the lead colors differ.
- **E-stop sense was not assigned a pin** on Rev B. It is a config entry on purpose.

## Wiring

Board power is J16: pin 1 +12 V, pin 2 GND. The 5 V rail is the R-78E5.0 buck. Teensy VIN is fed from that 5 V through Schottky D9. Cut the VIN–VUSB pad before USB and 12 V are both connected. After the cut, the board does not run from USB alone.

**E-stop power contact.** Put it in the 12 V feed to the solenoid coils, not in J16. J16 has to stay up or the Teensy, the sensors, and the log die. The PCB's +12 V pour feeds both the buck and valve-connector pin 1, so the contact belongs on the stand side of the coils: coil +12 V comes through the E-stop, coil return goes to the valve connector pin 2 (the MOSFET drain). The flyback diodes on the board are across pin 1 and pin 2; keep the E-stop out of that local loop if you can, on the supply side of the coil positive.

**E-stop sense.** A second contact on the mushroom, to the GPIO in `estop.pin`. Example wiring for pin 10: normally closed to +3.3 V, firmware pulldown, `active: low`. Do not feed this pin from 12 V or 5 V. Teensy 4.1 pins are not 5 V tolerant.

**Valves, J1–J7.** Pin 1 is +12 V, pin 2 is the switched return. The load sits between them. HIGH on the gate turns the low-side MOSFET on. The part is sized for about 1 A per channel and 5 A total. The gate has a 1k series resistor and a 10k pulldown to source, so an un-driven pin stays off.

**Digital inputs, J8–J15** (see the table for which header is which DI). Pin 1 is +3.3 V, pin 2 is the signal, with a 10k pulldown to GND on the board. Close the contact to read HIGH. The silkscreen says PWR and RTN; RTN here is the signal, not ground. Do not switch these to +5 V.

**Pressure, J23–J28.** Pin 1 GND, pin 2 +5 V, pin 3 SIG. Not +5 V / GND / SIG. A 0.5–4.5 V ratiometric sensor: 4.5 V at the sensor is 3.0 V at the ADC, through 10k series and 20k to GND, with 100 nF at the pin. Red to pin 2, black to pin 1, signal to pin 3.

**Load cells, J17–J19.** Pin 1 excitation +5 V, pin 2 excitation GND, pin 3 signal green, pin 4 signal white, into HX711 channel A. If a cell reads the wrong sign, swap pin 3 and pin 4 or set a negative `counts_per_unit`.

**Thermocouples, J20–J22.** Pin 1 blue, pin 2 red, into the MAX31856. Chip-down on the 3.3 V rail. DRDY and FAULT are not connected; faults show up in `tc_fault`.

**Displays, J29–J31.** Pin 1 +5 V, pin 2 GND, pin 3 CLK, pin 4 DIO. TM1637-style modules. The firmware bit-bangs them open-drain. Many modules pull CLK and DIO up to their VCC. If that pull-up goes to +5 V, the Teensy pin sees 5 V when released. Use a module whose pull-ups are to 3.3 V, or level-shift, before trusting a 5 V display on these headers.

While the E-stop latch is set, all three displays blink `STOP` (sense still tripped) or `RST` (released, waiting for the reset button) instead of the page. The CSV does not pause.
