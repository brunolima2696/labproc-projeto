#!/usr/bin/env python3
########################################################################
# Filename    : StopWatch.py
# Description : Control SevenSegmentDisplay with 74HC595.
# Author      : www.freenove.com
# modification: 2024/07/29
# Adapted for labproc-projeto: 2026/08/14
########################################################################
import threading
import time


DATA_PIN = 22
LATCH_PIN = 27
CLOCK_PIN = 17

MSB_FIRST = 2
DIGIT_ENABLE = (0x01, 0x02, 0x04, 0x08)
DIGIT_CODES = (0xC0, 0xF9, 0xA4, 0xB0, 0x99, 0x92, 0x82, 0xF8, 0x80, 0x90)
DECIMAL_POINT_ON = 0x7F
SEGMENTS_OFF = 0xFF
DIGIT_TIME = 0.002


def elapsed_to_digits(elapsed_seconds):
    if elapsed_seconds < 0:
        raise ValueError("O tempo decorrido não pode ser negativo")

    minutes = (elapsed_seconds // 60) % 100
    seconds = elapsed_seconds % 60
    return (
        minutes // 10,
        minutes % 10,
        seconds // 10,
        seconds % 10,
    )


class SessionDisplay:
    def __init__(self, data_pin=None, latch_pin=None, clock_pin=None, time_source=None):
        if data_pin is None or latch_pin is None or clock_pin is None:
            from gpiozero import OutputDevice

        self._data_pin = data_pin if data_pin is not None else OutputDevice(DATA_PIN)
        self._latch_pin = (
            latch_pin if latch_pin is not None else OutputDevice(LATCH_PIN)
        )
        self._clock_pin = (
            clock_pin if clock_pin is not None else OutputDevice(CLOCK_PIN)
        )
        self._time_source = time_source if time_source is not None else time.monotonic
        self._stop_event = threading.Event()
        self._thread = None
        self._started_at = None

    def _shift_out(self, order, value):
        for bit in range(8):
            self._clock_pin.off()
            if order == MSB_FIRST:
                state = value & (0x80 >> bit)
            else:
                state = value & (0x01 << bit)
            self._data_pin.on() if state else self._data_pin.off()
            self._clock_pin.on()

    def _write(self, digit, segments):
        self._latch_pin.off()
        self._shift_out(MSB_FIRST, digit)
        self._shift_out(MSB_FIRST, segments)
        self._latch_pin.on()

    def _display_elapsed(self, elapsed_seconds):
        digits = elapsed_to_digits(elapsed_seconds)

        for index, value in enumerate(digits):
            segments = DIGIT_CODES[value]
            if index == 1:
                segments &= DECIMAL_POINT_ON

            self._write(DIGIT_ENABLE[index], segments)
            if self._stop_event.wait(DIGIT_TIME):
                return
            self._write(0x00, SEGMENTS_OFF)

    def _refresh(self):
        while not self._stop_event.is_set():
            elapsed_seconds = int(self._time_source() - self._started_at)
            self._display_elapsed(elapsed_seconds)

    def start(self):
        if self._thread is not None:
            return

        self._started_at = self._time_source()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._refresh, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        self._write(0x00, SEGMENTS_OFF)

    def close(self):
        self.stop()
        self._data_pin.close()
        self._latch_pin.close()
        self._clock_pin.close()
