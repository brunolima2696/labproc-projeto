#!/usr/bin/env python3
########################################################################
# Filename    : FanController.py
# Description : Control the 5 V fan through the Freenove board relay.
# Adapted for labproc-projeto: 2026/08/14
########################################################################
import sys
import threading

from gpiozero import DigitalOutputDevice

from modules.Thermometer import Thermometer


RELAY_PIN = 12
FAN_ON_TEMPERATURE_C = 25.0
FAN_OFF_TEMPERATURE_C = 20.0
POLL_INTERVAL = 0.5


class FanController:
    def __init__(
        self,
        relay_pin=RELAY_PIN,
        on_temperature=FAN_ON_TEMPERATURE_C,
        off_temperature=FAN_OFF_TEMPERATURE_C,
        poll_interval=POLL_INTERVAL,
    ):
        if off_temperature >= on_temperature:
            raise ValueError("A temperatura de desligamento deve ser menor que a de acionamento")

        self._relay = None
        self._thermometer = None
        self._on_temperature = on_temperature
        self._off_temperature = off_temperature
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread = None
        self._read_error_reported = False

        try:
            self._relay = DigitalOutputDevice(relay_pin, initial_value=False)
            self._thermometer = Thermometer()
        except Exception:
            self.close()
            raise

    def _update(self):
        temperature = self._thermometer.read_celsius()

        if temperature >= self._on_temperature and not self._relay.is_active:
            self._relay.on()
        elif temperature <= self._off_temperature and self._relay.is_active:
            self._relay.off()

    def _monitor(self):
        while not self._stop_event.is_set():
            try:
                self._update()
                self._read_error_reported = False
            except Exception as error:
                # Keep cooling enabled if temperature monitoring becomes unavailable.
                if self._relay is not None:
                    self._relay.on()
                if not self._read_error_reported:
                    print(f"Erro no controle da ventoinha: {error}", file=sys.stderr)
                    self._read_error_reported = True

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
