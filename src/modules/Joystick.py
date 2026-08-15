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


ADC_ADDRESS = 0x48
JOYSTICK_X_CHANNEL = 5
JOYSTICK_Y_CHANNEL = 6
JOYSTICK_DEAD_ZONE = 40
POLL_INTERVAL = 0.01

BUTTON_PINS = (16, 21, 26, 20)


def axis_state(value, center, dead_zone=JOYSTICK_DEAD_ZONE):
    return value < center - dead_zone, value > center + dead_zone


class FreenoveController:
    def __init__(
        self,
        adc=None,
        buttons=None,
        keyboard=None,
        key_codes=None,
        center=None,
        calibration_samples=20,
        calibration_delay=0.01,
        dead_zone=JOYSTICK_DEAD_ZONE,
    ):
        if key_codes is None:
            from evdev import ecodes

            key_codes = ecodes

        self._key_codes = key_codes
        # Default RetroArch keyboard bindings: A=X, B=Z, X=S and Y=A.
        self._button_key_map = {
            16: key_codes.KEY_X,
            21: key_codes.KEY_Z,
            26: key_codes.KEY_S,
            20: key_codes.KEY_A,
        }
        self._direction_keys = (
            key_codes.KEY_LEFT,
            key_codes.KEY_RIGHT,
            key_codes.KEY_UP,
            key_codes.KEY_DOWN,
        )
        self._adc = adc
        self._buttons = buttons if buttons is not None else {}
        self._keyboard = keyboard
        self._calibration_samples = calibration_samples
        self._calibration_delay = calibration_delay
        self._dead_zone = dead_zone
        self._thread = None
        self._stop_event = threading.Event()
        self._key_states = {
            key: False
            for key in (*self._direction_keys, *self._button_key_map.values())
        }

        try:
            if self._adc is None:
                self._adc = self._open_adc()
            if buttons is None:
                self._buttons = self._open_buttons()
            if self._keyboard is None:
                self._keyboard = self._open_keyboard()
            if center is None:
                center = self._calibrate_joystick()
            self._center_x, self._center_y = center
        except Exception:
            self.close()
            raise

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

    def _open_buttons(self):
        from gpiozero import Button

        return {
            pin: Button(pin, pull_up=True, bounce_time=0.03)
            for pin in self._button_key_map
        }

    def _open_keyboard(self):
        from evdev import UInput

        return UInput(
            {self._key_codes.EV_KEY: list(self._key_states)},
            name="Freenove SNES Controls",
        )

    def _calibrate_joystick(self):
        samples_x = []
        samples_y = []
        for _ in range(self._calibration_samples):
            samples_x.append(self._adc.analogRead(JOYSTICK_X_CHANNEL))
            samples_y.append(self._adc.analogRead(JOYSTICK_Y_CHANNEL))
            time.sleep(self._calibration_delay)
        return sum(samples_x) // len(samples_x), sum(samples_y) // len(samples_y)

    def _set_key(self, key, pressed):
        if self._key_states[key] == pressed:
            return False
        self._key_states[key] = pressed
        self._keyboard.write(self._key_codes.EV_KEY, key, int(pressed))
        return True

    def _update_axis(self, value, center, negative_key, positive_key):
        negative_pressed, positive_pressed = axis_state(
            value, center, self._dead_zone
        )
        changed = self._set_key(negative_key, negative_pressed)
        changed |= self._set_key(positive_key, positive_pressed)
        return changed

    def update_once(self):
        x_value = self._adc.analogRead(JOYSTICK_X_CHANNEL)
        y_value = self._adc.analogRead(JOYSTICK_Y_CHANNEL)

        changed = self._update_axis(
            x_value,
            self._center_x,
            self._key_codes.KEY_RIGHT,
            self._key_codes.KEY_LEFT,
        )
        changed |= self._update_axis(
            y_value,
            self._center_y,
            self._key_codes.KEY_DOWN,
            self._key_codes.KEY_UP,
        )

        for pin, key in self._button_key_map.items():
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
                self.update_once()
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
