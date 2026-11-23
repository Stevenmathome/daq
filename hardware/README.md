# DAQ Rev B hardware

KiCad 9 project for the current DAQ Rev B board: a Teensy 4.1 data-acquisition and seven-valve controller. Three HX711 load cells, six pressure inputs, three MAX31856 thermocouples, eight panel inputs, three TM1637-style display headers, and a hardware E-stop that drops only the valve 12 V rail. F1 on the front edge is a user-replaceable ATO/ATC blade-fuse holder.

Open `daq-rev-b/DAQ Rev B.kicad_pro` in KiCad 9. The folder name has no spaces. The project files keep the name KiCad saved them with. Symbols and the Teensy footprint live in `daq-rev-b/lib/` and the library tables use `${KIPRJMOD}`, so the project opens from this directory without any extra libraries.

## Where things are

| Path | Contents |
|---|---|
| `daq-rev-b/DAQ Rev B.kicad_sch` | Schematic, including the drawing sheets |
| `daq-rev-b/DAQ Rev B.kicad_pcb` | PCB |
| `daq-rev-b/lib/` | Vendored symbols, the Teensy 4.1 footprint, and the F1 blade-fuse holder footprint and 3D model |
| `daq-rev-b/fab/DAQ_RevB_gerbers.zip` | Gerbers and drills for the board house |
| `daq-rev-b/fab/gerbers/` | The same Gerbers unpacked |
| `daq-rev-b/fab/DAQ_RevB_BOM_JLCPCB.csv` | JLCPCB BOM. The Teensy is not on it |
| `daq-rev-b/fab/DAQ_RevB_CPL_JLCPCB.csv` | JLCPCB pick-and-place |
| `daq-rev-b/fab/DAQ_RevB_BOM_full.csv` | BOM with manufacturer part numbers |
| `daq-rev-b/docs/DAQ_RevB_docs.pdf` | Eight-sheet drawing set |
| `daq-rev-b/docs/DAQ_RevB_S02`–`S08` `.kicad_sch` | Drawing-sheet sources. The schematic links them |
| `daq-rev-b/docs/png/` | PNG previews of those sheets |
| `daq-rev-b/docs/DAQ_RevB_solenoid_research.md` | Solenoid current notes |
| `daq-rev-b/review/DAQ_RevB_report.md` | Design report |
| `daq-rev-b/review/DAQ_RevB_schematic.pdf` | Schematic PDF |
| `daq-rev-b/review/DAQ_RevB_render_*.png` | Top, bottom, and isometric renders |

## Ordering

- The Teensy 4.1 is hand-fitted. JLCPCB does not place it. Solder the two 1×24 sockets and plug the module in. Cut the VIN–VUSB pad on the back of the Teensy before USB and 12 V are connected together. After that cut the board does not run from USB alone. J16 still needs 12 V, including while uploading firmware.
- With no E-stop fitted, jumper J32 pins 1–2. Those pins are the normally-closed contact that turns on Q10, the P-FET in the valve 12 V rail. Leave them open and the valves stay unpowered. Pin 10, the sense input, also stays low, so the firmware holds the valve latch.
- Size the 12 V supply for 15 A or more. Each valve channel is up to 2 A, and all seven on is 14 A.
- F1 is a Littelfuse 178.6165.0002 ATO/ATC blade-fuse holder (LCSC C207061) on the front edge. The holder is on the JLCPCB BOM. The fuse is not: fit a standard 20 A ATO/ATC fuse after assembly. If it blows, pull it and replace it from the front edge. The fuse body stands about 20 mm off the board. If the board mounts components-down toward the L-bracket, use standoffs about 25 mm long so the fuse clears the bracket.

Check the JLCPCB placement preview before paying. Look at Q1–Q8 pin 1, U3–U8 pin 1, electrolytic polarity, diode cathodes, and the Phoenix terminal orientation.
