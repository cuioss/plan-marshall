---
name: plan-marshall-opencode-target-rules
description: "OpenCode harness operational rules, tool invariants, execution discipline, and deployed flat layout. Reference library for OpenCode environments."
mode: knowledge
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
metadata:
  bundle: plan-marshall-opencode
  skill: target-rules
---

# OpenCode Target Rules

**KNOWLEDGE MODE**: Operational rules, tool invariants, and execution discipline for OpenCode environments.

## Constraints & Hard Rules

1. **OpenCode Tool & Permission Invariants**:
   - Use `bash` for command execution with single-command discipline.
   - Use `read`, `write`, and `edit` for file operations.
   - Use `glob` and `grep` for codebase exploration.
   - Use `question` for interactive user clarification.
   - Use `task` for background task dispatch and `skill` for skill activation.
   - Use `webfetch` for network retrieval of documentation or external references.

2. **Deployed Flat Layout**:
   - OpenCode skills deploy to a flat layout: `~/.config/opencode/skills/{bundle}-{skill}/` (global) or `.opencode/skills/{bundle}-{skill}/` (workspace).
   - Skills declare identity metadata (`metadata.bundle` and `metadata.skill`) in frontmatter.
   - Internal references resolve within the flat skill directory structure.

3. **Command & `.plan/` Discipline**:
   - One command per `bash` call — no `&&`, `;`, `|`, `$()`, subshells, loops, or heredocs.
   - All `.plan/` operations run exclusively through `python3 .plan/execute-script.py`. Never read, write, or edit `.plan/` files directly.
   - Store all temporary files in `.plan/temp/`.

## Available Standards

**File**: `standards/opencode-rules.md`

Detailed specifications for native rule delivery, tool mappings, command constraints, and workspace setup.
