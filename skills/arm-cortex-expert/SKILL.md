---
name: arm-cortex-expert
description: Firmware and driver development for ARM Cortex-M microcontrollers (STM32, nRF52, SAMD, Teensy): peripherals, interrupts, DMA, memory barriers, RTOS integration. Use for Cortex-M firmware design, review or debugging.
---

# arm-cortex-expert (wrapper)

This skill wraps the `arm-cortex-expert` agent prompt from [wshobson/agents](https://github.com/wshobson/agents)
(MIT), vendored and pinned in `vendor/wshobson-agents`. Read [upstream.md](upstream.md) now and
follow it as your working guidance for this task.

Rules that take precedence over upstream.md:
- The project's own AGENTS.md/CLAUDE.md, its language standard, toolchain and coding standard win.
- Ignore upstream frontmatter fields such as `model`; they do not apply here.
- Code samples are illustrative: check ISRs, critical sections, DMA and clock setup against the
  datasheet/reference manual and the project's existing patterns before reuse.
- Never flash, erase or write option bytes/fuses without the user's explicit approval.
