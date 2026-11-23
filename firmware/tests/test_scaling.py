import pytest

from scaling import load_eu, pin_volts, pressure_psi, sensor_volts


def test_divider_and_reference_at_the_worked_example():
    # 2730 / 4095 * 3.3 = 2.2 V at the pin, times 1.5 = 3.3 V at the sensor.
    assert pin_volts(2730) == pytest.approx(2.2)
    assert sensor_volts(2730) == pytest.approx(3.3)


def test_default_pressure_channel_reads_70_psi_at_2730_counts():
    assert pressure_psi(2730, 0.5, 4.5, 100) == pytest.approx(70)


def test_pressure_endpoints_and_a_wider_range():
    assert pressure_psi(0, 0.5, 4.5, 100) == pytest.approx(-12.5)
    # 4.5 V at the sensor is 3.0 V at the pin: 3.0 / 3.3 * 4095 = 3722.727...
    counts_at_full_scale = round(3.0 / 3.3 * 4095)
    assert pressure_psi(counts_at_full_scale, 0.5, 4.5, 100) == pytest.approx(100, abs=0.05)
    assert pressure_psi(2730, 0.5, 4.5, 150) == pytest.approx(105)


def test_pressure_rejects_a_zero_span():
    with pytest.raises(ZeroDivisionError):
        pressure_psi(1000, 1.0, 1.0, 100)


def test_load_cell_tare_and_scale():
    assert load_eu(128000, 100000, 280) == pytest.approx(100)
    assert load_eu(100000, 100000, 280) == pytest.approx(0)
    # Negative factor: green/white pair swapped on the connector.
    assert load_eu(128000, 100000, -280) == pytest.approx(-100)


def test_load_cell_rejects_a_zero_factor():
    with pytest.raises(ZeroDivisionError):
        load_eu(10, 0, 0)
