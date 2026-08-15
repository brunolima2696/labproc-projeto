import pytest

from modules.Joystick import FreenoveController, axis_state


class FakeKeyCodes:
    EV_KEY = "event-key"
    KEY_LEFT = "left"
    KEY_RIGHT = "right"
    KEY_UP = "up"
    KEY_DOWN = "down"
    KEY_X = "x"
    KEY_Z = "z"
    KEY_S = "s"
    KEY_A = "a"


class FakeADC:
    def __init__(self, x=128, y=128):
        self.values = {5: x, 6: y}
        self.closed = False

    def analogRead(self, channel):
        return self.values[channel]

    def close(self):
        self.closed = True


class FakeButton:
    def __init__(self):
        self.is_pressed = False
        self.closed = False

    def close(self):
        self.closed = True


class FakeKeyboard:
    def __init__(self):
        self.events = []
        self.sync_count = 0
        self.closed = False

    def write(self, event_type, key, value):
        self.events.append((event_type, key, value))

    def syn(self):
        self.sync_count += 1

    def close(self):
        self.closed = True


def make_controller():
    adc = FakeADC()
    buttons = {pin: FakeButton() for pin in (16, 21, 26, 20)}
    keyboard = FakeKeyboard()
    controller = FreenoveController(
        adc=adc,
        buttons=buttons,
        keyboard=keyboard,
        key_codes=FakeKeyCodes,
        center=(128, 128),
    )
    return controller, adc, buttons, keyboard


def test_axis_state_respects_dead_zone():
    assert axis_state(88, 128) == (False, False)
    assert axis_state(87, 128) == (True, False)
    assert axis_state(168, 128) == (False, False)
    assert axis_state(169, 128) == (False, True)


def test_centered_joystick_does_not_emit_events():
    controller, _, _, keyboard = make_controller()

    controller.update_once()

    assert keyboard.events == []
    assert keyboard.sync_count == 0
    controller.close()


def test_joystick_uses_inverted_physical_axes():
    controller, adc, _, keyboard = make_controller()
    adc.values.update({5: 50, 6: 50})

    controller.update_once()

    assert (FakeKeyCodes.EV_KEY, FakeKeyCodes.KEY_RIGHT, 1) in keyboard.events
    assert (FakeKeyCodes.EV_KEY, FakeKeyCodes.KEY_DOWN, 1) in keyboard.events
    assert (FakeKeyCodes.EV_KEY, FakeKeyCodes.KEY_LEFT, 1) not in keyboard.events
    assert (FakeKeyCodes.EV_KEY, FakeKeyCodes.KEY_UP, 1) not in keyboard.events
    controller.close()


@pytest.mark.parametrize(
    ("pin", "key"),
    [
        (16, FakeKeyCodes.KEY_X),
        (21, FakeKeyCodes.KEY_Z),
        (26, FakeKeyCodes.KEY_S),
        (20, FakeKeyCodes.KEY_A),
    ],
)
def test_button_gpio_mapping(pin, key):
    controller, _, buttons, keyboard = make_controller()
    buttons[pin].is_pressed = True

    controller.update_once()

    assert (FakeKeyCodes.EV_KEY, key, 1) in keyboard.events
    controller.close()

