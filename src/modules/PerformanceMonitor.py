#!/usr/bin/env python3
########################################################################
# Filename    : PerformanceMonitor.py
# Description : Record RetroArch and Raspberry Pi performance metrics.
# Adapted for labproc-projeto: 2026/08/21
########################################################################
import json
import math
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


POLL_INTERVAL = 1.0
CPU_TEMPERATURE_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
BYTES_PER_MEBIBYTE = 1024 * 1024


def read_cpu_temperature(path=CPU_TEMPERATURE_PATH):
    try:
        temperature = float(Path(path).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None

    if temperature > 1000:
        temperature /= 1000
    return temperature


def _rounded(value, digits=2):
    if value is None:
        return None

    value = float(value)
    if not math.isfinite(value):
        return None
    return round(value, digits)


class PerformanceMonitor:
    def __init__(
        self,
        process,
        fan_controller,
        log_path,
        poll_interval=POLL_INTERVAL,
        psutil_module=None,
        time_source=None,
        timestamp_source=None,
        cpu_temperature_reader=None,
        error_stream=None,
    ):
        if poll_interval <= 0:
            raise ValueError("O intervalo de monitoramento deve ser positivo")

        if psutil_module is None:
            import psutil

            psutil_module = psutil

        self._process = process
        self._fan_controller = fan_controller
        self._log_path = Path(log_path)
        self._poll_interval = poll_interval
        self._psutil = psutil_module
        self._process_metrics = psutil_module.Process(process.pid)
        self._time_source = time_source if time_source is not None else time.monotonic
        self._timestamp_source = (
            timestamp_source
            if timestamp_source is not None
            else lambda: datetime.now().astimezone().isoformat(timespec="milliseconds")
        )
        self._cpu_temperature_reader = (
            cpu_temperature_reader
            if cpu_temperature_reader is not None
            else read_cpu_temperature
        )
        self._error_stream = error_stream if error_stream is not None else sys.stderr
        self._stop_event = threading.Event()
        self._thread = None
        self._log_file = None
        self._started_at = None

    def _optional(self, callback):
        try:
            return callback()
        except Exception:
            return None

    def _board_temperature(self):
        if self._fan_controller is None:
            return None
        return self._optional(lambda: self._fan_controller.last_temperature)

    def _fan_state(self):
        if self._fan_controller is None:
            return None

        state = self._optional(lambda: self._fan_controller.fan_is_on)
        return None if state is None else bool(state)

    def _ensure_log_file(self):
        if self._log_file is not None:
            return

        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_path.open("a", encoding="utf-8")

    def sample_once(self):
        if self._process.poll() is not None:
            return None

        now = self._time_source()
        if self._started_at is None:
            self._started_at = now

        process_cpu = self._optional(
            lambda: self._process_metrics.cpu_percent(interval=None)
        )
        process_memory = self._optional(
            lambda: self._process_metrics.memory_info().rss / BYTES_PER_MEBIBYTE
        )
        system_cpu = self._optional(lambda: self._psutil.cpu_percent(interval=None))
        system_memory = self._optional(lambda: self._psutil.virtual_memory().percent)
        cpu_temperature = self._optional(self._cpu_temperature_reader)

        record = {
            "timestamp": self._timestamp_source(),
            "elapsed_s": _rounded(now - self._started_at, 3),
            "retroarch_pid": self._process.pid,
            "retroarch_cpu_pct": _rounded(process_cpu),
            "retroarch_memory_mb": _rounded(process_memory),
            "system_cpu_pct": _rounded(system_cpu),
            "system_memory_pct": _rounded(system_memory),
            "cpu_temp_c": _rounded(cpu_temperature),
            "board_temp_c": _rounded(self._board_temperature()),
            "fan_on": self._fan_state(),
        }

        self._ensure_log_file()
        self._log_file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            + "\n"
        )
        self._log_file.flush()
        return record

    def _monitor(self):
        try:
            while not self._stop_event.is_set():
                if self.sample_once() is None:
                    break
                self._stop_event.wait(self._poll_interval)
        except Exception as error:
            print(f"Erro no monitor de desempenho: {error}", file=self._error_stream)

    def start(self):
        if self._thread is not None:
            return

        self._ensure_log_file()
        self._started_at = self._time_source()
        self._optional(lambda: self._process_metrics.cpu_percent(interval=None))
        self._optional(lambda: self._psutil.cpu_percent(interval=None))
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval + 1)
            self._thread = None

        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None

    def close(self):
        self.stop()
