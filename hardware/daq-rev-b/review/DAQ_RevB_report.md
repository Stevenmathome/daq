# DAQ Rev B v4 - integration / usability review (Sun Nov 22 2026, ~8:47 PM CST)
KiCad 9.0.2. The DAQ 2 originals are untouched (hash-verified: pcb 94a719cee704126c, sch 1799c0af904a158e, pro af384d143baca7c9).

This revision is a first-power-up / wiring review of v3, before a JLCPCB order. The schematic and copper are unchanged. Silkscreen and the documentation set were updated so Steven can see, on the board, which pin is which.

## Status (v4)
| Check | Result |
|---|---|
| ERC, all 8 sheets (`review/erc_final.rpt/.json`) | **0 errors, 0 warnings** |
| DRC + schematic parity (`review/drc_final.rpt/.json`) | **0 violations, 0 unconnected, 0 parity issues** |
| Board | 2-layer, 1.6 mm, 1 oz, **142.5 x 138.0 mm** (unchanged) |
| Docs | `docs/DAQ_RevB_docs.pdf` (8 sheets) + `docs/png/` |
| Archive | `/workspace/pcb/DAQ_Rev_B_v4.tgz` |
| Progress render | `/workspace/pcb/progress/09_review.png` (top 3D, new silk visible) |

## Direct answer: where does the E-stop go?
**J32**, the 4-pin screw terminal on the **front / bottom edge** (left of the three display terminals).

- Pins **1-2** (silk **CUT**): NC contact that hardware-cuts +12V to all valves (Q10). Polarity-free, ~110 uA.
- Pins **3-4** (silk **SENSE**): NC contact to Teensy pin 10. HIGH = OK, LOW = tripped or unplugged.
- If no E-stop is fitted yet, **jumper pins 1-2** or the valves stay off. The board now says `JUMPER 1-2 IF NO E-STOP`.

## What was fixed on the board
Every external connector previously had only its reference (J1, J16, ...) on the silkscreen, except a short J32 note. Function names lived on the Fab layer, which is not printed on the finished PCB. That is the class of problem that led to the E-stop question.

Added or clarified on F.SilkS (DRC kept at 0):

- **J16 12 V in:** `12V IN`, **+** on pin 1 (right when looking at the front of the terminal), **-** on pin 2.
- **J32 E-stop:** jumper callout; `CUT` under pins 1-2, `SENSE` under pins 3-4, pin numbers 1-4.
- **J1-J6 valves:** `V1`..`V6` on the wire side, **+** (always-hot +12V_VALVE) and `RTN` (switched return) at the pins. Pin 1 arrow is the + pin.
- **J7:** `OUT` (valve 7 / 12 V output), same +/- convention.
- **J12, J13, J14, J10, J11, J9, J8, J15:** `DI1`..`DI8` (the J-numbers are not in DI order), plus `IN` and `3V3` at the pins. Switch between the two pins; close to +3V3 = HIGH.
- **J20-J22:** `TC1`..`TC3`, `T+` on pin 1, `T-` on pin 2 (type-agnostic, not blue/red or yellow/red).
- **J23-J28:** `PD1`..`PD6`, `GND` / `5V` / `SIG` (pins 1 / 2 / 3). Amazon 3-wire is black / red / yellow-or-green in that pin order, not red-black-signal starting at pin 1.
- **J17-J19:** `LC1`..`LC3`, `E+` `E-` `A+` `A-` (pins 1-4).
- **J29-J31:** `DISP1`..`DISP3`, `5V` `GND` `CLK` `DIO`.
- **SJ1-SJ3:** `80` on the +3V3 side (default, copper already bridges 1-2), `10` on the GND side.

Docs were updated to match: first-power checklist, the side-edge pin-1 convention (arrow is pin 1; pin 1 is left-most on the top and bottom edges, right-most on the left and right edges), the USB-only power correction, thermocouple type, pressure colours, 5 V budget, and a TM1637 5 V-tolerance warning.

## Firmware (no repo changes made — list for the parent)

`firmware/include/pins.h` on GitHub main **matches the board netlist exactly**: E-stop = pin 10; valves 24-30; LC DOUT 3/0/1, SCK 2; PD 20..15; TC CS 23/22/21, SPI 11/12/13; displays CLK/DIO 4/5, 6/7, 8/9; DI 38, 37, 36, 35, 34, 33, 31, 32. No pin-map changes are needed.

`firmware/config.yaml` thermocouples are type K. Silkscreen is T+ (pin 1) / T- (pin 2). ANSI type K is yellow positive and red negative.

## Needs Steven's decision (not changed)
- **TM1637 5 V vs Teensy 4.1:** display pin 1 is +5 V. Teensy CLK/DIO pins are **not 5 V tolerant**. If the module pulls CLK/DIO up to 5 V, that can damage the Teensy. Recommendation: use 3.3 V modules, or run VCC at 3.3 V if the displays stay bright enough. Do not leave this as an assumed "3.3 V logic is fine on a 5 V module."
- **3V3 on the panel:** +3V3 is brought out to every DI terminal (pin 1) and J32 pin 3, with no series resistor or PTC. A shorted panel wire can collapse the Teensy 3.3 V rail. Recommendation: a future single PTC (or a 3V3_PANEL net) on those feeds. Not done here (routing change).
- **Valve indicator LEDs:** none fitted. Optional future addition; not required for function.
- **Larger valve terminals:** Phoenix MPT 0,5 is rated 6 A (fine for 2 A electrically) but max wire is 0.5 mm² (20 AWG). If the solenoid leads are thicker, use a ferrule or a short pigtail rather than changing the footprint.
- **Dedicated test points** for +12V_VALVE, +5 V, +3V3 and GND. Not added.
- **USB under an L-bracket:** the Teensy USB connector is mid-board (left end of U1, ~27 mm in from the left-edge terminals). It plugs from above. If the board is mounted component-side toward a plate, leave a cutout or access from above.

## FYI (checked, no change needed)
- Valve outputs already have an M7 flyback on each channel, 1k gate series, **10k gate pulldowns** (valves stay off during boot), and +12 V / switched return on each terminal. No LEDs, as above.
- Digital inputs already have 10k pulldowns and close to +3V3 (active high), matching firmware.
- SJ1-SJ3 are copper solder jumpers, default-bridged 1-2 = 80 SPS. They are correctly excluded from the JLC BOM.
- **5 V budget (R-78E5.0-1.0, 1 A):** Teensy 0.10-0.25 A (includes 3.3 V loads) + HX711 AVDD ~10 mA + six pressure sensors ~60-90 mA + three TM1637 <= 240 mA ≈ 0.45-0.60 A. Comfortable, but do not add more 5 V loads. Teensy 3.3 V regulator headroom is ample (MAX31856 + HX711 DVDD + DI/E-stop are tens of mA vs ~250 mA).
- **USB-only power:** after the required VIN-VUSB cut, USB alone does **not** power the Teensy or the 5 V rail. 12 V and the 20 A fuse are required for logging and for programming. With 12 V on and the E-stop open, Teensy and sensors stay up; valves stay off. A previous docs sentence that said USB programming works with the board unpowered was wrong and has been corrected.
- **Input:** J16 is 12 V DC only. The R-78 would accept a wider range, but valve coils and the 15 V zeners are sized for 12 V — do not feed 24 V. Reverse polarity is blocked by Q8 (nothing downstream powers; the fuse does not blow).
- **Ground:** sensor returns and valve current share the board GND pours. Acceptable on this 2-layer board if the 12 V return at J16 is short and fat. A star-ground split was not done (bigger change).
- **Mechanicals:** connectors face the four edges; fuse holder is on the front edge for hand replacement on standoffs; H1 is close to J28 (labels placed around it); USB as above. An inserted ATO fuse stands ~20 mm above the board (~25 mm standoffs if components face the L-bracket).
- **Not assembled by JLC:** Teensy 4.1 and its two 24-pin female headers (hand-solder); 20 A ATO blade fuse (user supplied); SJ1-SJ3 are copper, not parts.
- **JLC stock (live, this evening CST):** F1 holder C207061 stock 193; AON6407 (Q8, Q10) C7603355 stock 795; MAX31856 C116632 stock **268** (watch this one). Verify DFN5x6 pin-1 orientation of Q8/Q10 in the JLC CPL preview before ordering. No DFN rotation-correction rule is applied.
- Load-cell 5-wire: no shield pin; tie the shield to E- at one end only.
- Gate pulldowns, flybacks, E-stop fail-safe, and the first-power jumper requirement were already in the v3 design; they are now visible on the board and in the assembly checklist.

## What was not changed
No schematic nets, copper, footprints (other than moving the J28 reference text), parts, or board size. Valve terminals were not upsized. No short-protection, test points, or valve LEDs were added.

---
# DAQ Rev B v3 - replaceable ATO fuse holder (Sun Nov 22 2026, evening CST)
KiCad 9.0.2. The DAQ 2 originals are untouched (hash-verified).

## Fuse holder change (this revision)
F1 (previously a 20 A non-resettable SMD fuse, LUTE LTC2410-2200TSK) is now a **board-mounted holder for a standard regular-size ATO/ATC automotive blade fuse**, so a blown fuse can be pulled and replaced by hand with the board on standoffs.

| Item | Choice |
|---|---|
| Holder | Littelfuse **178.6165.0002** (ATO / FKS / ATC PCB holder, 4-pin THT, vertical top entry) |
| LCSC | **C207061** |
| Price / stock (live, this evening) | **$2.32** qty-1, **193** in JLC stock, library type **Extended** |
| Ratings | 80 V, **22.5 A continuous / 30 A max** (silver-plated 4-pin terminals). Design load 14 A; 20 A fuse. |
| Assembly | **JLC can place** it as a through-hole Extended part (same class as the Phoenix terminals). It can also be hand-soldered. |
| Fuse | **20 A ATO blade fuse, user supplied** — not on the JLC BOM, not in the shipment. Noted in the full BOM, assembly notes (sheet 7) and power budget (sheet 6). Typical colour: yellow. |
| Placement | Front / bottom edge, immediately below J16 (12 V input), centre at **(114.5, 147.25) mm**. The long axis is parallel to the edge. The fuse pulls straight up and is reachable with the board on standoffs. |
| Board size | **Unchanged: 142.5 x 138.0 mm**. Existing pour widths were kept and extended to the holder (~13.3 mm x 2 layers under F1, well above 20 A at 10 C rise). The holder pads are PTH and stitch the layers. |
| ERC / DRC | **0 / 0** (schematic parity included) |

An ESTOP_A bottom-copper run that used to follow the board edge was rerouted around the holder (along y=143.6 mm, then down past D10).

If the board is mounted with components facing the L-bracket, use ~25 mm standoffs (an inserted ATO fuse stands ~20 mm above the board) or let the holder sit past the bracket edge. Components facing away from the bracket need no extra height.

---
# DAQ Rev B v2 - change report (Phase 3 update, Sun Nov 22 2026, CST)
KiCad 9.0.2. The DAQ 2 originals are untouched (hash-verified). The Phase 2 report is kept below as history; where it conflicts with this section, this section wins.

## Status (v2)
| Check | Result |
|---|---|
| ERC, all 8 sheets (`review/erc_final.rpt/.json`) | **0 errors, 0 warnings** |
| DRC + schematic parity (`review/drc_final.rpt/.json`) | **0 violations, 0 unconnected, 0 parity issues** |
| Board | 2-layer, 1.6 mm, 1 oz, **142.5 x 138.0 mm**, 4x M3 mounting holes (3.2 mm NPTH, 4 mm from the edges, 7 mm keepout) |
| Docs | `docs/DAQ_RevB_docs.pdf` (8 sheets, KiCad frame and title block) + `docs/png/` previews |

## What changed in v2
1. **Solenoid current re-design** (research table: `docs/DAQ_RevB_solenoid_research.md`, sheet 6): 2.0 A per channel nominal (2.15 A worst case), 14 A total (15.05 A worst case), supply >= 12 V / 15 A.
   - Q8 reverse-polarity FET: AO4407A -> single **AON6407** (100 A, 4.1 mOhm, LCSC C7603355): 0.80 W at 14 A.
   - F1: **20 A fast fuse** (LCSC C54824505, non-resettable; no SMD PTC holds 14 A).
   - J16 (12 V input): **KF128 5.08 mm 2-pin** (LCSC C474952).
   - Valve bus: B.Cu strip + F.Cu pours, minimum 6.2 mm wide on B.Cu (IPC-2221 dT 23 C at 12.9 A with all valves on, with parallel F.Cu).
   - J1-J7 valve terminals stay Phoenix MPT 0,5 (6 A rated, 0.5 mm2 wire max).
2. **Hardware E-stop**: P-FET **Q10 (AON6407)** in the valve rail (`+12V_VALVE`). J32 4-pin terminal: pins 1-2 = NC contact A (closed = gate pulled to GND via R37 10k = valves powered; open or disconnected = gate pulled to source by R36 100k with D10 15 V zener = valves off). Pins 3-4 = NC contact B: +3V3 to `ESTOP_SENSE` -> R38 1k -> **Teensy pin 10** (`ESTOP_IN`), C27 100 nF, **R39 10k pulldown**. HIGH = E-stop OK/closed, LOW = tripped or wire disconnected. Teensy, 5 V/3.3 V logic and sensors stay powered.
3. **HX711 RATE**: three 3-way solder jumpers SJ1-SJ3, default bridged 1-2 to +3V3 = **80 SPS**. Cut and bridge 2-3 for 10 SPS (GND).
4. **Mounting**: H1-H4, MountingHole_3.2mm_M3 (NPTH) at 4.0 mm in from each corner (hole centres 134.5 x 130.0 mm apart); board outline extended (left edge x=8, bottom y=151 in KiCad coordinates).
5. **Documentation set** (sheets 2-8, KiCad sub-sheets in `docs/`, same frame/title block as the schematic): index/spec, Teensy pin table, connector pinouts J1-J32 with wire colours (2 sheets), power budget + solenoid research + design maths, assembly notes, board drawing with dimensions and holes. Title block of the schematic set: project DAQ Rev B, Steven Mendelsohn, rev B, 2026-11-22.
6. Root schematic tidy-up: E-stop network re-spaced inside the frame, long notes wrapped, sheet symbols moved to the bottom edge.
7. Fab outputs and renders in `fab/` and `review/` were regenerated after the PCB change (latest PCB DRC 0). BOM LCSC changes: F1 C54824505, J16 C474952, Q8/Q10 C7603355, 4-pin terminals C3816889 (incl. J32), R36/R37/R38/R39 C25803/C25804/C21190/C25804.

## Open items
- J1-J15, J17-J31 are Phoenix MPT 0,5 terminals: wire <= 0.5 mm2.
- F1 is non-resettable: a blown fuse means find the fault first.
- PSU must be >= 12 V / 15 A if all 7 valves are on, or sequence the valves in firmware.
- AON6407 JLC stock is low (800 for 2 per board); MAX31856 stock low (268).
- Verify pin-1 orientation of the DFN5x6 AON6407 (Q8, Q10) in the JLC CPL preview before ordering.
- Teensy 4.1 is hand-soldered (female headers); cut the VIN-VUSB pad on the Teensy underside.
- The first-fit E-stop wiring needs a jumper across J32 pins 1-2 before first power-up.

---
# Phase 2 report (history)
Prepared Sun Nov 22 2026, ~6:55 PM CST (America/Chicago). KiCad 9.0.2.
Project: `DAQ Rev B/DAQ Rev B.kicad_pro`. This is a new copy; the DAQ 2 originals are unchanged (hash-verified).

## Status
| Check | Result |
|---|---|
| ERC (`review/erc_final.rpt`) | **0 errors, 0 warnings** |
| DRC with schematic parity (`review/drc_final.rpt`) | **0 violations, 0 unconnected, 0 parity issues** |
| Board | 2-layer, 1.6 mm, 1 oz, **138.5 × 131.5 mm**: same outline as DAQ 2, about 29% of a MacBook footprint (300×210 mm) |
| Library | Teensy symbol and footprint plus the project symbols are vendored in `lib/`, with project `sym-lib-table`/`fp-lib-table`. All footprints resolve. |

Nothing was waived: every ERC/DRC warning was fixed. The fixes included:
- MAX31856 SDO set to tri-state (a shared MISO bus).
- Teensy 3V3 out pin set to power_out and the GND pins set to power_in. The original symbol marked them as outputs.
- 13 local footprint copies refreshed from the stock library. Pads were checked identical first.
- HX711, AO3400A and MAX31856 symbols moved into the project lib `DAQ_RevB`.
- Every unused IC pin got an explicit no-connect flag.

## Changes (fixes 1–8 + extras)
1. **HX711 DOUTs are now on separate GPIOs.** U3 → pin 3 (`LoadCell1_DO`), U4 → pin 0 (`LoadCell2_DO`), U5 → pin 1 (`LoadCell3_DO`). SCK stays shared on pin 2.
   - *Steven's question (can they share a pin like I2C?)* No. HX711 DOUT is a push-pull output with no address, so three chips on one wire would fight each other. Sharing SCK is fine, and is how the board does it. Read them in parallel: one clock, three data pins.
   - The true I2C alternative is the NAU7802, but it has a fixed address, so three of them would need an I2C mux. Not worth it here.
2. **AO3400A orientation fixed.** The schematic symbols were mirrored, so S/D were swapped. Q1–Q7 are now rot 180 with no mirror.
   - SOT-23 pinout: 1 = G, 2 = S, 3 = D.
   - Pad 2 (S) → GND; pad 3 (D) → valve RTN / flyback anode; gate via 1k from the Teensy, with a 10k pulldown gate→source.
   - Flyback diodes stay across each load: K = +12V, A = drain node. They are now SMD **M7 (1N4007-equivalent, SMA, JLC Basic)** instead of THT DO-41.
3. **12V input protection.** J16 → **F1 PTC BSMD2920-500-16V** (5 A hold / 10 A trip, 16 V) → **Q8 AO4407A P-FET ideal-diode reverse-polarity protection** → +12V.
   - Q8: drain = input, source = rail. Gate is pulled to GND by R35 100k and clamped by D8 BZT52C15 (15 V zener, gate–source).
   - *Why a P-FET over an SS54:* at 5 A an SS54 drops ~0.55 V and burns ~2.75 W. The AO4407A (~12 mΩ) drops ~60 mV and dissipates ~0.3 W.
   - C20 100 µF 25 V bulk sits on the protected rail.
   - **Assumption:** ≤1 A per valve channel, **≤5 A total continuous** (e.g. 5 channels at 1 A, or all 7 at ≤0.65 A).
   - J16 (Phoenix MPT 2.54 mm) is rated 6 A. The PTC trips around 10 A, so it is a wiring-fault fuse, not a precise limit.
4. **Decoupling (all JLC Basic).** 100 nF 0603 (C14663) at:
   - each HX711 VSUP/AVDD (+5V) and DVDD (+3V3): C4–C9;
   - each MAX31856 AVDD/DVDD: C10–C15;
   - R-78 input: C16, plus 10 µF C17;
   - Teensy 3V3: C18, plus 10 µF bulk C19.
   
   Existing output caps: C1 100 µF + C2 10 µF + C3 100 nF on +5V.
5. **Power traces/pours (IPC-2221, external, 1 oz, ΔT = 10 °C).** See the current math below.
6. **Teensy VIN/USB backfeed fixed.** Teensy VIN is now its own net, `TEENSY_VIN`, fed from +5V through **D9 B5819W Schottky** (Basic). The old "NEVER HAVE 12VDC AND USB ON" note is replaced.
   - **Steven must also cut the VIN–VUSB jumper pad on the back of the Teensy 4.1** (PJRC documents this).
   - After the cut, USB alone no longer powers the Teensy. 12V must be on to run it (programming over USB still works whenever 12V is on).
   - The diode alone prevents the board's 5V from backfeeding the PC. The cut keeps USB 5V from feeding the board's 5V rail.
7. **C1/C2/C3 and BOM fields.**
   - C1 → CP_Elec_6.3x7.7 (100 µF 25 V, C4747965); C2 → 0805 10 µF (C15850); C3 → 0603 100 nF (C14663). All three moved next to U2's output.
   - Every part has `LCSC`, `MPN` and `Manufacturer` fields in both the schematic and the PCB.
   - The Teensy (U1) is excluded from the JLC BOM/CPL: hand-solder 2× 1×24 female headers (HC-PM254-8.5H-1x24PZ, LCSC C41376163) and plug in the Teensy.
8. **Teensy library vendored.**
   - Symbols: `lib/teensy.kicad_sym` (Teensy4.1) and `lib/DAQ_RevB.kicad_sym` (AO4407A 8-pin, HX711, AO3400A, MAX31856).
   - Footprint: `lib/teensy.pretty/Teensy41.kicad_mod`.
   - Project tables: `sym-lib-table` and `fp-lib-table`, with paths based on `${KIPRJMOD}`.

**Extras**
- **Pressure inputs:** the 10k/20k dividers are kept (4.5 V → 3.0 V at the ADC). C21–C26 100 nF are added at the Teensy ADC pins: f_c = 1/(2π·6.67k·100n) ≈ 240 Hz.
  - J23–J28 pinout (unchanged, confirmed in the netlist): pin 1 GND, pin 2 +5V, pin 3 SIG.
  - Wire the Amazon sensor: red → +5V (pin 2), black → GND (pin 1), signal (yellow/green/white per listing) → pin 3. Note the terminal order is GND/+5V/SIG, not +5V/GND/SIG.
- **Silkscreen:** "Steven Mendelsohn" / "Red Bull Futurist", 1.5 mm text on F.Silkscreen, plus "DAQ Rev B". The old "Created By…" text was actually on **copper (F.Cu)** and has been removed.
- **Full re-route** with Freerouting 2.1 and netclasses:

  | Netclass | Track width |
  |---|---|
  | Default | 0.25 mm |
  | +3V3 | 0.4 mm |
  | +5V / TEENSY_VIN | 0.8 mm |
  | +12V branches | 1.0 mm |
  | Valve drain nets | 1.0 mm |

  - GND pours on both layers, with fan-out and stitching vias (6–7 mm grid).
  - 12V pours: F.Cu VIN_RAW / VIN_FUSED / +12V along the bottom edge, plus a **B.Cu +12V bus strip** under the valve terminals. 22 +12V vias (0.8/0.4) tie the layers together.

## Teensy 4.1 pin map (final)
| Function | Teensy pins |
|---|---|
| Load cells: LC1 / LC2 / LC3 DOUT | 3 / 0 / 1 |
| Load cells: shared SCK | 2 |
| Display 1–3 CLK/DIO | 4–9 (unchanged) |
| Thermocouple SPI MOSI / MISO / SCK | 11 / 12 / 13 |
| TC CS1 / CS2 / CS3 | 23 / 22 / 21 |
| Pressure PD_1…PD_6 (A6…A1) | 20 / 19 / 18 / 17 / 16 / 15 |
| Valves 1–6 + Extra 12V | 24–30 |
| DI_7, DI_8, DI_6, DI_5, DI_4, DI_3, DI_2, DI_1 | 31–38 |
| Free | 10, 14 (A0), 39, 40, 41 |
| Power | VIN = TEENSY_VIN (via D9); 3V3 out → +3V3 rail; GND pins 1/34/47 |

## Current math (IPC-2221 external, 1 oz = 1.378 mil, ΔT = 10 °C)
I = 0.048·ΔT^0.44·A^0.725 = 0.1322·A^0.725 (A in mil²) → A = (I/0.1322)^1.379

| Net | Design current | Required width | Implemented | Capacity @10 °C |
|---|---|---|---|---|
| VIN_RAW (J16→F1) | 5 A | 2.76 mm (150 mil²) | F.Cu pour, narrowest neck 3.6 mm | ~6.0 A |
| VIN_FUSED (F1→Q8) | 5 A | 2.76 mm | F.Cu pour, min 5.8 mm | ~8.6 A |
| +12V (Q8→bus) | 5 A | 2.76 mm | F.Cu pour, min 5.3 mm, +22 vias | ~8 A |
| +12V bus to J1–J7 | 5 A (cumulative) | 2.76 mm | B.Cu pour strip, min 4.5 mm | ~7.1 A |
| +12V branch per valve | ≤1 A | 0.30 mm | 1.0 mm | 2.4 A |
| Valve drain (Q→D/J) | ≤1 A | 0.30 mm | 1.0 mm | 2.4 A |
| +5V (R-78E, 1 A max) | ≤1 A | 0.30 mm | 0.8 mm | 2.0 A |
| +3V3 (Teensy reg., ~250 mA) | 0.25 A | 0.05 mm | 0.4 mm | 1.2 A |
| GND return | 5 A | – | solid pours on both layers + ~270 vias | – |

Vias: a 0.4 mm drill with 25 µm plating gives ≈ 49 mil² of barrel, about 2.2 A each. The 12V layer transfer uses 16+ vias, so it has well over 5 A of capacity.
AO3400A at 1 A: R_DS(on) ≈ 30–50 mΩ at 3.3 V gate drive → ≤0.05 W each. That's fine.

## Parts list (JLC, live stock checked 6:50 PM CST)
| Designators | Part | LCSC | MPN | JLC type | Stock |
|---|---|---|---|---|---|
| C1, C20 | 100 µF 25 V elec. | C4747965 | RST100UF25V006 | Extended | 6,737 |
| C2, C17, C19 | 10 µF 25 V 0805 | C15850 | CL21A106KAYNNNE | Basic | 9.27 M |
| C3–C16, C18, C21–C26 (21) | 100 nF 0603 | C14663 | CC0603KRX7R9BB104 | Basic | 53 M |
| D1–D7 | M7 SMA (flyback) | C95872 | M7 | Basic | 5.86 M |
| D8 | BZT52C15 SOD-123 | C2104 | BZT52C15 | Extended | 118,755 |
| D9 | B5819W SOD-123 | C8598 | B5819W SL | Basic | 964,141 |
| F1 | PTC 5 A/10 A 2920 | C910846 | BSMD2920-500-16V | Extended | 24,542 |
| Q1–Q7 | AO3400A SOT-23 | C20917 | AO3400A | Basic | 1.50 M |
| Q8 | AO4407A SO-8 | C2841482 | AO4407A (UMW) | Extended | 45,022 |
| R1,4,7,8,12,13,14 | 1k 0603 | C21190 | 0603WAF1001T5E | Basic | 40 M |
| R2,3,5,6,9–11,15–23,25,27,29,31,33 | 10k 0603 | C25804 | 0603WAF1002T5E | Basic | 42 M |
| R24,26,28,30,32,34 | 20k 0603 | C4184 | 0603WAF2002T5E | Basic | 4.8 M |
| R35 | 100k 0603 | C25803 | 0603WAF1003T5E | Basic | 12.9 M |
| U2 | R-78E5.0-1.0 (YLPTEC, pin-compatible with RECOM) | C22371890 | R-78E5.0-1.0 | Extended | 3,455 |
| U3–U5 | HX711 SOIC-16 | C43656 | HX711 | Extended | 5,170 |
| U6–U8 | MAX31856 TSSOP-14 | C116632 | MAX31856MUD+ | Extended | **268 (low; fine for 1–2 boards)** |
| J1–J16, J20–J22 (19) | Phoenix 1725656 2-pos | C3029316 | 1725656 | Extended (THT) | 1,259 |
| J17–J19, J29–J31 (6) | Phoenix 1725672 4-pos | C3816889 | 1725672 | Extended (THT) | 1,760 |
| J23–J28 (6) | Phoenix 1725669 3-pos | C5288763 | 1725669 | Extended (THT) | 659 |
| U1 | Teensy 4.1 + 2× HC-PM254-8.5H-1x24PZ sockets | C41376163 (sockets) | – | **Consigned / hand-solder** | 17,775 (sockets) |

- Parts cost per board: ≈ **$76** at JLC qty-1 prices. The MAX31856s ($5.28 × 3) and the 31 Phoenix terminals dominate.
- There are 10 unique Extended parts, so expect about $3 × 10 extended-part setup fees per order, plus THT assembly fees for the terminals and U2.

## Fab package (`fab/`)
- `DAQ_RevB_gerbers.zip`: F/B Cu, Mask, Paste, Silk, Edge.Cuts, and PTH + NPTH Excellon (mm) with drill maps. Upload this as-is to JLCPCB/PCBWay.
  - 2-layer, 1.6 mm, 1 oz. The minimum track is 0.25 mm and the minimum via 0.6/0.3 mm, both inside JLC's free/standard capability.
- `DAQ_RevB_BOM_JLCPCB.csv`: Comment, Designator, Footprint, LCSC (U1 excluded).
- `DAQ_RevB_BOM_full.csv`: adds MPN, manufacturer, Basic/Extended, live stock and price.
- `DAQ_RevB_CPL_JLCPCB.csv`: Designator, Mid X, Mid Y, Layer, Rotation. All parts are on the top side.
  - Rotation corrections follow the JLCKicadTools rotation DB: SOT-23 −90°, SOIC/TSSOP +270°, CP_Elec_6.3x7.7 +180°; chips, SMA, SOD-123 and 2920 get 0°.
  - **Check the placement preview on JLC before paying.** Look at Q1–Q8 pin 1, U3–U8 pin 1 dots, C1/C20 polarity, D1–D9 cathode bars, and the Phoenix terminal orientation (THT; JLC's models sometimes differ).

## Images
- `review/DAQ_RevB_render_top.png`, `review/DAQ_RevB_render_bottom.png`, `review/DAQ_RevB_render_iso.png` (3D)
- `review/DAQ_RevB_top_copper.png`, `review/DAQ_RevB_bottom_copper.png` (layers)
- `review/DAQ_RevB_schematic.pdf` / `.png`
- Progress series in `/workspace/pcb/progress/`:
  - 01 schematic ERC 0
  - 02 / 02b placement
  - 03 / 03b routed copper
  - 04 / 04b / 04c final 3D
  - 05 final schematic

## Open questions / notes for Steven
1. **Cut the Teensy VIN–VUSB pad** before plugging in USB with 12V present. After the cut, USB alone won't power the Teensy.
2. **Total 12V budget:** the design is good for ≤5 A continuous total. If more than 5 valves at 1 A each will ever be on at once, tell me the real solenoid currents and I'll size up (6 A terminals are the next limit).
3. The **pressure terminal order is GND / +5V / SIG** (pins 1/2/3). Check the silkscreen before wiring the Amazon sensors. The 4.5 V full scale reads 3.0 V at the ADC.
4. A **DIP mode selector** was not added. With a single sensor type (0.5–4.5 V ratiometric), the fixed 10k/20k divider is right. A selector would only matter for mixing 0–10 V or 4–20 mA sensors later.
5. The **MAX31856 has only 268 in stock** at JLC. That's fine for 1–2 boards (3 each), but order soon.
6. R-78E5.0-1.0: the footprint is RECOM R-78E-0.5 THT (same SIP-3 pinout/pitch), and the part is the YLPTEC clone because the RECOM part has 0 JLC stock.
7. The board size is unchanged (138.5 × 131.5 mm). There is visible free space in the center and lower middle. A future Rev C could shrink to about 120 × 110 mm by tightening the left terminal column and the displays, but that wasn't required now.
