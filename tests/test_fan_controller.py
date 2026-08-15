from io import StringIO

import pytest

from modules.FanController import FanController, next_fan_state


class FakeRelay:
    def __init__(self, active=False):
        self.is_active = active
        self.closed = False

    def on(self):
        self.is_active = True

    def off(self):
        self.is_active = False

    def close(self):
        self.closed = True


class FakeThermometer:
    def __init__(self, readings):
        self._readings = iter(readings)
        self.closed = False

    def read_celsius(self):
        reading = next(self._readings)
        if isinstance(reading, Exception):
            raise reading
        return reading

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    ("temperature", "current_state", "expected_state"),
    [
        (24.0, False, False),
        (25.0, False, True),
        (23.0, True, True),
        (20.0, True, False),
    ],
)
def test_next_fan_state_applies_hysteresis(
    temperature, current_state, expected_state
):
    assert next_fan_state(temperature, current_state) is expected_state


def test_controller_applies_temperature_sequence_and_closes_devices():
    thermometer = FakeThermometer([24.0, 25.0, 23.0, 20.0])
    relay = FakeRelay()
    controller = FanController(thermometer=thermometer, relay=relay)

    expected_states = [False, True, True, False]
    for expected_state in expected_states:
        controller.update_once()
        assert relay.is_active is expected_state

    controller.close()

    assert relay.is_active is False
    assert relay.closed is True
    assert thermometer.closed is True


def test_read_error_enables_fan_and_reports_only_once():
    thermometer = FakeThermometer(
        [RuntimeError("falha no ADC"), RuntimeError("falha no ADC")]
    )
    relay = FakeRelay()
    error_stream = StringIO()
    controller = FanController(
        thermometer=thermometer,
        relay=relay,
        error_stream=error_stream,
    )

    assert controller.update_once() is None
    assert controller.update_once() is None

    assert relay.is_active is True
    assert error_stream.getvalue().count("Erro no controle da ventoinha") == 1

    controller.close()


def test_invalid_temperature_limits_are_rejected():
    with pytest.raises(ValueError):
        next_fan_state(22.0, False, on_temperature=20.0, off_temperature=20.0)

