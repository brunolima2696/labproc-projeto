#!/bin/bash

set -e

sudo apt update
sudo apt install -y \
    retroarch \
    libretro-snes9x \
    i2c-tools \
    python3-smbus \
    python3-gpiozero \
    python3-evdev \
    python3-pytest

UINPUT_RULE='KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"'
TARGET_USER="${SUDO_USER:-$USER}"

sudo modprobe uinput
printf '%s\n' 'uinput' | sudo tee /etc/modules-load.d/labproc-uinput.conf >/dev/null
printf '%s\n' "$UINPUT_RULE" | sudo tee /etc/udev/rules.d/99-labproc-uinput.rules >/dev/null
sudo usermod -aG input "$TARGET_USER"
sudo udevadm control --reload-rules
sudo chgrp input /dev/uinput
sudo chmod 0660 /dev/uinput

echo "Reinicie a sessão para aplicar a permissão do controle virtual."
