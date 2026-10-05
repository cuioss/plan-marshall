# plan-marshall-opencode

OpenCode harness operational rules and runtime integration bundle for plan-marshall.

## Purpose

- Defines tool mapping and execution invariants for OpenCode environments.
- Enforces command discipline (`bash` tool with single command per call).
- Establishes deployed flat layout expectations (`~/.config/opencode/skills/{bundle}-{skill}/` or `.opencode/skills/{bundle}-{skill}/`).
- Guarantees fail-safe access to `.plan/` via `python3 .plan/execute-script.py`.
- Enables zero-token native rule delivery into `.opencode/rules/plan-marshall-target-rules.md`.

## Skills (1 skill)

| Skill | Purpose |
|-------|---------|
| `target-rules` | OpenCode harness operational rules, tool invariants, execution discipline, and flat layout standards |

## Architecture

```
plan-marshall-opencode/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    └── target-rules/
        ├── SKILL.md
        └── standards/
            └── opencode-rules.md
```

## Target Scoping

This bundle declares `"targets": ["opencode"]` in `.claude-plugin/plugin.json`. It is emitted exclusively to the `opencode` target tree and omitted from `claude` and `antigravity` targets.
