# DAQ Rev B

Firmware for the Teensy 4.1 on the DAQ Rev B board. The operator interface is the panel: switches, a button, three 7-segment displays, and an E-stop on an L-shaped bracket, wired to the board's input and display headers. The other face of the bracket carries the connectors out to the stand. A laptop is optional. USB serial is a CSV log and a few commands, not a control GUI.

The pin numbers below were checked against the Rev B schematic and the Rev B v2 hardware. Digital inputs are not in DI-number order on pins 31–38, and the HX711 rate is set by solder jumpers. Both are called out in the pin map.

The KiCad project, fab files, and drawing set are in [hardware/](hardware/README.md).

## Safety

Valve gates are driven low before `setup()` does anything else, and again on every boot. HIGH turns a MOSFET on.

The hardware E-stop removes 12 V from the valve coils only. Q10, a P-FET in the valve 12 V rail, is driven by the normally-closed contact on J32 pins 1-2. Opening that contact turns the valve rail off. Logic and sensors stay powered, so sampling, the displays, and the CSV continue through a trip. The firmware does not drive Q10. It only watches the sense pin.

That sense is Teensy pin 10, through 1 kΩ and 100 nF, with a 10 kΩ pulldown on the board. HIGH means the E-stop is closed (OK). LOW means tripped, or the E-stop is unplugged. The latch then forces every valve gate off. The displays blink `STOP` while the line is still low, and blink `RST` after it goes high again, until the configured reset input. Reset is ignored while the sense is still low, including a reset that was already held. Press it again after release.

With no E-stop fitted, J32 pins 1-2 need a jumper. Otherwise Q10 keeps the valve rail off and the valves stay unpowered. The sense pin also reads low until something holds it high, so the firmware latch stays set too.

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
| `load_cells` | Name, unit, `slope`, and `offset`. Raw is HX711 counts. Optional `points` table. |
| `pressures` | Same line. Raw is sensor volts, before the 10k/20k divider. |
| `thermocouples` | MAX31856 type, plus a correction line. Raw is the chip's degC. `slope: 1` and `offset: 0` leave it unchanged. |
| `pages` | Each page is the three channels the displays show, display 1 then 2 then 3. The page input cycles the list. |
| `inputs` | DI1–DI8, each exactly once. `action` is `arm`, `reset`, `toggle_valve`, `momentary_valve`, `tare`, `display_page`, or `none`. |
| `estop` | Sense GPIO, `active`, `pull`, and which input is the reset button. |
| `interlocks` | `valve` N requires an input whose action is `arm`. |

A toggle already ON when the board boots does not energize. Cycle it. That is deliberate: boot forces the valves off, and a toggle is an edge, not a level.

## How to calibrate

Every analog channel uses one line:

```text
value = slope * raw + offset
```

`raw` is not the same number for every kind of channel:

| Channel | raw |
|---|---|
| LC1–LC3 | HX711 counts |
| PT1–PT6 | volts at the sensor, before the 10k/20k divider |
| TC1–TC3 | the MAX31856 temperature in °C |

Two readings fix the line. `raw0` should read `value0`, `raw1` should read `value1`:

```text
slope  = (value1 - value0) / (raw1 - raw0)
offset = value0 - slope * raw0
```

A 0.5–4.5 V, 0–100 PSI transducer is that formula with the datasheet endpoints:

```text
slope  = (100 - 0) / (4.5 - 0.5) = 25
offset = 0 - 25 * 0.5 = -12.5
```

The example config already uses those numbers. ADC code 2730 is 2.2 V at the pin and 3.3 V at the sensor, which the line reads as 70 PSI.

A load cell is the same shape. Unloaded counts `Z`, counts `L` with a known weight `W`:

```text
slope  = W / (L - Z)
offset = -slope * Z
```

A negative slope flips a cell whose green and white wires are swapped.

An optional `points` list replaces the line when it is present. Each entry is `[raw, value]`. Two to eight points. Raw values must increase. Values must keep rising or keep falling, not both. Between points the firmware draws a straight segment. Outside the first and last point it extends that end segment.

Which numbers are actually used, per channel:

1. EEPROM, if `CAL SAVE` stored that channel. Boot prints `cal=eeprom`.
2. Otherwise `config.yaml`. Boot prints `cal=config`.
3. The tare button is applied after either of those. It is not saved. Reboot clears it. Boot never prints a tare source because tare starts at zero.

A bench session that has not been saved prints `cal=session` from `CAL SHOW` and from `INFO`. Reboot throws it away.

### Pressure from the datasheet

Nothing to do if the sensor is 0.5–4.5 V and 0–100 PSI. The example is already that line. For a 0–150 PSI sensor with the same voltages, set `slope: 37.5` and `offset: -18.75` (`150 / 4` and `-37.5 * 0.5`).

### Load cell on the bench

1. Open the serial port and wait until rows are printing. Opening the port reboots the board.
2. Unload the cell.
3. Send `CAL LC1 ZERO`. The current counts become the zero. Slope stays whatever the file (or EEPROM) had.
4. Apply a known load, for example 50 lbf.
5. Send `CAL LC1 SPAN 50`.
6. Send `CAL SHOW`. The LC1 block is YAML you can paste over that cell in `config.yaml`.
7. Send `CAL SAVE` if this board should keep the line across reboots without editing the file.

`CAL LC1 SPAN` without a `ZERO` in this session uses the raw where the current line already reads zero. On the example config that raw is 0, which is not an unloaded cell. Zero it first.

### Several points instead of one line

1. `CAL CLEAR LC1` if you want to leave the old line behind. Clearing writes EEPROM, so the file's line is what remains.
2. At each known load, send `CAL LC1 POINT <value>`. The first point is stored and the line is still used. The second point turns the table on.
3. `CAL SHOW`, then `CAL SAVE` or paste the block into `config.yaml`.

A point that repeats a raw, or that makes the values fold back, is rejected and the previous table is kept.

### Thermocouple correction

Leave `slope: 1` and `offset: 0` unless the probe is off. An ice bath is `CAL TC1 ZERO` (this raw should read 0 °C). A second known temperature is `CAL TC1 SPAN 100`. The chip type is separate from this line. This board is type K.

### Tare

The tare button, and `TARE LC1` or `TARE ALL`, subtract the live reading so the cell shows zero. They do not change slope, offset, or points, and they do not touch EEPROM. Power cycle clears them. Use `CAL … ZERO` when the zero should survive a reboot.

`CAL CLEAR` drops every EEPROM override and reloads the file. `CAL CLEAR PT1` does that for one channel. Both write EEPROM immediately.

### E-stop sense

```yaml
estop:
  pin: 10
  active: low   # LOW = tripped or unplugged; HIGH = closed, OK
  pull: none    # the board already has the 10k pulldown
  reset: DI7
```

Pin 10 is the Rev B v2 sense input. The board puts 1 kΩ in series, 100 nF to ground, and 10 kΩ to ground, so the firmware pull is `none`. `active: low` matches the pin: HIGH is healthy. The check rejects a pull-up or pull-down on this pin, and it rejects `active: high`. Other free GPIOs are **14, 39, 40, and 41**.

A digital-input header can be the sense line only if that input's `action` is `none`. Those headers already have a 10k pulldown, so `pull` must be `none` or the firmware would fight the resistor.

With no E-stop fitted, jumper J32 pins 1-2, or the valve rail stays off and pin 10 reads low so the firmware latch stays set.

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

The Teensy VIN–VUSB pad has to be cut (PJRC documents the pads on the back of the board). After the cut, USB does not power the Teensy. J16 needs 12 V for the board to run, including during upload. The E-stop does not belong in series with J16. Q10 already opens only the valve 12 V rail. Jumper J32 pins 1-2 when no E-stop is plugged in, or that rail stays off.

`pytest` covers the config checks, the pressure and load-cell math, the E-stop latch rules, and that the CSV column list in the firmware matches the generator.

## Serial log

The port is the Teensy USB serial device. Tools ask for 115200 baud; USB CDC ignores it. On macOS the device is `/dev/cu.usbmodem…`.

```bash
pio device monitor -b 115200
```

Connecting resets the board. The first lines are comments (`#`). Data rows follow at `stream_hz` (80 Hz in the example). SJ1–SJ3 ship bridged to +3.3 V, so the load cells convert at 80 samples/s. Cut those jumpers and bridge the GND side for 10 samples/s, and lower `stream_hz` to match or the log repeats each sample.

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
| `STREAM <0-100>` | Row rate. 0 pauses rows. Does not touch the valves. 80 matches the factory HX711 jumpers. |
| `VALVE <1-7> <0\|1>` | Same rules as a panel toggle: rejected while latched or disarmed. |
| `ALLOFF` | Clears every valve request. |
| `TARE <LC1\|LC2\|LC3\|ALL>` | Subtracts the live reading until reboot. Does not change slope, offset, or EEPROM. |
| `CAL <ch> ZERO` | Current raw reads 0. Keeps slope, drops any point table. Not saved until `CAL SAVE`. |
| `CAL <ch> SPAN <value>` | Current raw reads `<value>`. Builds slope and offset from the last `ZERO` (or from the line's existing zero). |
| `CAL <ch> POINT <value>` | Adds `[raw, value]`. Two or more points replace the line. |
| `CAL SHOW` | Prints YAML for the active calibration, with `source=config`, `eeprom`, or `session`. |
| `CAL SAVE` | Writes session changes, and channels already in EEPROM, to EEPROM. |
| `CAL CLEAR [ch]` | Drops EEPROM overrides and reloads `config.yaml`. |
| `PAGE` | Next display page. |
| `RESET` | Clears the E-stop latch only if the sense line is released. |

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
| E-stop sense | J32 (power), pin 10 (sense) | 10 | 1 kΩ, 100 nF, 10 kΩ pulldown. HIGH = OK, LOW = tripped or unplugged. |
| Unused | — | 14, 39, 40, 41 | Not connected on Rev B v2. |

Checked against the schematic, and where it disagrees with the obvious guess:

- **HX711 RATE defaults to +3.3 V through SJ1–SJ3**, so U3–U5 run at 80 samples/s. Cut the +3.3 V bridge and solder the other side for 10 samples/s. RATE is not a Teensy pin. The firmware still clocks all three chips from pin 2 when DOUT falls, and the not-ready wait is long enough for the 10 sample/s jumper.
- **Digital inputs are not DI1 = pin 31 through DI8 = pin 38.** The schematic and the change report wire them as DI7, DI8, DI6, DI5, DI4, DI3, DI2, DI1 on pins 31–38. The table above is that wiring. The config talks about DI1–DI8, and the firmware maps those names onto these pins.
- **Valve pins 24–30 match** the original plan: valves 1–6, then the extra 12 V output.
- **Display CLK/DIO pairs are pins 4/5, 6/7, and 8/9.** The report's "4–9" is these three pairs, in that order.
- **Thermocouple terminals are T+ on pin 1 and T- on pin 2.** ANSI type K is yellow positive and red negative. The example config selects type K.
- **E-stop sense is Teensy pin 10** on Rev B v2. The valve-power contact is J32 pins 1-2, driving P-FET Q10. The firmware only senses pin 10.

## Wiring

Board power is J16: pin 1 +12 V, pin 2 GND. The 5 V rail is the R-78E5.0 buck. Teensy VIN is fed from that 5 V through Schottky D9. Cut the VIN–VUSB pad before USB and 12 V are both connected. After the cut, the board does not run from USB alone.

**E-stop.** J32 pins 1-2 are the normally-closed contact in the gate drive of Q10, the P-FET that feeds 12 V to the valves. The contact opens and Q10 drops that rail. J16 stays powered, so the Teensy and the sensors keep running. Pin 10 is only the sense: 1 kΩ from the switched node, 100 nF to ground, 10 kΩ pulldown. HIGH is closed and healthy. LOW is open, tripped, or unplugged. Do not feed pin 10 from 12 V or 5 V. With no E-stop plugged in, jumper J32 pins 1-2. Leave them open and the valves have no 12 V, and pin 10 stays low so the firmware latch stays set.

**Valves, J1–J7.** Pin 1 is switched +12 V (after Q10), pin 2 is the MOSFET return. The load sits between them. HIGH on the gate turns the low-side MOSFET on. Each channel is sized for up to 2 A. All seven on is 14 A, so the 12 V supply should be 15 A or more. The gate has a 1 kΩ series resistor and a 10 kΩ pulldown to source, so an un-driven pin stays off.

**Digital inputs, J8–J15** (see the table for which header is which DI). Pin 1 is +3.3 V, pin 2 is the signal, with a 10k pulldown to GND on the board. Close the contact to read HIGH. The silkscreen says PWR and RTN; RTN here is the signal, not ground. Do not switch these to +5 V.

**Pressure, J23–J28.** Pin 1 GND, pin 2 +5 V, pin 3 SIG. Not +5 V / GND / SIG. A 0.5–4.5 V ratiometric sensor: 4.5 V at the sensor is 3.0 V at the ADC, through 10k series and 20k to GND, with 100 nF at the pin. Red to pin 2, black to pin 1, signal to pin 3.

**Load cells, J17–J19.** Pin 1 excitation +5 V, pin 2 excitation GND, pin 3 signal green, pin 4 signal white, into HX711 channel A. If a cell reads the wrong sign, swap pin 3 and pin 4 or set a negative slope.

**Thermocouples, J20–J22.** Pin 1 is T+ (ANSI type K yellow), pin 2 is T- (red), into the MAX31856. Chip-down on the 3.3 V rail. DRDY and FAULT are not connected; faults show up in `tc_fault`.

**Displays, J29–J31.** Pin 1 +5 V, pin 2 GND, pin 3 CLK, pin 4 DIO. TM1637-style modules. The firmware bit-bangs them open-drain. Many modules pull CLK and DIO up to their VCC. If that pull-up goes to +5 V, the Teensy pin sees 5 V when released. Use a module whose pull-ups are to 3.3 V, or level-shift, before trusting a 5 V display on these headers.

While the E-stop latch is set, all three displays blink `STOP` (sense still tripped) or `RST` (released, waiting for the reset button) instead of the page. The CSV does not pause.
