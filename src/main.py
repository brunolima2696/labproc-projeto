#!/usr/bin/env python3

import shutil
import subprocess
import sys
from contextlib import suppress

RETROARCH_COMMAND = ("retroarch",)


def load_component_factories():
    from modules.Alertor import EmulatorBuzzer
    from modules.Joystick import FreenoveController
    from modules.StopWatch import SessionDisplay

    return {
        "buzzer": EmulatorBuzzer,
        "controller": FreenoveController,
        "display": SessionDisplay,
    }


def stop_process(process):
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main(
    command=RETROARCH_COMMAND,
    which=None,
    process_factory=None,
    component_factories=None,
):
    which = which if which is not None else shutil.which
    process_factory = (
        process_factory if process_factory is not None else subprocess.Popen
    )

    if which(command[0]) is None:
        print("Erro: RetroArch não está instalado ou não está no PATH.", file=sys.stderr)
        return 1

    buzzer = None
    controller = None
    display = None
    retroarch = None
    emulator_started = False

    try:
        if component_factories is None:
            component_factories = load_component_factories()

        buzzer = component_factories["buzzer"]()
        controller = component_factories["controller"]()
        display = component_factories["display"]()

        retroarch = process_factory(command)
        emulator_started = True

        controller.start()
        display.start()
        buzzer.emulator_started()

        return retroarch.wait()
    except KeyboardInterrupt:
        if retroarch is not None:
            stop_process(retroarch)
        return 130
    except Exception as error:
        print(f"Erro ao executar o controlador: {error}", file=sys.stderr)
        return 1
    finally:
        if retroarch is not None and retroarch.poll() is None:
            with suppress(Exception):
                stop_process(retroarch)

        if emulator_started:
            if controller is not None:
                with suppress(Exception):
                    controller.stop()
            if display is not None:
                with suppress(Exception):
                    display.stop()
            if buzzer is not None:
                with suppress(Exception):
                    buzzer.emulator_stopped()

        if buzzer is not None:
            with suppress(Exception):
                buzzer.close()
        if controller is not None:
            with suppress(Exception):
                controller.close()
        if display is not None:
            with suppress(Exception):
                display.close()


if __name__ == "__main__":
    raise SystemExit(main())
