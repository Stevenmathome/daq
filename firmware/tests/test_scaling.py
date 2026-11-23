import pytest

from scaling import (
    Fit,
    StoredCal,
    apply_linear,
    cal_point,
    cal_span,
    cal_zero,
    calibrated,
    capture_tare,
    format_show,
    line_from_two_points,
    normalize_points,
    piecewise,
    resolve_cal,
    sensor_volts,
    source_name,
    will_save,
    CalError,
)


def test_datasheet_pressure_line():
    slope, offset = line_from_two_points(0.5, 0, 4.5, 100)
    assert slope == pytest.approx(25)
    assert offset == pytest.approx(-12.5)
    assert apply_linear(0.5, slope, offset) == pytest.approx(0)
    assert apply_linear(4.5, slope, offset) == pytest.approx(100)
    # ADC code 2730 is 3.3 V at the sensor. Same 70 PSI as the old span formula.
    assert sensor_volts(2730) == pytest.approx(3.3)
    assert apply_linear(sensor_volts(2730), slope, offset) == pytest.approx(70)


def test_known_weight_matches_counts_over_factor():
    # Unloaded 100000 counts, 128000 counts at 100 lbf.
    # Old form: (raw - 100000) / 280.
    slope, offset = line_from_two_points(100000, 0, 128000, 100)
    assert apply_linear(128000, slope, offset) == pytest.approx(100)
    assert apply_linear(100000, slope, offset) == pytest.approx(0)
    assert apply_linear(114000, slope, offset) == pytest.approx(50)
    flipped = line_from_two_points(128000, 0, 100000, 100)
    assert flipped[0] < 0
    assert apply_linear(100000, *flipped) == pytest.approx(100)


def test_piecewise_interpolates_and_extends_the_end_segment():
    points = ((0.5, 0.0), (2.5, 50.0), (4.5, 100.0))
    assert piecewise(2.5, points) == pytest.approx(50)
    assert piecewise(1.5, points) == pytest.approx(25)
    assert piecewise(3.3, points) == pytest.approx(70)
    assert piecewise(0.0, points) == pytest.approx(-12.5)
    assert piecewise(5.0, points) == pytest.approx(112.5)


def test_point_table_rejects_a_fold_and_a_repeated_raw():
    with pytest.raises(CalError, match="monotonic"):
        normalize_points([(0.5, 0), (2.5, 80), (4.5, 70)])
    with pytest.raises(CalError, match="increasing"):
        normalize_points([(1, 0), (1, 10)])


def test_zero_then_span_builds_the_line_and_drops_points():
    fit = Fit(1, 0, ((0, 0), (10, 10)))
    fit = cal_zero(fit, 100000)
    assert calibrated(100000, fit) == pytest.approx(0)
    assert fit.points == ()
    fit = cal_span(fit, 128000, 100)
    assert calibrated(100000, fit) == pytest.approx(0)
    assert calibrated(128000, fit) == pytest.approx(100)
    assert calibrated(114000, fit) == pytest.approx(50)


def test_span_without_zero_uses_the_current_line():
    slope, offset = line_from_two_points(0.5, 0, 4.5, 100)
    fit = cal_span(Fit(slope, offset), 4.7, 110)
    # Zero stays at 0.5 V. 4.7 V is now 110 PSI.
    assert calibrated(0.5, fit) == pytest.approx(0)
    assert calibrated(4.7, fit) == pytest.approx(110)


def test_span_rejects_a_zero_value_and_a_repeated_raw():
    fit = cal_zero(Fit(1, 0), 10)
    with pytest.raises(CalError):
        cal_span(fit, 20, 0)
    with pytest.raises(CalError):
        cal_span(fit, 10, 50)


def test_points_override_the_line_once_two_exist():
    fit = Fit(25, -12.5)
    fit = cal_point(fit, 0.5, 0)
    assert fit.points == ((0.5, 0),)
    assert calibrated(3.3, fit) == pytest.approx(70)  # still the line
    fit = cal_point(fit, 4.5, 100)
    assert calibrated(2.5, fit) == pytest.approx(50)
    with pytest.raises(CalError, match="monotonic"):
        cal_point(fit, 2.5, 120)


def test_tare_is_runtime_and_does_not_change_the_line():
    fit = Fit(*line_from_two_points(100000, 0, 128000, 100))
    tared = capture_tare(fit, 114000)
    assert tared.slope == pytest.approx(fit.slope)
    assert tared.offset == pytest.approx(fit.offset)
    assert calibrated(114000, tared) == pytest.approx(0)
    assert calibrated(128000, tared) == pytest.approx(50)
    # A second tare, still at the same raw, stays at zero.
    again = capture_tare(tared, 114000)
    assert calibrated(114000, again) == pytest.approx(0)


def test_eeprom_overrides_config_per_channel():
    config = StoredCal(1, 0)
    saved = StoredCal(25, -12.5, (), True)
    chosen, source = resolve_cal(config, saved)
    assert source == "eeprom"
    assert calibrated(4.5, Fit(chosen.slope, chosen.offset)) == pytest.approx(100)
    untouched, source = resolve_cal(config, StoredCal(99, 0, (), False))
    assert source == "config"
    assert untouched.slope == 1
    absent, source = resolve_cal(config, None)
    assert source == "config"


def test_save_and_source_names():
    assert source_name(False, False) == "config"
    assert source_name(True, False) == "eeprom"
    assert source_name(True, True) == "session"
    assert will_save(False, False) is False
    assert will_save(False, True) is True
    assert will_save(True, False) is True


def test_show_yaml_is_ready_to_paste():
    fit = Fit(25, -12.5, ((0.5, 0), (4.5, 100)))
    text = format_show("PT1", "Pressure 1", "psi", fit, "eeprom")
    assert "# PT1 source=eeprom" in text
    assert 'name: "Pressure 1"' in text
    assert "slope: 25" in text
    assert "offset: -12.5" in text
    assert "unit: \"psi\"" in text
    assert "- [0.5, 0]" in text
    assert "- [4.5, 100]" in text
    tc = format_show("TC1", "Temp 1", "C", Fit(1, 0), "config", tc_type="T")
    assert 'type: "T"' in tc
