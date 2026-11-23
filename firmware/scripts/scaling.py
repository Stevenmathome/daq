"""One calibration line for every analog channel.

    value = slope * raw + offset

raw depends on the channel, and the firmware uses that same raw:

  load cell     HX711 counts
  pressure      sensor volts, before the 10k/20k divider
  thermocouple  MAX31856 temperature in degC (a correction on top of the chip)

A point table, when it has at least two points, replaces the line.
The table is piecewise linear. Past either end, the end segment is extended.

The tare button is not part of the line. It subtracts the live value until
reboot: reading = calibrated(raw) - tare.

EEPROM stores slope, offset, and points per channel. A saved channel
overrides the config.yaml line at boot. Tare is never stored.

src/scale.h is the same arithmetic. Change both together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ADC_VREF = 3.3
ADC_MAX_COUNT = 4095
DIVIDER = 1.5  # (10k + 20k) / 20k
MAX_POINTS = 8


class CalError(Exception):
    pass


def pin_volts(counts: int) -> float:
    return (counts / ADC_MAX_COUNT) * ADC_VREF


def sensor_volts(counts: int) -> float:
    return pin_volts(counts) * DIVIDER


def line_from_two_points(raw0: float, value0: float, raw1: float, value1: float) -> tuple[float, float]:
    """slope, offset for the line through two (raw, value) points.

    A 0.5-4.5 V, 0-100 PSI sensor is line_from_two_points(0.5, 0, 4.5, 100),
    which is slope 25 and offset -12.5.
    """
    span = raw1 - raw0
    if span == 0:
        raise CalError("the two raw readings are equal")
    slope = (value1 - value0) / span
    offset = value0 - slope * raw0
    return slope, offset


def apply_linear(raw: float, slope: float, offset: float) -> float:
    return slope * raw + offset


def piecewise(raw: float, points: tuple[tuple[float, float], ...]) -> float:
    if len(points) < 2:
        raise CalError("a point table needs at least 2 points")
    if raw <= points[0][0]:
        return _lerp(raw, points[0], points[1])
    if raw >= points[-1][0]:
        return _lerp(raw, points[-2], points[-1])
    for index in range(1, len(points)):
        if raw <= points[index][0]:
            return _lerp(raw, points[index - 1], points[index])
    return points[-1][1]


def _lerp(raw: float, left: tuple[float, float], right: tuple[float, float]) -> float:
    span = right[0] - left[0]
    if span == 0:
        return left[1]
    return left[1] + (raw - left[0]) / span * (right[1] - left[1])


def normalize_points(points: list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    ordered = sorted(points, key=lambda point: point[0])
    if len(ordered) < 2:
        raise CalError("a point table needs at least 2 points")
    if len(ordered) > MAX_POINTS:
        raise CalError(f"a point table can hold at most {MAX_POINTS} points")
    for index in range(1, len(ordered)):
        if ordered[index][0] <= ordered[index - 1][0]:
            raise CalError("raw values must be strictly increasing")
    rising = all(ordered[index][1] > ordered[index - 1][1] for index in range(1, len(ordered)))
    falling = all(ordered[index][1] < ordered[index - 1][1] for index in range(1, len(ordered)))
    if not rising and not falling:
        raise CalError("values must be strictly monotonic")
    return tuple(ordered)


@dataclass
class Fit:
    slope: float
    offset: float
    points: tuple[tuple[float, float], ...] = ()
    tare: float = 0.0
    # zero_raw is the raw captured by CAL ZERO. None means "use -offset/slope".
    zero_raw: float | None = None


def calibrated(raw: float, fit: Fit) -> float:
    if len(fit.points) >= 2:
        base = piecewise(raw, fit.points)
    else:
        base = apply_linear(raw, fit.slope, fit.offset)
    return base - fit.tare


def capture_tare(fit: Fit, raw: float) -> Fit:
    """Runtime tare. The stored line is unchanged; the live value becomes zero."""
    base = calibrated(raw, Fit(fit.slope, fit.offset, fit.points, 0.0, fit.zero_raw))
    return Fit(fit.slope, fit.offset, fit.points, base, fit.zero_raw)


def cal_zero(fit: Fit, raw: float) -> Fit:
    if fit.slope == 0:
        raise CalError("slope is zero")
    # Keep the slope, move the line so this raw reads 0, and drop any point table.
    return Fit(fit.slope, -fit.slope * raw, (), fit.tare, raw)


def cal_span(fit: Fit, raw: float, known: float) -> Fit:
    if known == 0:
        raise CalError("span value must not be zero")
    if fit.slope == 0 and fit.zero_raw is None:
        raise CalError("slope is zero")
    zero_raw = fit.zero_raw if fit.zero_raw is not None else -fit.offset / fit.slope
    if raw == zero_raw:
        raise CalError("span raw equals the zero raw")
    slope = known / (raw - zero_raw)
    return Fit(slope, -slope * zero_raw, (), fit.tare, zero_raw)


def cal_point(fit: Fit, raw: float, known: float) -> Fit:
    draft = list(fit.points) + [(raw, known)]
    if len(draft) > MAX_POINTS:
        raise CalError(f"a point table can hold at most {MAX_POINTS} points")
    if len(draft) == 1:
        points: tuple[tuple[float, float], ...] = ((raw, known),)
    else:
        points = normalize_points(draft)
    return Fit(fit.slope, fit.offset, points, fit.tare, fit.zero_raw)


@dataclass
class StoredCal:
    """One channel as config.yaml or EEPROM would hand it over. No runtime tare."""

    slope: float
    offset: float
    points: tuple[tuple[float, float], ...] = field(default_factory=tuple)
    overrides: bool = False


def resolve_cal(config: StoredCal, eeprom: StoredCal | None) -> tuple[StoredCal, str]:
    """EEPROM wins per channel when that channel was saved. Otherwise the file."""
    if eeprom is not None and eeprom.overrides:
        return eeprom, "eeprom"
    return config, "config"


def source_name(from_eeprom: bool, dirty: bool) -> str:
    if dirty:
        return "session"
    if from_eeprom:
        return "eeprom"
    return "config"


def will_save(from_eeprom: bool, dirty: bool) -> bool:
    """CAL SAVE writes a channel when this session changed it or EEPROM already had it."""
    return from_eeprom or dirty


def format_show(channel_id: str, name: str, unit: str, fit: Fit, source: str, tc_type: str | None = None) -> str:
    """YAML a person can paste over one list item in config.yaml."""
    lines = [f"# {channel_id} source={source}"]
    lines.append(f"- id: {channel_id}")
    lines.append(f"  name: {_quote(name)}")
    if tc_type is not None:
        lines.append(f"  type: {_quote(tc_type)}")
    lines.append(f"  slope: {_num(fit.slope)}")
    lines.append(f"  offset: {_num(fit.offset)}")
    lines.append(f"  unit: {_quote(unit)}")
    if fit.points:
        lines.append("  points:")
        for raw, value in fit.points:
            lines.append(f"    - [{_num(raw)}, {_num(value)}]")
    return "\n".join(lines)


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _num(value: float) -> str:
    return f"{value:.8g}"
