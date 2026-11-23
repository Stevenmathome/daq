"""Validate config.yaml and render the C++ header the firmware compiles.

The Teensy never parses YAML. PlatformIO runs this before the build.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PINS_H = ROOT / "include" / "pins.h"

LC_IDS = ("LC1", "LC2", "LC3")
PT_IDS = tuple(f"PT{i}" for i in range(1, 7))
TC_IDS = ("TC1", "TC2", "TC3")
DI_IDS = tuple(f"DI{i}" for i in range(1, 9))
CHANNEL_IDS = LC_IDS + PT_IDS + TC_IDS

TC_TYPES = {"B": 0, "E": 1, "J": 2, "K": 3, "N": 4, "R": 5, "S": 6, "T": 7}

ACTIONS = {
    "none": 0,
    "arm": 1,
    "reset": 2,
    "toggle_valve": 3,
    "momentary_valve": 4,
    "tare": 5,
    "display_page": 6,
}

PULLS = {"none": 0, "down": 1, "up": 2}

TOP_KEYS = {
    "version",
    "stream_hz",
    "debounce_ms",
    "load_cells",
    "pressures",
    "thermocouples",
    "pages",
    "inputs",
    "estop",
    "interlocks",
}

CSV_COLUMNS = [
    "t_us",
    "LC1",
    "LC2",
    "LC3",
    "LC1_raw",
    "LC2_raw",
    "LC3_raw",
    "PT1",
    "PT2",
    "PT3",
    "PT4",
    "PT5",
    "PT6",
    "PT1_counts",
    "PT2_counts",
    "PT3_counts",
    "PT4_counts",
    "PT5_counts",
    "PT6_counts",
    "TC1",
    "TC2",
    "TC3",
    "tc_fault",
    "valves",
    "inputs",
    "arm",
    "estop_sense",
    "estop_latch",
    "page",
]

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._+/-]{0,23}$")
_UNIT = re.compile(r"^[A-Za-z0-9.%/]{1,8}$")
_ARRAY = re.compile(
    r"constexpr\s+uint8_t\s+(PIN_[A-Z0-9_]+)\s*\[\d+\]\s*=\s*\{([^}]+)\}\s*;"
)
_SCALAR = re.compile(r"constexpr\s+uint8_t\s+(PIN_[A-Z0-9_]+)\s*=\s*(\d+)\s*;")


class ConfigError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass
class PinMap:
    by_name: dict[str, tuple[int, ...]]
    di: tuple[int, ...]  # index 0 is DI1
    occupied: frozenset[int]
    free: tuple[int, ...]

    def di_index_for_pin(self, pin: int) -> int | None:
        for index, mapped in enumerate(self.di):
            if mapped == pin:
                return index
        return None


@dataclass
class LoadCell:
    id: str
    name: str
    unit: str
    tare: float
    counts_per_unit: float


@dataclass
class Pressure:
    id: str
    name: str
    zero_volts: float
    full_scale_volts: float
    full_scale_psi: float


@dataclass
class Thermo:
    id: str
    name: str
    letter: str
    code: int


@dataclass
class Page:
    name: str
    show: tuple[str, str, str]


@dataclass
class Input:
    id: str
    name: str
    action: str
    action_code: int
    active_high: bool
    valve: int
    tare_mask: int


@dataclass
class Lock:
    valve: int
    arm_input: int  # index into the DI1..DI8 table


@dataclass
class Config:
    stream_hz: int
    debounce_ms: int
    load_cells: list[LoadCell]
    pressures: list[Pressure]
    thermocouples: list[Thermo]
    pages: list[Page]
    inputs: list[Input]  # DI1..DI8
    estop_pin: int
    estop_active_high: bool
    estop_pull: str
    estop_reset_input: int
    locks: list[Lock] = field(default_factory=list)


def load_pinmap(path: Path = PINS_H) -> PinMap:
    text = path.read_text()
    found: dict[str, tuple[int, ...]] = {}
    for name, body in _ARRAY.findall(text):
        found[name] = tuple(int(part.strip()) for part in body.split(",") if part.strip())
    for name, value in _SCALAR.findall(text):
        found[name] = (int(value),)
    required = [
        "PIN_LC_SCK",
        "PIN_LC_DOUT",
        "PIN_DISP_CLK",
        "PIN_DISP_DIO",
        "PIN_TC_MOSI",
        "PIN_TC_MISO",
        "PIN_TC_SCK",
        "PIN_TC_CS",
        "PIN_PT",
        "PIN_VALVE",
        "PIN_DI",
    ]
    missing = [name for name in required if name not in found]
    if missing:
        raise ConfigError([f"{path}: could not read {', '.join(missing)}"])
    if len(found["PIN_DI"]) != 8:
        raise ConfigError([f"{path}: PIN_DI must list 8 pins"])
    occupied_list: list[int] = []
    for name in required:
        occupied_list.extend(found[name])
    occupied = frozenset(occupied_list)
    free = tuple(pin for pin in range(42) if pin not in occupied)
    return PinMap(by_name=found, di=found["PIN_DI"], occupied=occupied, free=free)


def load_yaml(path: Path):
    try:
        text = path.read_text()
    except OSError as exc:
        raise ConfigError([f"{path}: {exc}"]) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError([f"{path}: YAML syntax: {exc}"]) from exc
    if data is None:
        raise ConfigError([f"{path}: file is empty"])
    if not isinstance(data, dict):
        raise ConfigError([f"{path}: the top level must be a mapping"])
    return data


def _err(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _reject_unknown(errors: list[str], path: str, data: dict, allowed: set[str]) -> None:
    for key in data:
        if key not in allowed:
            _err(errors, path, f"unknown key '{key}'")


def _as_int(errors: list[str], path: str, value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        _err(errors, path, f"expected an integer, got {value!r}")
        return None
    return value


def _as_float(errors: list[str], path: str, value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _err(errors, path, f"expected a number, got {value!r}")
        return None
    number = float(value)
    if not math.isfinite(number):
        _err(errors, path, "expected a finite number")
        return None
    return number


def _as_name(errors: list[str], path: str, value) -> str | None:
    if not isinstance(value, str) or _NAME.match(value) is None:
        _err(
            errors,
            path,
            "expected 1-24 characters: letters, digits, space, . _ + / -",
        )
        return None
    return value


def _as_words(errors: list[str], path: str, value, allowed: set[str]) -> str | None:
    if isinstance(value, bool):
        _err(
            errors,
            path,
            "quote this value. Unquoted T, Y, N, ON, OFF, YES, and NO are "
            "booleans in YAML, not words",
        )
        return None
    if not isinstance(value, str):
        _err(errors, path, f"expected one of {sorted(allowed)}, got {value!r}")
        return None
    if value not in allowed:
        _err(errors, path, f"expected one of {sorted(allowed)}, got {value!r}")
        return None
    return value


def _mapping(errors: list[str], path: str, value) -> dict | None:
    if not isinstance(value, dict):
        _err(errors, path, "expected a mapping")
        return None
    return value


def _sequence(errors: list[str], path: str, value) -> list | None:
    if not isinstance(value, list):
        _err(errors, path, "expected a list")
        return None
    return value


def validate(data: dict, pins: PinMap, filename: str = "config.yaml") -> Config:
    errors: list[str] = []

    def err(path: str, message: str) -> None:
        _err(errors, f"{filename}: {path}", message)

    if not isinstance(data, dict):
        raise ConfigError([f"{filename}: the top level must be a mapping"])
    _reject_unknown(errors, f"{filename}", data, TOP_KEYS)

    version = _as_int(errors, f"{filename}: version", data.get("version"))
    if version is not None and version != 1:
        err("version", "only version 1 is supported")

    stream = _as_int(errors, f"{filename}: stream_hz", data.get("stream_hz"))
    if stream is not None and not 0 <= stream <= 50:
        err("stream_hz", "expected an integer from 0 to 50")

    debounce = _as_int(errors, f"{filename}: debounce_ms", data.get("debounce_ms"))
    if debounce is not None and not 1 <= debounce <= 200:
        err("debounce_ms", "expected an integer from 1 to 200")

    load_cells = _parse_load_cells(data.get("load_cells"), errors, filename)
    pressures = _parse_pressures(data.get("pressures"), errors, filename)
    thermos = _parse_thermos(data.get("thermocouples"), errors, filename)
    pages = _parse_pages(data.get("pages"), errors, filename)
    inputs = _parse_inputs(data.get("inputs"), errors, filename)
    estop = _parse_estop(data.get("estop"), inputs, pins, errors, filename)
    locks = _parse_locks(data.get("interlocks"), inputs, errors, filename)

    if (
        inputs
        and pages
        and any(item.action == "display_page" for item in inputs)
        and len(pages) < 2
    ):
        err("pages", "display_page needs at least 2 pages")

    if errors:
        raise ConfigError(errors)

    assert stream is not None and debounce is not None
    assert load_cells and pressures and thermos and pages and inputs and estop
    pin, active_high, pull, reset_index = estop
    return Config(
        stream_hz=stream,
        debounce_ms=debounce,
        load_cells=load_cells,
        pressures=pressures,
        thermocouples=thermos,
        pages=pages,
        inputs=inputs,
        estop_pin=pin,
        estop_active_high=active_high,
        estop_pull=pull,
        estop_reset_input=reset_index,
        locks=locks,
    )


def _parse_load_cells(raw, errors: list[str], filename: str) -> list[LoadCell] | None:
    items = _sequence(errors, f"{filename}: load_cells", raw)
    if items is None:
        return None
    parsed: dict[str, LoadCell] = {}
    for index, item in enumerate(items):
        path = f"{filename}: load_cells[{index}]"
        body = _mapping(errors, path, item)
        if body is None:
            continue
        _reject_unknown(errors, path, body, {"id", "name", "tare", "counts_per_unit", "unit"})
        ident = body.get("id")
        if ident not in LC_IDS:
            _err(errors, f"{path}.id", f"expected one of {list(LC_IDS)}, got {ident!r}")
            continue
        if ident in parsed:
            _err(errors, f"{path}.id", f"{ident} is listed twice")
        name = _as_name(errors, f"{path}.name", body.get("name"))
        tare = _as_float(errors, f"{path}.tare", body.get("tare"))
        scale = _as_float(errors, f"{path}.counts_per_unit", body.get("counts_per_unit"))
        unit = body.get("unit")
        if not isinstance(unit, str) or _UNIT.match(unit) is None:
            _err(errors, f"{path}.unit", "expected 1-8 characters: letters, digits, . % /")
            unit = None
        if scale == 0:
            _err(errors, f"{path}.counts_per_unit", "must not be zero")
        if None in (name, tare, scale, unit) or scale == 0:
            continue
        parsed[ident] = LoadCell(ident, name, unit, tare, scale)
    missing = [ident for ident in LC_IDS if ident not in parsed]
    if missing:
        _err(errors, f"{filename}: load_cells", f"missing {', '.join(missing)}")
        return None
    return [parsed[ident] for ident in LC_IDS]


def _parse_pressures(raw, errors: list[str], filename: str) -> list[Pressure] | None:
    items = _sequence(errors, f"{filename}: pressures", raw)
    if items is None:
        return None
    parsed: dict[str, Pressure] = {}
    for index, item in enumerate(items):
        path = f"{filename}: pressures[{index}]"
        body = _mapping(errors, path, item)
        if body is None:
            continue
        _reject_unknown(
            errors,
            path,
            body,
            {"id", "name", "zero_volts", "full_scale_volts", "full_scale_psi"},
        )
        ident = body.get("id")
        if ident not in PT_IDS:
            _err(errors, f"{path}.id", f"expected one of {list(PT_IDS)}, got {ident!r}")
            continue
        if ident in parsed:
            _err(errors, f"{path}.id", f"{ident} is listed twice")
        name = _as_name(errors, f"{path}.name", body.get("name"))
        zero_v = _as_float(errors, f"{path}.zero_volts", body.get("zero_volts"))
        full_v = _as_float(errors, f"{path}.full_scale_volts", body.get("full_scale_volts"))
        full_psi = _as_float(errors, f"{path}.full_scale_psi", body.get("full_scale_psi"))
        if zero_v is not None and full_v is not None and zero_v == full_v:
            _err(errors, f"{path}.full_scale_volts", "span is zero; it must differ from zero_volts")
        if None in (name, zero_v, full_v, full_psi) or zero_v == full_v:
            continue
        parsed[ident] = Pressure(ident, name, zero_v, full_v, full_psi)
    missing = [ident for ident in PT_IDS if ident not in parsed]
    if missing:
        _err(errors, f"{filename}: pressures", f"missing {', '.join(missing)}")
        return None
    return [parsed[ident] for ident in PT_IDS]


def _parse_thermos(raw, errors: list[str], filename: str) -> list[Thermo] | None:
    items = _sequence(errors, f"{filename}: thermocouples", raw)
    if items is None:
        return None
    parsed: dict[str, Thermo] = {}
    for index, item in enumerate(items):
        path = f"{filename}: thermocouples[{index}]"
        body = _mapping(errors, path, item)
        if body is None:
            continue
        _reject_unknown(errors, path, body, {"id", "name", "type"})
        ident = body.get("id")
        if ident not in TC_IDS:
            _err(errors, f"{path}.id", f"expected one of {list(TC_IDS)}, got {ident!r}")
            continue
        if ident in parsed:
            _err(errors, f"{path}.id", f"{ident} is listed twice")
        name = _as_name(errors, f"{path}.name", body.get("name"))
        letter = _as_words(errors, f"{path}.type", body.get("type"), set(TC_TYPES))
        if name is None or letter is None:
            continue
        parsed[ident] = Thermo(ident, name, letter, TC_TYPES[letter])
    missing = [ident for ident in TC_IDS if ident not in parsed]
    if missing:
        _err(errors, f"{filename}: thermocouples", f"missing {', '.join(missing)}")
        return None
    return [parsed[ident] for ident in TC_IDS]


def _parse_pages(raw, errors: list[str], filename: str) -> list[Page] | None:
    items = _sequence(errors, f"{filename}: pages", raw)
    if items is None:
        return None
    if len(items) < 1 or len(items) > 12:
        _err(errors, f"{filename}: pages", "expected 1 to 12 pages")
    pages: list[Page] = []
    for index, item in enumerate(items):
        path = f"{filename}: pages[{index}]"
        body = _mapping(errors, path, item)
        if body is None:
            continue
        _reject_unknown(errors, path, body, {"name", "show"})
        name = _as_name(errors, f"{path}.name", body.get("name"))
        show = _sequence(errors, f"{path}.show", body.get("show"))
        if show is None or name is None:
            continue
        if len(show) != 3:
            _err(errors, f"{path}.show", "expected exactly 3 channels, one per display")
            continue
        channels: list[str] = []
        bad = False
        for slot, channel in enumerate(show):
            if channel not in CHANNEL_IDS:
                _err(
                    errors,
                    f"{path}.show[{slot}]",
                    f"unknown channel {channel!r}. Use one of {list(CHANNEL_IDS)}",
                )
                bad = True
            else:
                channels.append(channel)
        if bad:
            continue
        pages.append(Page(name, (channels[0], channels[1], channels[2])))
    if not pages:
        return None
    return pages


def _parse_inputs(raw, errors: list[str], filename: str) -> list[Input] | None:
    items = _sequence(errors, f"{filename}: inputs", raw)
    if items is None:
        return None
    parsed: dict[str, Input] = {}
    claimed_valves: dict[int, str] = {}
    for index, item in enumerate(items):
        path = f"{filename}: inputs[{index}]"
        body = _mapping(errors, path, item)
        if body is None:
            continue
        action = _as_words(errors, f"{path}.action", body.get("action"), set(ACTIONS))
        allowed = {"id", "name", "action", "active"}
        if action in ("toggle_valve", "momentary_valve"):
            allowed.add("valve")
        elif action == "tare":
            allowed.add("channels")
        _reject_unknown(errors, path, body, allowed)
        ident = body.get("id")
        if ident not in DI_IDS:
            _err(errors, f"{path}.id", f"expected one of {list(DI_IDS)}, got {ident!r}")
            continue
        if ident in parsed:
            _err(errors, f"{path}.id", f"{ident} is listed twice")
        name = _as_name(errors, f"{path}.name", body.get("name"))
        active = _as_words(errors, f"{path}.active", body.get("active"), {"high", "low"})
        if action is None or name is None or active is None:
            continue
        valve = 0
        mask = 0
        if action in ("toggle_valve", "momentary_valve"):
            valve_number = _as_int(errors, f"{path}.valve", body.get("valve"))
            if valve_number is None:
                continue
            if not 1 <= valve_number <= 7:
                _err(errors, f"{path}.valve", "expected a valve from 1 to 7")
                continue
            if valve_number in claimed_valves:
                _err(
                    errors,
                    f"{path}.valve",
                    f"valve {valve_number} is already commanded by {claimed_valves[valve_number]}",
                )
            claimed_valves[valve_number] = ident
            valve = valve_number
        elif action == "tare":
            channels = _sequence(errors, f"{path}.channels", body.get("channels"))
            if channels is None:
                continue
            if not channels:
                _err(errors, f"{path}.channels", "list at least one of LC1, LC2, LC3")
                continue
            seen: set[str] = set()
            bad = False
            for slot, channel in enumerate(channels):
                if channel not in LC_IDS:
                    _err(errors, f"{path}.channels[{slot}]", f"expected a load cell, got {channel!r}")
                    bad = True
                    continue
                if channel in seen:
                    _err(errors, f"{path}.channels[{slot}]", f"{channel} is listed twice")
                    bad = True
                seen.add(channel)
                mask |= 1 << LC_IDS.index(channel)
            if bad or mask == 0:
                continue
        elif "valve" in body or "channels" in body:
            _err(errors, path, f"action {action} does not take valve or channels")
            continue
        parsed[ident] = Input(
            id=ident,
            name=name,
            action=action,
            action_code=ACTIONS[action],
            active_high=active == "high",
            valve=valve,
            tare_mask=mask,
        )
    resets = [item.id for item in parsed.values() if item.action == "reset"]
    if len(resets) == 0:
        _err(errors, f"{filename}: inputs", "one input with action reset is required")
    elif len(resets) > 1:
        _err(errors, f"{filename}: inputs", f"only one reset input is allowed ({' and '.join(resets)})")
    missing = [ident for ident in DI_IDS if ident not in parsed]
    if missing:
        _err(
            errors,
            f"{filename}: inputs",
            "each of DI1..DI8 is required once. Use action: none for a header "
            f"you are not using. Missing {', '.join(missing)}",
        )
        return None
    return [parsed[ident] for ident in DI_IDS]


def _parse_estop(raw, inputs: list[Input] | None, pins: PinMap, errors: list[str], filename: str):
    path = f"{filename}: estop"
    body = _mapping(errors, path, raw)
    if body is None or inputs is None:
        return None
    _reject_unknown(errors, path, body, {"pin", "active", "pull", "reset"})
    pin = _as_int(errors, f"{path}.pin", body.get("pin"))
    active = _as_words(errors, f"{path}.active", body.get("active"), {"high", "low"})
    pull = _as_words(errors, f"{path}.pull", body.get("pull"), set(PULLS))
    reset_id = body.get("reset")
    if not isinstance(reset_id, str) or reset_id not in DI_IDS:
        _err(errors, f"{path}.reset", f"expected one of {list(DI_IDS)}, got {reset_id!r}")
        reset_index = None
    else:
        reset_index = DI_IDS.index(reset_id)
        if inputs[reset_index].action != "reset":
            _err(
                errors,
                f"{path}.reset",
                f"{reset_id} action is {inputs[reset_index].action}, expected reset",
            )
    if pin is None or active is None or pull is None or reset_index is None:
        return None
    if not 0 <= pin <= 41:
        _err(errors, f"{path}.pin", "Teensy 4.1 GPIO pins are 0 through 41")
        return None
    free_text = ", ".join(str(number) for number in pins.free)
    di_index = pins.di_index_for_pin(pin)
    if pin in pins.occupied and di_index is None:
        _err(
            errors,
            f"{path}.pin",
            f"pin {pin} is already used by a sensor, display, or valve. "
            f"Free GPIOs: {free_text}. A digital-input header can be used only "
            "when that input's action is none.",
        )
        return None
    if di_index is not None:
        owner = inputs[di_index]
        if owner.action != "none":
            _err(
                errors,
                f"{path}.pin",
                f"pin {pin} is {owner.id}, and {owner.id} action is {owner.action}. "
                "Set that input to action: none, or choose a free GPIO "
                f"({free_text}).",
            )
        if pull != "none":
            _err(
                errors,
                f"{path}.pull",
                "that header already has a 10k pulldown on the board. Use pull: none "
                "so the firmware does not fight it.",
            )
        if reset_index == di_index:
            _err(errors, f"{path}.reset", "the reset button cannot be the same pin as the sense line")
    elif pull == "none":
        _err(
            errors,
            f"{path}.pull",
            "a free GPIO needs pull: down or pull: up, or the sense line floats. "
            "pull: down and active: low is the fail-safe wiring "
            "(normally-closed switch to +3V3).",
        )
    if any(item.startswith(f"{filename}: estop") for item in errors):
        return None
    return pin, active == "high", pull, reset_index


def _parse_locks(raw, inputs: list[Input] | None, errors: list[str], filename: str) -> list[Lock]:
    if raw is None:
        _err(errors, f"{filename}: interlocks", "expected a list (it may be empty)")
        return []
    items = _sequence(errors, f"{filename}: interlocks", raw)
    if items is None or inputs is None:
        return []
    locks: list[Lock] = []
    seen: set[int] = set()
    for index, item in enumerate(items):
        path = f"{filename}: interlocks[{index}]"
        body = _mapping(errors, path, item)
        if body is None:
            continue
        _reject_unknown(errors, path, body, {"valve", "requires"})
        valve = _as_int(errors, f"{path}.valve", body.get("valve"))
        requires = body.get("requires")
        if valve is None:
            continue
        if not 1 <= valve <= 7:
            _err(errors, f"{path}.valve", "expected a valve from 1 to 7")
            continue
        if valve in seen:
            _err(errors, f"{path}.valve", f"valve {valve} is listed twice")
        seen.add(valve)
        if not isinstance(requires, str) or requires not in DI_IDS:
            _err(errors, f"{path}.requires", f"expected one of {list(DI_IDS)}, got {requires!r}")
            continue
        arm_index = DI_IDS.index(requires)
        if inputs[arm_index].action != "arm":
            _err(
                errors,
                f"{path}.requires",
                f"{requires} action is {inputs[arm_index].action}, expected arm",
            )
            continue
        locks.append(Lock(valve, arm_index))
    return locks


def _c_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _c_float(value: float) -> str:
    rendered = f"{value:.8f}".rstrip("0").rstrip(".")
    if "." not in rendered and "e" not in rendered:
        rendered += ".0"
    return rendered + "f"


def render(config: Config) -> str:
    channel_index = {ident: index for index, ident in enumerate(CHANNEL_IDS)}
    lines: list[str] = [
        "#pragma once",
        "",
        "#include <stdint.h>",
        "",
        "// Generated from config.yaml by scripts/gen_config.py. Do not edit.",
        f"// E-stop sense: Teensy pin {config.estop_pin}, "
        f"active {'high' if config.estop_active_high else 'low'}, "
        f"pull {config.estop_pull}.",
        f"// Reset input: {DI_IDS[config.estop_reset_input]}, "
        "accepted only after the sense line is released.",
        "",
        "enum CfgAction : uint8_t {",
        "    CFG_NONE = 0,",
        "    CFG_ARM = 1,",
        "    CFG_RESET = 2,",
        "    CFG_TOGGLE = 3,",
        "    CFG_MOMENTARY = 4,",
        "    CFG_TARE = 5,",
        "    CFG_PAGE = 6",
        "};",
        "",
        "enum CfgPull : uint8_t {",
        "    CFG_PULL_NONE = 0,",
        "    CFG_PULL_DOWN = 1,",
        "    CFG_PULL_UP = 2",
        "};",
        "",
        "struct CfgLoadCell {",
        "    const char* id;",
        "    const char* name;",
        "    const char* unit;",
        "    float tare;",
        "    float countsPerUnit;",
        "};",
        "",
        "struct CfgPressure {",
        "    const char* id;",
        "    const char* name;",
        "    float zeroVolts;",
        "    float fullScaleVolts;",
        "    float fullScalePsi;",
        "};",
        "",
        "struct CfgThermo {",
        "    const char* id;",
        "    const char* name;",
        "    uint8_t typeCode;",
        "    char typeLetter;",
        "};",
        "",
        "struct CfgPage {",
        "    const char* name;",
        "    uint8_t show[3];",
        "};",
        "",
        "struct CfgInput {",
        "    uint8_t di;",
        "    uint8_t activeHigh;",
        "    CfgAction action;",
        "    uint8_t valve;",
        "    uint8_t tareMask;",
        "    const char* name;",
        "};",
        "",
        "struct CfgLock {",
        "    uint8_t valve;",
        "    uint8_t armInput;",
        "};",
        "",
        f"static constexpr uint16_t CFG_STREAM_HZ = {config.stream_hz};",
        f"static constexpr uint16_t CFG_DEBOUNCE_MS = {config.debounce_ms};",
        f"static constexpr uint8_t CFG_ESTOP_PIN = {config.estop_pin};",
        f"static constexpr uint8_t CFG_ESTOP_ACTIVE_HIGH = {1 if config.estop_active_high else 0};",
        f"static constexpr CfgPull CFG_ESTOP_PULL = CFG_PULL_{config.estop_pull.upper()};",
        f"static constexpr uint8_t CFG_ESTOP_RESET_INPUT = {config.estop_reset_input};",
        f"static constexpr char CFG_CSV_HEADER[] = {_c_string(','.join(CSV_COLUMNS))};",
        "",
        "static constexpr CfgLoadCell CFG_LC[] = {",
    ]
    for cell in config.load_cells:
        lines.append(
            "    {"
            f"{_c_string(cell.id)}, {_c_string(cell.name)}, {_c_string(cell.unit)}, "
            f"{_c_float(cell.tare)}, {_c_float(cell.counts_per_unit)}"
            "},"
        )
    lines += [
        "};",
        "",
        "static constexpr CfgPressure CFG_PT[] = {",
    ]
    for channel in config.pressures:
        lines.append(
            "    {"
            f"{_c_string(channel.id)}, {_c_string(channel.name)}, "
            f"{_c_float(channel.zero_volts)}, {_c_float(channel.full_scale_volts)}, "
            f"{_c_float(channel.full_scale_psi)}"
            "},"
        )
    lines += [
        "};",
        "",
        "static constexpr CfgThermo CFG_TC[] = {",
    ]
    for channel in config.thermocouples:
        lines.append(
            "    {"
            f"{_c_string(channel.id)}, {_c_string(channel.name)}, "
            f"{channel.code}, '{channel.letter}'"
            "},"
        )
    lines += [
        "};",
        "",
        f"static constexpr uint8_t CFG_N_PAGES = {len(config.pages)};",
        "static constexpr CfgPage CFG_PAGES[] = {",
    ]
    for page in config.pages:
        shows = ", ".join(str(channel_index[ident]) for ident in page.show)
        lines.append(f"    {{{_c_string(page.name)}, {{{shows}}}}},")
    lines += [
        "};",
        "",
        "static constexpr CfgInput CFG_INPUTS[] = {",
    ]
    for index, item in enumerate(config.inputs):
        lines.append(
            "    {"
            f"{index + 1}, {1 if item.active_high else 0}, "
            f"static_cast<CfgAction>({item.action_code}), "
            f"{item.valve}, {item.tare_mask}, {_c_string(item.name)}"
            "},"
        )
    lines += [
        "};",
        "static constexpr uint8_t CFG_N_INPUTS = 8;",
        "",
    ]
    if config.locks:
        lines.append(f"static constexpr uint8_t CFG_N_LOCKS = {len(config.locks)};")
        lines.append(f"static constexpr CfgLock CFG_LOCKS[{len(config.locks)}] = {{")
        for lock in config.locks:
            lines.append(f"    {{{lock.valve}, {lock.arm_input}}},")
        lines.append("};")
    else:
        lines += [
            "static constexpr uint8_t CFG_N_LOCKS = 0;",
            "static constexpr CfgLock CFG_LOCKS[1] = {{0, 0}};",
        ]
    lines += [
        "",
        "static_assert(CFG_N_PAGES >= 1, \"config needs a display page\");",
        "static_assert(CFG_N_INPUTS == 8, \"eight panel inputs\");",
    ]
    for index in range(8):
        lines.append(
            f"static_assert(CFG_INPUTS[{index}].di == {index + 1}, \"DI{index + 1} order\");"
        )
    lines.append("")
    return "\n".join(lines)


def generate(src: Path, dst: Path) -> str:
    pins = load_pinmap()
    config = validate(load_yaml(src), pins, filename=src.name)
    text = render(config)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return text
