import pytest

from estop_logic import display_mode, next_latch


@pytest.mark.parametrize(
    ("latched", "sense", "reset", "expected"),
    [
        (False, False, False, False),
        (False, False, True, False),
        (False, True, False, True),
        (False, True, True, True),
        (True, False, False, True),
        (True, False, True, False),
        (True, True, False, True),
        (True, True, True, True),
    ],
)
def test_latch_truth_table(latched, sense, reset, expected):
    assert next_latch(latched, sense, reset) is expected


def test_reset_after_release_is_the_only_way_out():
    latched = next_latch(False, True, False)
    assert latched is True
    # Mushroom released, button not pressed yet.
    assert next_latch(latched, False, False) is True
    # Reset while it is still in does nothing.
    assert next_latch(True, True, True) is True
    assert next_latch(latched, False, True) is False


def test_displays_follow_the_latch_and_the_log_does_not():
    assert display_mode(False, False) == "channels"
    assert display_mode(False, True) == "channels"
    assert display_mode(True, True) == "stop"
    assert display_mode(True, False) == "reset"
