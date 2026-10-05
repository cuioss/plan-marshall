---
name: target-rules
description: "Antigravity harness operational rules, tool invariants, execution discipline, and runtime integration constraints. Reference library for Google Antigravity environments."
user-invocable: false
mode: knowledge
---

# Antigravity Target Rules

**KNOWLEDGE MODE**: Operational rules, tool invariants, and execution discipline for Google Antigravity (AGY) environments.

## Constraints & Hard Rules

1. **Antigravity Tool Invariants**:
   - Use `run_command` for executing shell commands. Always maintain sandbox safety (`BypassSandbox: false` by default).
   - Use `view_file` to view file contents; do not use `cat`, `head`, `tail`, or shell pagers.
   - Use `write_to_file` to create or overwrite files; do not use shell redirection or `touch`.
   - Use `replace_file_content` for surgical, contiguous edits to existing files.
   - Use `ask_question` when user clarification or decision-making is needed.
   - Use `invoke_subagent` and `send_message` for subagent coordination; never communicate with the user via `send_message`.
   - Use `manage_task` to monitor or cancel background commands and scheduled tasks.
   - Use `schedule` for timers and background reminders; never run `sleep` in bash.

2. **Terminal Sandbox Discipline**:
   - One command per `run_command` call — no `&&`, `;`, `|`, `$()`, subshells, loops, or heredocs.
   - Never propose `cd` commands. Set `Cwd` explicitly within the workspace directory.
   - No shell file inspection tools (`ls`, `find`, `cat`, `grep`). Use dedicated tools or structured queries (`architecture`).

3. **Reactive Task & Subagent Handling**:
   - Never poll `manage_task status` in a loop.
   - Antigravity provides automatic reactive wakeup when background tasks finish or subagents send messages. Simply end turn after launching.

4. **`.plan/` Script-Only Access**:
   - Never read, write, or edit `.plan/` files directly.
   - All `.plan/` access goes exclusively through `python3 .plan/execute-script.py` with the appropriate notation.
   - Store all temporary files in `.plan/temp/`.

5. **Artifact Isolation**:
   - UI artifacts, markdown reports, and diagrams belong in `<appDataDir>/brain/<conversation-id>/`.
   - Keep artifacts isolated from repository source code and `.plan/` state.

## Available Standards

**File**: `standards/antigravity-rules.md`

Detailed specifications for native rule delivery, tool mappings, command constraints, and workspace setup.
