import json
from types import SimpleNamespace

import pytest

from modules.PerformanceMonitor import PerformanceMonitor, read_cpu_temperature


class FakeProcess:
    pid = 4321

    def __init__(self, running=True):
        self.running = running

    def poll(self):
        return None if self.running else 0


class FakeProcessMetrics:
    def cpu_percent(self, interval=None):
        assert interval is None
        return 37.25

    def memory_info(self):
        return SimpleNamespace(rss=150 * 1024 * 1024)


class FakePsutil:
    def __init__(self):
        self.process = FakeProcessMetrics()

    def Process(self, pid):
        assert pid == 4321
        return self.process

    def cpu_percent(self, interval=None):
        assert interval is None
        return 62.5

    def virtual_memory(self):
        return SimpleNamespace(percent=48.75)


class FakeFanController:
    last_temperature = 25.4
    fan_is_on = True


def test_monitor_writes_one_json_object_per_sample(tmp_path):
    times = iter((100.0, 101.25))
    timestamps = iter(
        (
            "2026-08-21T14:32:05-03:00",
            "2026-08-21T14:32:06-03:00",
        )
    )
    log_path = tmp_path / "performance-test.jsonl"
    monitor = PerformanceMonitor(
        process=FakeProcess(),
        fan_controller=FakeFanController(),
        log_path=log_path,
        psutil_module=FakePsutil(),
        time_source=lambda: next(times),
        timestamp_source=lambda: next(timestamps),
        cpu_temperature_reader=lambda: 54.125,
    )

    first_record = monitor.sample_once()
    second_record = monitor.sample_once()
    monitor.close()

    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert records == [first_record, second_record]
    assert first_record == {
        "timestamp": "2026-08-21T14:32:05-03:00",
        "elapsed_s": 0.0,
        "retroarch_pid": 4321,
        "retroarch_cpu_pct": 37.25,
        "retroarch_memory_mb": 150.0,
        "system_cpu_pct": 62.5,
        "system_memory_pct": 48.75,
        "cpu_temp_c": 54.12,
        "board_temp_c": 25.4,
        "fan_on": True,
    }
    assert second_record["elapsed_s"] == 1.25


def test_monitor_does_not_record_after_retroarch_exits(tmp_path):
    log_path = tmp_path / "performance-test.jsonl"
    monitor = PerformanceMonitor(
        process=FakeProcess(running=False),
        fan_controller=FakeFanController(),
        log_path=log_path,
        psutil_module=FakePsutil(),
    )

    assert monitor.sample_once() is None
    assert not log_path.exists()


def test_cpu_temperature_reader_converts_millicelsius(tmp_path):
    temperature_path = tmp_path / "temp"
    temperature_path.write_text("55125\n", encoding="utf-8")

    assert read_cpu_temperature(temperature_path) == 55.125


def test_invalid_poll_interval_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        PerformanceMonitor(
            process=FakeProcess(),
            fan_controller=FakeFanController(),
            log_path=tmp_path / "performance.jsonl",
            poll_interval=0,
            psutil_module=FakePsutil(),
        )
