---
name: c-pro
description: Efficient, memory-safe C: ownership, pointer arithmetic, bounds, error paths, system calls, embedded and performance-critical code. Use for writing, reviewing or optimizing C.
---

# c-pro (wrapper)

This skill wraps the `c-pro` agent prompt from [wshobson/agents](https://github.com/wshobson/agents)
(MIT), vendored and pinned in `vendor/wshobson-agents`. Read [upstream.md](upstream.md) now and
follow it as your working guidance for this task.

Rules that take precedence over upstream.md:
- The project's own AGENTS.md/CLAUDE.md, its language standard, toolchain and coding standard win.
- Ignore upstream frontmatter fields such as `model`; they do not apply here.
- Code samples are illustrative: check ISRs, critical sections, DMA and clock setup against the
  datasheet/reference manual and the project's existing patterns before reuse.
- Never flash or erase a board without the user's explicit approval. Never write fuses, option
  bytes or lock bits at all: give the user the exact command instead (global rule).
