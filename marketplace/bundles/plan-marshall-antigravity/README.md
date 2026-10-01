# plan-marshall-antigravity

Google Antigravity harness operational rules and runtime integration bundle for plan-marshall.

## Purpose

- Defines tool mapping and execution invariants for Google Antigravity environments.
- Enforces terminal sandbox discipline (`run_command` with `BypassSandbox: false`, single command per call).
- Establishes reactive task and subagent lifecycle patterns (no polling loops).
- Guarantees fail-safe access to `.plan/` via `python3 .plan/execute-script.py`.
- Isolates conversation artifacts in `<appDataDir>/brain/<conversation-id>/` from repository workspace state.
- Enables zero-token native rule delivery into `.agents/rules/plan-marshall-target-rules.md`.

## Skills (1 skill)

| Skill | Purpose |
|-------|---------|
| `target-rules` | Antigravity harness operational rules, tool invariants, execution discipline, and sandbox constraints |

## Architecture

```
plan-marshall-antigravity/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    └── target-rules/
        ├── SKILL.md
        └── standards/
            └── antigravity-rules.md
```

## Target Scoping

This bundle declares `"targets": ["antigravity"]` in `.claude-plugin/plugin.json`. It is emitted exclusively to the `antigravity` target tree and omitted from `claude` and `opencode` targets.
