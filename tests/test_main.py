import main as application


class FakeProcess:
    def __init__(self, return_code=0):
        self.return_code = return_code
        self.running = True
        self.wait_calls = []

    def poll(self):
        return None if self.running else self.return_code

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        self.running = False
        return self.return_code

    def terminate(self):
        self.running = False

    def kill(self):
        self.running = False


class FakeBuzzer:
    def __init__(self):
        self.calls = []

    def emulator_started(self):
        self.calls.append("started")

    def emulator_stopped(self):
        self.calls.append("stopped")

    def close(self):
        self.calls.append("close")


class FakeModule:
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")

    def close(self):
        self.calls.append("close")


def test_main_starts_and_closes_all_components():
    buzzer = FakeBuzzer()
    controller = FakeModule()
    display = FakeModule()
    process = FakeProcess(return_code=0)
    commands = []

    result = application.main(
        which=lambda executable: f"/usr/bin/{executable}",
        process_factory=lambda command: commands.append(command) or process,
        component_factories={
            "buzzer": lambda: buzzer,
            "controller": lambda: controller,
            "display": lambda: display,
        },
    )

    assert result == 0
    assert commands == [("retroarch",)]
    assert buzzer.calls == ["started", "stopped", "close"]
    assert controller.calls == ["start", "stop", "close"]
    assert display.calls == ["start", "stop", "close"]


def test_main_returns_error_when_retroarch_is_missing(capsys):
    result = application.main(which=lambda executable: None)

    assert result == 1
    assert "RetroArch não está instalado" in capsys.readouterr().err
