# Emulação de SNES em Raspberry Pi

Projeto da disciplina PCS3732 — Laboratório de Processadores. A aplicação usa uma Raspberry Pi 3B+ para executar o RetroArch com o núcleo libretro-snes9x e integrar os periféricos da Freenove Projects Board.

O `main.py` abre o RetroArch e coordena o joystick da placa, quatro botões GPIO, o display de sete segmentos e o buzzer. Controles USB também podem ser usados diretamente pelo RetroArch.

## Funcionalidades

- execução da interface normal do RetroArch;
- emulação de SNES pelo núcleo libretro-snes9x;
- joystick da placa usado como direcional;
- botões A, B, X e Y conectados aos GPIOs;
- display de quatro dígitos com o tempo da sessão;
- alertas sonoros no início e no encerramento;
- suporte nativo do RetroArch a controles USB;
- módulos experimentais para leitura do termistor e controle de uma ventoinha de 5 V.

> O termômetro e o controle da ventoinha ainda não foram validados no hardware.

## Requisitos

### Hardware

- Raspberry Pi 3B+;
- cartão microSD com Raspberry Pi OS ou sistema compatível baseado em Debian;
- Freenove Projects Board;
- monitor ou TV com HDMI;
- fonte de alimentação adequada;
- controle USB opcional;
- ventoinha de 5 V para os testes térmicos.

### Software

As dependências são instaladas pelo script do projeto:

- RetroArch e libretro-snes9x;
- Python 3;
- GPIO Zero;
- SMBus e ferramentas I²C;
- evdev e módulo `uinput`;
- pytest para os testes automatizados.

## Instalação

Clone o repositório e entre no diretório do projeto:

```bash
git clone https://github.com/brunolima2696/labproc-projeto.git
cd labproc-projeto
```

Execute o instalador. O próprio script solicitará `sudo` quando necessário:

```bash
bash scripts/install_dependencies.sh
```

Habilite o barramento I²C:

```bash
sudo raspi-config nonint do_i2c 0
```

Reinicie a Raspberry Pi para aplicar o carregamento do `uinput` e a nova permissão do usuário:

```bash
sudo reboot
```

O instalador cria configurações em `/etc/modules-load.d/` e `/etc/udev/rules.d/` para permitir que o programa gere as entradas virtuais usadas pelo joystick e pelos botões da placa.

## Execução

Depois da reinicialização, entre novamente no diretório do projeto e execute:

```bash
python3 src/main.py
```


O RetroArch será aberto. Use a interface para escolher o núcleo libretro-snes9x e carregar ROMs. Nenhuma ROM é distribuída neste repositório.

Para encerrar, feche o RetroArch ou pressione `Ctrl+C` no terminal que executa o `main.py`. Os módulos ativos e os GPIOs serão finalizados pelo programa.

## Controles

O joystick analógico é lido pelo ADS7830 e convertido em setas de teclado por um dispositivo virtual `uinput`. Os quatro botões usam os mapeamentos padrão do RetroArch:

| Comando SNES | Entrada física | Tecla enviada |
|---|---|---|
| Direcional | Joystick A5/A6 | Setas |
| A | GPIO16 | `X` |
| B | GPIO21 | `Z` |
| X | GPIO26 | `S` |
| Y | GPIO20 | `A` |

Alternativamente, um controle USB pode ser conectado antes de iniciar o programa, a partir do suporte nativo do RetroArch. Pode ser necessária configuração adicional.

## Conexões principais

Os números abaixo seguem a numeração BCM:

| Recurso | GPIO ou canal |
|---|---|
| I²C SDA / SCL | GPIO2 / GPIO3 |
| Buzzer | GPIO4 |
| Relé da ventoinha | GPIO12 |
| Botão A | GPIO16 |
| Clock do display | GPIO17 |
| Botão Y | GPIO20 |
| Botão B | GPIO21 |
| Dados do display | GPIO22 |
| Botão X | GPIO26 |
| Latch do display | GPIO27 |
| Termistor | ADS7830 A0 |
| Joystick | ADS7830 A5/A6 |

> A ventoinha deve usar alimentação de 5 V comutada pelo relé. Ela não deve ser alimentada diretamente por um GPIO.

## Estrutura do projeto

```text
src/main.py                       Coordenação da aplicação
src/modules/Joystick.py           Joystick e botões
src/modules/StopWatch.py          Display e tempo da sessão
src/modules/Alertor.py            Buzzer
src/modules/Thermometer.py        Leitura de temperatura experimental
src/modules/FanController.py      Controle térmico experimental
src/modules/utils/ADCDevice.py    Comunicação com o ADS7830
scripts/install_dependencies.sh   Instalação das dependências
docs/relatorio.md                 Relatório técnico do projeto
tests/                            Testes automatizados com hardware simulado
pytest.ini                        Configuração da suíte de testes
```

Os exemplos do [repositório da Freenove](https://github.com/Freenove/Freenove_Projects_Kit_for_Raspberry_Pi) foram usados como referência para a integração dos componentes da placa.

## Diagnóstico rápido

Verifique se o ADS7830 aparece no endereço `0x48`:

```bash
i2cdetect -y 1
```

Confira a existência e as permissões do dispositivo virtual:

```bash
ls -l /dev/uinput
groups
```

Se o grupo `input` ainda não aparecer para o usuário, reinicie a sessão ou a Raspberry Pi. Se o RetroArch não for encontrado, execute novamente `scripts/install_dependencies.sh` e confira as mensagens do `apt`.

## Testes automatizados

Os testes usam objetos simulados no lugar do ADC, relé, botões, teclado virtual, display e processo do RetroArch. Dessa forma, verificam a lógica sem acionar os periféricos reais.

```bash
python3 -m pytest
```

A suíte cobre a histerese e a falha segura da ventoinha, a conversão da temperatura, a zona morta e os mapeamentos do joystick, a formatação do tempo da sessão e o ciclo de inicialização e encerramento do `main.py`.

Os testes automatizados não verificam conexões elétricas, calibração do termistor nem o comportamento físico do relé, display, buzzer e controles. Esses itens ainda precisam ser testados na Raspberry Pi.

## Documentação

Uma descrição mais detalhada da arquitetura e das decisões do projeto está em [docs/relatorio.md](docs/relatorio.md).

## Licença

Este projeto é distribuído sob a licença [GPL-3.0](LICENSE).
