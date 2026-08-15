import pytest

from modules.StopWatch import elapsed_to_digits


@pytest.mark.parametrize(
    ("elapsed_seconds", "expected_digits"),
    [
        (0, (0, 0, 0, 0)),
        (125, (0, 2, 0, 5)),
        (3599, (5, 9, 5, 9)),
        (3600, (6, 0, 0, 0)),
    ],
)
def test_elapsed_time_is_split_into_display_digits(
    elapsed_seconds, expected_digits
):
    assert elapsed_to_digits(elapsed_seconds) == expected_digits


def test_negative_elapsed_time_is_rejected():
    with pytest.raises(ValueError):
        elapsed_to_digits(-1)

