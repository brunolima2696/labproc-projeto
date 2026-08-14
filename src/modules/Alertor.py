#!/usr/bin/env python3
########################################################################
# Filename    : Alertor.py
# Description : Control the Freenove Projects Board passive buzzer.
# Author      : www.freenove.com
# modification: 2024/07/29
# Adapted for labproc-projeto: 2026/08/14
########################################################################
import time

from gpiozero import TonalBuzzer
from gpiozero.tones import Tone


BUZZER_PIN = 4
START_TONES = (440.0, 660.0)
STOP_TONES = tuple(reversed(START_TONES))


class EmulatorBuzzer:
    def __init__(self, pin=BUZZER_PIN, tone_duration=0.08, pause=0.03):
        self._buzzer = TonalBuzzer(pin)
        self._tone_duration = tone_duration
        self._pause = pause

    def _play(self, frequencies):
        for index, frequency in enumerate(frequencies):
            try:
                self._buzzer.play(Tone(frequency))
                time.sleep(self._tone_duration)
            finally:
                self._buzzer.stop()

            if index < len(frequencies) - 1:
                time.sleep(self._pause)

    def emulator_started(self):
        self._play(START_TONES)

    def emulator_stopped(self):
        self._play(STOP_TONES)

    def close(self):
        self._buzzer.stop()
        self._buzzer.close()
