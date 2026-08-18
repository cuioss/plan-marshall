# Run report — 020-target-scoped-components (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/target-scoped-components-k3qt57`    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded by reading the bundle source path (the `plan-marshall` plugin is not installed in this
cloud session, so `Skill: {bundle}:{skill}` notation was not attempted).

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |
| `pm-plugin-development:plugin-architecture` | `SKILL.md` / bundle structure (D4) |
| `plan-marshall:persona-implementer` | Production-code work identity |

Every skill resolved at its bundle path; none was unobtainable.

## Claim labels — re-derived before building

The plan's claim table required re-derivation. All were re-checked against the tree at HEAD of
`origin/main`:

| Claim | Verdict |
|---|---|
| No `targets:` frontmatter filter exists anywhere under `marketplace/targets/` | **CONFIRMED.** No `targets` handling in any `marketplace/targets/**/*.py` or `*.json`, and no bundle component declared the field. The premise held; the plan was not halted. |
| The Claude target is a verbatim mirror gated by `run_equality_check` | **CONFIRMED.** `claude/target.py::generate` mirrors via `emit_bundle_verbatim` and gates on `equality_check.run_equality_check`. |
| `TARGET_REGISTRY` holds `claude`, `opencode`, `pr-agent` | **CONFIRMED** as a lead only. D1/D2 iterate the registry; no enumeration was written. |
| `tools-fix-intellij-diagnostics.md` has YAML frontmatter incl. `mcp__ide__getDiagnostics` | **CONFIRMED.** |
| `pr-agent` emits no per-component bundle tree | **CONFIRMED.** `pr_agent/target.py` overrides `emits_bundle_tree` to `False` and emits one `.pr_agent.toml`. |
| `plugin-doctor` frontmatter validation would flag an unknown `targets:` key today | **REFUTED.** The doctor carries no closed-frontmatter-key rule at all — no allowlist of permitted keys exists in any analyzer — so an unknown key was neither flagged nor validated. D4 therefore had to ADD validation rather than extend an existing allowlist. |

## Deliverables

| Deliverable | What was done | Commit | Verification state |
|---|---|---|---|
| **D1 — filter mechanism** | New `marketplace/targets/component_targets.py` parses the `targets:` declaration and answers `emits_to(path, target_name)`. Both component-tree-emitting targets consult it: the Claude verbatim emitter (`excluded_emission_roots` + `is_under_any`, skipping a scoped-out file or a whole scoped-out skill directory) and its manifest generator (`plugin_json_gen` drops the same entries), and the OpenCode emitter (per-skill / per-agent / per-command skip). The governed set is derived from `TARGET_REGISTRY` filtered by each target's `emits_bundle_tree` capability — never enumerated. Absent field still means every target. | `fab9611` | `test_component_targets.py` (31 collected), `test_target_scoped_emission.py` (14 collected) |
| **D2 — fail-closed validation** | `_validate` rejects an unknown target name, an empty list, and a list naming only non-component-tree targets. Every message names the component path and the offending value. Validation fires on every path that READS components: both component-tree targets' emit paths and the Claude target's validate-only mode (which re-walks each bundle's components for this check alone). A `pr-agent`-only run reads no component and so validates none; the doctor rule is the authoring-time net there. | `fab9611` | `test_component_targets.py` + `test_target_scoped_emission.py::test_generation_fails_*` |
| **D3 — first consumer** | `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md` declares `targets: [claude]`. | `fab9611` | Asserted by generation-output listing (below) |
| **D4 — authoring surface** | New `targets-scope-invalid` plugin-doctor rule (`_analyze_target_scope.py`), registered in `_rule_registry.py` and wired into both the quality gate and analyze mode, with rows in `rule-provenance.md` and `rule-catalog.md` and a firing positive fixture in `_fixtures.py`. The field, its semantics, its validation table, and the three-condition admission test are documented in `plugin-architecture/references/frontmatter-standards.md` § "Target Scoping". | `fab9611` | `test_analyze_target_scope.py` (18 collected); the doctor runs clean over the real tree with D3's declaration in place |

### D3 generation-output listing (the plan's own "Done when" evidence)

`python3 marketplace/targets/generate.py --target all --output /tmp/tgt-all` exits **0**:

```text
claude: produced 1166 entries
opencode: produced 1090 entries
pr-agent: produced 1 entries
```

- `/tmp/tgt-all/claude/plan-marshall/commands/` — contains `tools-fix-intellij-diagnostics.md`.
- `/tmp/tgt-all/claude/plan-marshall/.claude-plugin/plugin.json` — `commands` declares
  `./commands/tools-fix-intellij-diagnostics.md`.
- `/tmp/tgt-all/opencode/command/` — the command is **absent**.
- `pr-agent` emits `.pr_agent.toml` only, unaffected by construction.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` reports **15 changed Python files**, so the gate
applies. Working tree confirmed clean (`git status --porcelain` empty) before the diff was taken, so
the gate saw the whole branch.

`./pw verify` — **SUCCESS**, all three sub-steps clean:

- quality-gate: `ruff … All checks passed!`, `mypy … Success: no issues found in 415 source files`,
  `SPDX-header check passed`, plugin-doctor `total_issues: 0`
- test-compile: mypy over 775 test files, clean
- module-tests: 0 failed, 0 errors (the count is re-derived at close, below)

No lockfile churn: `git status --porcelain` was empty after the build, and every commit staged
explicit deliverable paths (never `git add -A`).

## Findings

_(filled in as verification rounds complete)_

## Reviewer participation

_(filled in after the PR is opened)_

## Cost

_(filled in at close)_

## Contract check (Step 9)

_(filled in at close)_

## What have we learned (Step 9)

_(filled in at close)_

## Residue

_(filled in at close)_
