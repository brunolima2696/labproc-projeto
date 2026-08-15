#!/usr/bin/env python3
########################################################################
# Filename    : FanController.py
# Description : Control the 5 V fan through the Freenove board relay.
# Adapted for labproc-projeto: 2026/08/14
########################################################################
import sys
import threading


RELAY_PIN = 12
FAN_ON_TEMPERATURE_C = 25.0
FAN_OFF_TEMPERATURE_C = 20.0
POLL_INTERVAL = 0.5


def next_fan_state(
    temperature,
    fan_is_on,
    on_temperature=FAN_ON_TEMPERATURE_C,
    off_temperature=FAN_OFF_TEMPERATURE_C,
):
    if off_temperature >= on_temperature:
        raise ValueError("A temperatura de desligamento deve ser menor que a de acionamento")
    if temperature >= on_temperature:
        return True
    if temperature <= off_temperature:
        return False
    return fan_is_on


class FanController:
    def __init__(
        self,
        relay_pin=RELAY_PIN,
        on_temperature=FAN_ON_TEMPERATURE_C,
        off_temperature=FAN_OFF_TEMPERATURE_C,
        poll_interval=POLL_INTERVAL,
        thermometer=None,
        relay=None,
        error_stream=None,
    ):
        if off_temperature >= on_temperature:
            raise ValueError("A temperatura de desligamento deve ser menor que a de acionamento")

        self._relay = relay
        self._thermometer = thermometer
        self._on_temperature = on_temperature
        self._off_temperature = off_temperature
        self._poll_interval = poll_interval
        self._error_stream = error_stream if error_stream is not None else sys.stderr
        self._stop_event = threading.Event()
        self._thread = None
        self._read_error_reported = False

        try:
            if self._relay is None:
                from gpiozero import DigitalOutputDevice

                self._relay = DigitalOutputDevice(relay_pin, initial_value=False)
            if self._thermometer is None:
                from modules.Thermometer import Thermometer

                self._thermometer = Thermometer()
        except Exception:
            self.close()
            raise

    def update_once(self):
        try:
            temperature = self._thermometer.read_celsius()
            should_be_on = next_fan_state(
                temperature,
                self._relay.is_active,
                self._on_temperature,
                self._off_temperature,
            )
            self._relay.on() if should_be_on else self._relay.off()
            self._read_error_reported = False
            return temperature
        except Exception as error:
            # Keep cooling enabled if temperature monitoring becomes unavailable.
            if self._relay is not None:
                self._relay.on()
            if not self._read_error_reported:
                print(
                    f"Erro no controle da ventoinha: {error}",
                    file=self._error_stream,
                )
                self._read_error_reported = True
            return None

    def _monitor(self):
        while not self._stop_event.is_set():
            self.update_once()
            self._stop_event.wait(self._poll_interval)

    def start(self):
        if self._thread is not None:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        if self._relay is not None:
            self._relay.off()

    def close(self):
        self.stop()
        if self._thermometer is not None:
            self._thermometer.close()
            self._thermometer = None
        if self._relay is not None:
            self._relay.close()
            self._relay = None
