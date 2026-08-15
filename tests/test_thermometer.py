import pytest

from modules.Thermometer import Thermometer, adc_to_celsius


class FakeADC:
    def __init__(self, value):
        self.value = value
        self.channels = []
        self.closed = False

    def analogRead(self, channel):
        self.channels.append(channel)
        return self.value

    def close(self):
        self.closed = True


def test_reference_resistance_corresponds_to_25_celsius():
    assert adc_to_celsius(127.5) == pytest.approx(25.0)


@pytest.mark.parametrize("value", [0, 255])
def test_invalid_adc_values_are_rejected(value):
    with pytest.raises(ValueError):
        adc_to_celsius(value)


def test_thermometer_reads_channel_zero_and_closes_adc():
    adc = FakeADC(127.5)
    thermometer = Thermometer(adc=adc)

    assert thermometer.read_celsius() == pytest.approx(25.0)
    assert adc.channels == [0]

    thermometer.close()
    assert adc.closed is True

