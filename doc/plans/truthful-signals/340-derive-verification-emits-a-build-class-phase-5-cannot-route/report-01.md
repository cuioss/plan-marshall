# Run report — 340-derive-verification-emits-a-build-class-phase-5-cannot-route (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/derive-verification-build-phase-5-am54le` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `plan-marshall:ref-code-quality` (read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (read from bundle path)
- (conditional skills loaded during implementation — recorded below)

## Deliverables

### D0 — GATE: re-derive the defect against HEAD (read by symbol)

**Verdict: CONFIRMED at HEAD.** The defect is real, highly reachable, and reproduces
by construction whenever a derived `compile`/`test-compile` command resolves
`orchestrator` tier (the fail-closed default for any **unmeasured** command).

**Emission site (read by symbol):**
`marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py`
- `_resolve_verbs_for_build_class(build_class)` (≈L383) maps
  `compile → ['compile']`, `module-tests → ['test-compile', 'module-tests']`,
  `verify → ['verify']`.
- `cmd_derive_verification(args)` (≈L403) classifies each changed path to a
  `build_class`, resolves those verbs, and returns `status: 'success'` with the
  command rows — each row carrying the resolved executable for verbs `compile`,
  `test-compile`, `module-tests`, `verify`.

**Compose resolution site (read by symbol):**
`marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/`
- `_manifest_rules.py::_VERB_TO_PHASE_5_STEP` (≈L915) = `{quality-gate, verify,
  module-tests, coverage}` only. `_verb_to_phase_5_step` (≈L986) is a bare dict
  lookup — `compile`/`test-compile` return `None`.
- `manage-execution-manifest.py::_route_task_verification_commands` (≈L1169):
  an **orchestrator-tier** command whose verb is unmapped generalizes to
  `verify:{verb}` (≈L1260) → so `compile → verify:compile`,
  `test-compile → verify:test-compile`, appended to `phase_5.verification_steps`.
- `_manifest_validation.py::check_emitted_steps_resolvable` (≈L743) →
  `_check_step_resolvable` (≈L634) → `_verify_canonicals_universe` (≈L592). The
  universe seeds from `_manifest_core.py::_CANONICAL_TO_ROLE` (≈L332) =
  `{quality-gate, verify, module-tests, coverage, integration-tests, e2e}` ∪
  ext-point canonicals ∪ domain-appended — **none of which contains `compile` or
  `test-compile`.** So `verify:compile`/`verify:test-compile` → `unresolvable_step`,
  failing the whole compose.

**Tier trigger (read by symbol):** `manage-architecture/scripts/_cmd_client_build.py::
_compute_execution_tier_fields` (≈L315) — `tier = 'per_task' if (measured and not
exceeds) else 'orchestrator'`. An **unmeasured** command fails closed to
`orchestrator`. Standalone `compile`/`test-compile` keys are essentially never
measured in normal operation, so they persistently resolve `orchestrator`.

**Stamping site (read):** `phase-4-plan/SKILL.md` (≈L589-597) stamps **every**
returned `commands[].executable` into the task's `verification.commands` — so
`compile`/`test-compile` rows reach compose unchanged.

**Reachability in this project (read):** `build-pyproject/scripts/extension.py::
classify_globs` (≈L235) routes `marketplace/bundles/*.py → production` and
`test/*.py → test`; the base defaults map `production → compile`,
`test → module-tests` (≈L246). Every production change emits `compile`; every test
change emits `test-compile`.

**Emission reports `status: 'success'`** while carrying these unroutable commands
(`cmd_derive_verification` return, ≈L463) — the ⭐ epic-theme half of the defect.

**Scope finding (per the plan's re-scope clause):** the emitted verbs `compile`
and `test-compile` are **legitimate** registered canonical commands
(`extension-api/standards/canonical-commands.md` §§ "Source-conditional",
"Test-conditional"; `resolve-command.md` § "Build-class → verification command"),
deliberately derived, and providing real per-task verification value (fast compile
check; test-tree type-check). The mismatched component is the **compose router**
(its `verify:{verb}` generalization produces an unresolvable step for these
build-phase canonicals). Per the plan's out-of-scope note ("If D0 finds [the class
is legitimate and the router is wrong], say so and re-scope"), this is the re-scope
case. Decision escalated to the operator (see § Findings / this run's residue).

### D1–D4

_Pending the scope decision._

## Build gate

_Pending._

## Findings

_Pending._

## Reviewer participation

_Pending._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
