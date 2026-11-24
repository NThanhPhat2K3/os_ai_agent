# <Project name>: agent rules

Global rules: `~/.codex/AGENTS.md` / `~/.claude/CLAUDE.md` (from os_ai_agent). This file adds project specifics.
Setup: `ln -s AGENTS.md CLAUDE.md` so both agents read the same file.

## Target
- MCU / board: <e.g. ESP32-S3, rev B>
- SDK / toolchain (pinned): <e.g. ESP-IDF v5.x.y, xtensa-esp32s3-elf-gcc 14.x>
- RTOS: <FreeRTOS / uC-OS2 / Zephyr / bare metal>

## Commands
- Build: `<idf.py build>`
- Unit tests (host): `<...>`
- Static analysis: `cppcheck --project=build/compile_commands.json`, `clang-tidy -p build <file>`
- Flash (ASK FIRST): `<idf.py -p /dev/ttyUSB0 flash monitor>`

## Hardware map
| Signal | Pin | Notes |
|---|---|---|
| <LED> | <GPIO5> | <active low> |

## Rules
- Do not edit third-party code in `<components/vendor/...>`.
- Coding standard: <MISRA C:2012 subset / project style>.
- Record decisions in `docs/decisions.md`.
