#!/usr/bin/env python3
########################################################################
# Filename    : Thermometer.py
# Description : Read the Freenove board thermistor.
# Author      : www.freenove.com
# modification: 2024/07/29
# Adapted for labproc-projeto: 2026/08/14
########################################################################
import math

from modules.utils.ADCDevice import ADCDevice, ADS7830


ADC_ADDRESS = 0x48
THERMISTOR_CHANNEL = 0
REFERENCE_VOLTAGE = 3.3
REFERENCE_RESISTANCE = 10.0
REFERENCE_TEMPERATURE_C = 25.0
THERMISTOR_BETA = 3950.0


class Thermometer:
    def __init__(self):
        self._adc = None

        probe = ADCDevice(ADC_ADDRESS)
        try:
            if not probe.detectI2C(ADC_ADDRESS):
                raise RuntimeError("ADS7830 não encontrado no barramento I²C")
        finally:
            probe.close()

        self._adc = ADS7830(ADC_ADDRESS)

    def read_celsius(self):
        value = self._adc.analogRead(THERMISTOR_CHANNEL)
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

    def close(self):
        if self._adc is not None:
            self._adc.close()
            self._adc = None
