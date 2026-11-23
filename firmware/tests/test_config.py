import copy
from pathlib import Path

import pytest

import configtool
from configtool import ConfigError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config.yaml"
MAIN = ROOT / "src" / "main.cpp"


@pytest.fixture
def pins():
    return configtool.load_pinmap()


@pytest.fixture
def example():
    return configtool.load_yaml(EXAMPLE)


def _validate(data, pins):
    return configtool.validate(copy.deepcopy(data), pins)


def test_schematic_pin_map(pins):
    assert pins.di == (38, 37, 36, 35, 34, 33, 31, 32)
    assert pins.by_name["PIN_LC_DOUT"] == (3, 0, 1)
    assert pins.by_name["PIN_LC_SCK"] == (2,)
    assert pins.by_name["PIN_DISP_CLK"] == (4, 6, 8)
    assert pins.by_name["PIN_DISP_DIO"] == (5, 7, 9)
    assert pins.by_name["PIN_TC_CS"] == (23, 22, 21)
    assert pins.by_name["PIN_TC_MOSI"] == (11,)
    assert pins.by_name["PIN_TC_MISO"] == (12,)
    assert pins.by_name["PIN_TC_SCK"] == (13,)
    assert pins.by_name["PIN_PT"] == (20, 19, 18, 17, 16, 15)
    assert pins.by_name["PIN_VALVE"] == (24, 25, 26, 27, 28, 29, 30)
    assert pins.free == (10, 14, 39, 40, 41)


def test_example_is_the_fail_safe_panel(example, pins):
    config = _validate(example, pins)
    assert config.estop_pin == 10
    assert config.estop_active_high is False
    assert config.estop_pull == "down"
    assert config.inputs[config.estop_reset_input].id == "DI7"
    assert config.inputs[config.estop_reset_input].action == "reset"
    assert [lock.valve for lock in config.locks] == [1, 2, 3, 4, 5, 6, 7]
    assert config.thermocouples[0].letter == "T"
    assert config.load_cells[0].slope == 1
    assert config.load_cells[0].offset == 0
    assert config.pressures[0].slope == 25
    assert config.pressures[0].offset == -12.5
    assert config.thermocouples[0].slope == 1
    assert config.thermocouples[0].offset == 0


def test_example_header_carries_the_estop_and_the_csv(example, pins, tmp_path):
    text = configtool.render(_validate(example, pins))
    destination = tmp_path / "config_gen.h"
    destination.write_text(text)
    assert "CFG_ESTOP_PIN = 10" in text
    assert "CFG_ESTOP_ACTIVE_HIGH = 0" in text
    assert "CFG_PULL_DOWN" in text
    assert "estop_sense,estop_latch,page" in text
    assert "Specimen 1" in text
    assert destination.read_text() == text


def test_firmware_csv_column_comment_matches_the_generator():
    source = MAIN.read_text()
    marker = "csv columns: "
    line = next(item for item in source.splitlines() if marker in item)
    columns = line.split(marker, 1)[1].strip()
    assert columns == ",".join(configtool.CSV_COLUMNS)
    assert columns.endswith("estop_sense,estop_latch,page")


def test_estop_pin_cannot_be_a_valve(example, pins):
    example["estop"]["pin"] = 24
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "pin 24" in str(caught.value)
    assert "10, 14, 39, 40, 41" in str(caught.value)


def test_estop_can_take_a_spare_input_header(example, pins):
    example["inputs"][7]["action"] = "none"
    del example["inputs"][7]["valve"]
    example["estop"]["pin"] = 32  # DI8
    example["estop"]["pull"] = "none"
    config = _validate(example, pins)
    assert config.estop_pin == 32
    assert config.estop_pull == "none"


def test_estop_rejects_a_header_that_already_has_an_action(example, pins):
    example["estop"]["pin"] = 38  # DI1, the arm switch
    example["estop"]["pull"] = "none"
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "DI1" in str(caught.value)


def test_free_pin_must_not_float(example, pins):
    example["estop"]["pull"] = "none"
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "floats" in str(caught.value)


def test_header_pulldown_is_not_fought(example, pins):
    example["inputs"][7]["action"] = "none"
    del example["inputs"][7]["valve"]
    example["estop"]["pin"] = 32
    example["estop"]["pull"] = "up"
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "10k pulldown" in str(caught.value)


def test_boolean_thermocouple_type_is_rejected(example, pins):
    # Bare "yes" is a YAML boolean. The validator has to say so, not just
    # "expected one of B, E, J...".
    example["thermocouples"][0]["type"] = True
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "quote" in str(caught.value)


def test_zero_slope_is_rejected(example, pins):
    example["load_cells"][0]["slope"] = 0
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "must not be zero" in str(caught.value)


def test_legacy_scale_keys_are_rejected(example, pins):
    example["load_cells"][0]["counts_per_unit"] = 280
    example["pressures"][0]["zero_volts"] = 0.5
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    message = str(caught.value)
    assert "counts_per_unit" in message
    assert "slope" in message
    assert "zero_volts" in message


def test_point_table_rejects_a_repeated_raw(example, pins):
    example["pressures"][0]["points"] = [[0.5, 0], [0.5, 10]]
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "strictly increasing" in str(caught.value)


def test_point_table_values_must_not_fold(example, pins):
    example["pressures"][0]["points"] = [[0.5, 0], [2.5, 80], [4.5, 70]]
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "strictly monotonic" in str(caught.value)


def test_point_table_is_accepted_and_sorted(example, pins):
    example["pressures"][0]["points"] = [[4.5, 100], [0.5, 0]]
    config = _validate(example, pins)
    assert config.pressures[0].points == ((0.5, 0.0), (4.5, 100.0))


def test_missing_reset_and_duplicate_input(example, pins):
    example["inputs"][6]["action"] = "none"
    example["inputs"][1]["id"] = "DI1"
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    message = str(caught.value)
    assert "reset" in message
    assert "listed twice" in message


def test_interlock_must_name_an_arm_switch(example, pins):
    example["interlocks"][0]["requires"] = "DI2"
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "expected arm" in str(caught.value)


def test_display_page_needs_two_pages(example, pins):
    example["pages"] = [example["pages"][0]]
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "at least 2" in str(caught.value)


def test_unknown_key_and_bad_valve(example, pins):
    example["inputs"][1]["colour"] = "red"
    example["inputs"][2]["valve"] = 8
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    message = str(caught.value)
    assert "unknown key" in message
    assert "1 to 7" in message


def test_two_buttons_cannot_command_one_valve(example, pins):
    example["inputs"][2]["valve"] = 1
    with pytest.raises(ConfigError) as caught:
        _validate(example, pins)
    assert "already commanded" in str(caught.value)


def test_yaml_syntax_error(tmp_path, pins):
    path = tmp_path / "config.yaml"
    path.write_text("version: [\n")
    with pytest.raises(ConfigError) as caught:
        configtool.load_yaml(path)
    assert "YAML syntax" in str(caught.value)
    del pins
