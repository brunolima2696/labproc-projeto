#!/usr/bin/env python3
########################################################################
# Filename    : Joystick.py
# Description : Expose the Freenove joystick and buttons as keyboard input.
# Based on    : Freenove Projects Kit Joystick.py
# Adapted for labproc-projeto: 2026/08/14
########################################################################
import sys
import threading
import time

from evdev import UInput, ecodes
from gpiozero import Button

from modules.utils.ADCDevice import ADCDevice, ADS7830


ADC_ADDRESS = 0x48
JOYSTICK_X_CHANNEL = 5
JOYSTICK_Y_CHANNEL = 6
JOYSTICK_DEAD_ZONE = 40
POLL_INTERVAL = 0.01

# Default RetroArch keyboard bindings: A=X, B=Z, X=S and Y=A.
BUTTON_KEY_MAP = {
    16: ecodes.KEY_X,
    21: ecodes.KEY_Z,
    26: ecodes.KEY_S,
    20: ecodes.KEY_A,
}

DIRECTION_KEYS = (
    ecodes.KEY_LEFT,
    ecodes.KEY_RIGHT,
    ecodes.KEY_UP,
    ecodes.KEY_DOWN,
)


class FreenoveController:
    def __init__(self):
        self._adc = None
        self._buttons = {}
        self._keyboard = None
        self._thread = None
        self._stop_event = threading.Event()
        self._key_states = {
            key: False for key in (*DIRECTION_KEYS, *BUTTON_KEY_MAP.values())
        }

        try:
            self._adc = self._open_adc()
            self._buttons = {
                pin: Button(pin, pull_up=True, bounce_time=0.03)
                for pin in BUTTON_KEY_MAP
            }
            self._keyboard = UInput(
                {ecodes.EV_KEY: list(self._key_states)},
                name="Freenove SNES Controls",
            )
            self._center_x, self._center_y = self._calibrate_joystick()
        except Exception:
            self.close()
            raise

    @staticmethod
    def _open_adc():
        probe = ADCDevice(ADC_ADDRESS)
        try:
            if not probe.detectI2C(ADC_ADDRESS):
                raise RuntimeError("ADS7830 não encontrado no barramento I²C")
        finally:
            probe.close()
        return ADS7830(ADC_ADDRESS)

    def _calibrate_joystick(self):
        samples_x = []
        samples_y = []
        for _ in range(20):
            samples_x.append(self._adc.analogRead(JOYSTICK_X_CHANNEL))
            samples_y.append(self._adc.analogRead(JOYSTICK_Y_CHANNEL))
            time.sleep(0.01)
        return sum(samples_x) // len(samples_x), sum(samples_y) // len(samples_y)

    def _set_key(self, key, pressed):
        if self._key_states[key] == pressed:
            return False
        self._key_states[key] = pressed
        self._keyboard.write(ecodes.EV_KEY, key, int(pressed))
        return True

    def _update_axis(self, value, center, negative_key, positive_key):
        negative_pressed = value < center - JOYSTICK_DEAD_ZONE
        positive_pressed = value > center + JOYSTICK_DEAD_ZONE
        changed = self._set_key(negative_key, negative_pressed)
        changed |= self._set_key(positive_key, positive_pressed)
        return changed

    def _update(self):
        x_value = self._adc.analogRead(JOYSTICK_X_CHANNEL)
        y_value = self._adc.analogRead(JOYSTICK_Y_CHANNEL)

        changed = self._update_axis(
            x_value, self._center_x, ecodes.KEY_LEFT, ecodes.KEY_RIGHT
        )
        changed |= self._update_axis(
            y_value, self._center_y, ecodes.KEY_UP, ecodes.KEY_DOWN
        )

        for pin, key in BUTTON_KEY_MAP.items():
            changed |= self._set_key(key, self._buttons[pin].is_pressed)

        if changed:
            self._keyboard.syn()

    def _release_all(self):
        if self._keyboard is None:
            return
        changed = False
        for key in self._key_states:
            changed |= self._set_key(key, False)
        if changed:
            self._keyboard.syn()

    def _poll(self):
        try:
            while not self._stop_event.is_set():
                self._update()
                self._stop_event.wait(POLL_INTERVAL)
        except Exception as error:
            print(f"Erro no controle da placa: {error}", file=sys.stderr)
        finally:
            self._release_all()

    def start(self):
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        self._release_all()

    def close(self):
        self.stop()
        for button in self._buttons.values():
            button.close()
        self._buttons.clear()
        if self._keyboard is not None:
            self._keyboard.close()
            self._keyboard = None
        if self._adc is not None:
            self._adc.close()
            self._adc = None
