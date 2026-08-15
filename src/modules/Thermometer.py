#!/usr/bin/env python3
########################################################################
# Filename    : Thermometer.py
# Description : Read the Freenove board thermistor.
# Author      : www.freenove.com
# modification: 2024/07/29
# Adapted for labproc-projeto: 2026/08/14
########################################################################
import math


ADC_ADDRESS = 0x48
THERMISTOR_CHANNEL = 0
REFERENCE_VOLTAGE = 3.3
REFERENCE_RESISTANCE = 10.0
REFERENCE_TEMPERATURE_C = 25.0
THERMISTOR_BETA = 3950.0


def adc_to_celsius(value):
    if value <= 0 or value >= 255:
        raise ValueError(f"Leitura inválida do termistor: {value}")

    voltage = value / 255.0 * REFERENCE_VOLTAGE
    resistance = (
        REFERENCE_RESISTANCE
        * voltage
        / (REFERENCE_VOLTAGE - voltage)
    )
    temperature_kelvin = 1.0 / (
        1.0 / (273.15 + REFERENCE_TEMPERATURE_C)
        + math.log(resistance / REFERENCE_RESISTANCE) / THERMISTOR_BETA
    )
    return temperature_kelvin - 273.15


class Thermometer:
    def __init__(self, adc=None):
        self._adc = adc if adc is not None else self._open_adc()

    @staticmethod
    def _open_adc():
        from modules.utils.ADCDevice import ADCDevice, ADS7830

        probe = ADCDevice(ADC_ADDRESS)
        try:
            if not probe.detectI2C(ADC_ADDRESS):
                raise RuntimeError("ADS7830 não encontrado no barramento I²C")
        finally:
            probe.close()

        return ADS7830(ADC_ADDRESS)

    def read_celsius(self):
        value = self._adc.analogRead(THERMISTOR_CHANNEL)
        return adc_to_celsius(value)

    def close(self):
        if self._adc is not None:
            self._adc.close()
            self._adc = None
