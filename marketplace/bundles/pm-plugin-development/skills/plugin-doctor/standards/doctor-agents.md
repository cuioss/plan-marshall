# Doctor Agents Workflow

Follows the common workflow pattern (see SKILL.md). Reference guide: `agents-guide.md`.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `agent-name` (optional): Analyze specific agent
- `--no-fix` (optional): Diagnosis only, no fixes

## Agent-Specific Checks

**Check against agents-guide.md**:
- Tool fit score >= 70% (good) or >= 90% (excellent)
- No agent-task-tool-prohibited violations when the Claude rule-pack binds — the `Task` tool is
  denied to Claude sub-agents. `plugin-create:component validate` accepts a `Task` declaration on
  the OpenCode target (the `task` tool exists and subagent dispatch is supported there), and the
  doctor reports this rule only when `resolve_runtime_target() != 'opencode'`, matching the
  validator's binding.
- No agent-maven-restricted violations (only maven-builder can use Maven)
- No agent-lessons-via-skill violations (must use manage-lessons skill, not self-invoke)
- No `hardcoded-model-on-canonical` violations (see below)

### `hardcoded-model-on-canonical` rule

**Rationale**: The role-variants system (see [`plan-marshall:plan-marshall/standards/effort-variants.md`](../../../../plan-marshall/skills/plan-marshall/standards/effort-variants.md)) routes per-role model selection through build-time variant emission. Canonical agent files in `marketplace/bundles/{bundle}/agents/` MUST NOT pin `model:` or `effort:` directly — variants are emitted by the ACTIVE target with the right `(model, effort)` per ordinal level, and the canonical no-suffix file serves the `inherit` resolution. Pinning a model on the canonical defeats the system; declaring `implements:` AND a model line creates silent shadowing.

The rule fires hard errors in two branches:

1. **`missing_implements`**: Agent has `model:` or `effort:` AND lacks `implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor`. Either remove the hardcoded pin, or add the `implements:` declaration to opt into role-based variant emission.
2. **`shadowing_with_implements`**: Agent declares `implements: <ext-point>` AND has `model:` or `effort:`. The build target sets these on emitted variants; the canonical must not duplicate them.

**Only exception**: variant frontmatter written by the build target into the active target's build-output directory (`target/{target}/` — e.g. `target/claude/{bundle}/agents/{name}-{level}.md`). The doctor's source-of-truth scan path is rooted at `marketplace/bundles/`; the rule's file-path check exempts anything under the active target's build-output prefix.

**Bloat thresholds** (component-type specific):

| Component | NORMAL | LARGE | BLOATED | CRITICAL |
|-----------|--------|-------|---------|----------|
| Agents | <300 | 300-500 | 500-800 | >800 |
| Commands | <100 | 100-150 | 150-200 | >200 |
| Skills | <400 | 400-800 | 800-1200 | >1200 |

## Agent-Specific Fix Categories

**Risky fixes** (always prompt):
- agent-task-tool-prohibited violations (requires architectural refactoring)
- agent-maven-restricted violations (Maven usage restriction)
- agent-lessons-via-skill violations (self-invocation)
- Bloat issues (agents >500 lines)
