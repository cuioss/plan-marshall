envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:47Z

# Candidate lesson L8 — RECURRENCE: references.affected_files is frozen at outline time so every derived finalize gate under-scopes

- component: `plan-marshall:phase-5-execute`
- category: bug
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: recurrence of a known archetype

## Observation — first-party reproduction

`references.json` `affected_files` lists **9** paths, all from outline time. The merged squash commit `38f45faeb` carries **14**.

- Intersection: 7 → recall 77.8%, **precision 50.0%**
- Declared but never touched (2): `test/plan-marshall/manage-logging/test_logging.py`, `test_logging_orchestrator_store.py`
- Realized but never declared (7): both new ADRs (`016`, `017`), `tools-script-executor/templates/execute-script.py.template`, and four `pm-plugin-development/plugin-doctor` files (`rule-catalog.md`, `rule-provenance.md`, `_analyze_literal_count.py`, `test_analyze_literal_count.py`)

Scope moved **twice during finalize**, both times legitimately and both times logged:

- 17:44Z — self-review finding `bddc03` fixed the executor template (an eighth unguarded `get_log_path` entry point the plan's own docstring claimed did not exist).
- 19:29Z — operator explicitly accepted a scope deviation on pr-comment `6b6ce5` and directed the derived-standards-index mechanism be built in this plan.

Neither growth updated `affected_files`.

## The downstream consequence, concretely

`scope_estimate` remained `single_module` while the realized footprint spans **2 bundles** (`plan-marshall`, `pm-plugin-development`) and **5 skills**. `project:finalize-step-plugin-doctor` ran at 17:36Z and reported *"plugin-doctor clean: 3 skills gated"* — a green gate over 3 of the 5 skills the plan ultimately shipped, and it was never re-run after the 19:29Z scope acceptance added four `pm-plugin-development` files.

That is the failure mode in full: an `affected_files`-derived gate reports **clean** against a scope that has since moved, and the report of cleanliness carries no indication of the denominator it used.

## Why this is filed as a recurrence, not a discovery

The `affected_files` under-recording archetype is already known. What this instance adds is the *mechanism of the miss*: the under-recording is not a writer bug at execute time, it is that **nothing re-derives `affected_files` after a finalize-phase scope change** (self-review fix, triage-accepted scope deviation, ADR creation). Any mitigation scoped to phase-5 task completion will not cover these three paths.

## Proposed remedy

Re-derive `affected_files` from the live worktree diff at each finalize step boundary that can mutate source (self-review, simplify, security-audit, triage loop-back, adr-propose), and re-run any scope-gated step whose recorded gate scope is now a strict subset of the realized footprint. At minimum, have `pre-push-quality-gate` / `plugin-doctor` publish the file/skill set they gated so a stale denominator is visible in the display detail.
