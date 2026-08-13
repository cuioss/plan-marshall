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

### Scope decision (operator-approved re-scope)

D0 found the emitted verbs legitimate and the router mismatched. Escalated to the
operator via `AskUserQuestion` (interactive session, plan's flagged re-scope case).
**Question:** which fix direction — router fix + provenance / emitter constraint
(plan as written) / provenance only. **Operator answer: "Router fix + provenance".**
So the plan's D1/D2 (constrain the emitter) are superseded by an equivalent-intent
router fix that preserves the legitimate `compile`/`test-compile` per-task checks;
D3 (provenance) and D4 (matched-pair tests) are unchanged in intent.

### R — Router fix (supersedes D1/D2, operator-approved)

`manage-execution-manifest.py::_route_task_verification_commands`: an
orchestrator-tier command whose verb is a KNOWN canonical build command
(`ALL_CANONICAL_COMMANDS`, imported from `extension_base` — derived from the
vocabulary registry, **not** a hand-listed `{compile, test-compile}`) with no
resolvable `verify:{verb}` gate (`_check_step_resolvable(candidate, 'phase_5')`)
is kept with the task (per_task fallback) instead of routed to a nonexistent gate.
Restricted to known canonicals so a custom/typo'd verb still routes and fails loud.
Emits a provenance decision-log line naming the verb and the absent gate.
*Verification:* new tests `test_compile_kept_with_task_not_routed`,
`test_test_compile_kept_with_task_not_routed`, `test_mixed_task_composes_without_unresolvable_step`
— all seen to fail pre-fix, pass post-fix. Commit `2430747`.

### D3 — Compose-error provenance

`_manifest_validation.py::check_emitted_steps_resolvable`: the `unresolvable_step`
error now distinguishes a marshal.json-authored step (named by the author's key,
"in marshal.json") from a routed/derived step (present in the emitted list, absent
from the marshal step map → "appended by execution_tier COMMAND routing from a
derived `verification.commands` entry (architecture derive-verification) — NOT
authored in marshal.json"). CSV-fallback (marshal_map None) keeps the emitted-id
wording. *Verification:* `test_routed_step_error_names_routing_origin` reads the
actual error string (fails pre-fix — the old message falsely said "in marshal.json"),
`test_marshal_authored_step_error_names_marshal_json` control. Commit `2430747`.

### D4 — Matched control pair (each seen to fail pre-fix)

Empirically confirmed by a stash-out pre-fix run of the target test file:
- **Unroutable (fail pre-fix → pass post-fix):** `test_compile_kept_with_task_not_routed`
  (`mutated==1` pre-fix), `test_test_compile_kept_with_task_not_routed`,
  `test_mixed_task_composes_without_unresolvable_step` (pre-fix phase_5 was
  `['verify:compile', 'verify:module-tests']` — the literal unroutable step),
  `test_routed_step_error_names_routing_origin` (D3).
- **Routable / over-broad guards (pass pre+post):** `test_module_tests_still_routes`,
  `test_custom_verb_still_routes_and_fails_loud`, `test_marshal_authored_step_error_names_marshal_json`.

Note on "each seen to fail pre-fix": that clause was written for the emitter-constraint
direction where both halves would fail. Under the router-fix direction the routable
half is an over-broad-fix guard that correctly passes pre+post (it cannot fail pre-fix
without breaking existing correct routing); the unroutable half and D3 are the meaningful
"seen to fail pre-fix" cases, and all four were observed to fail pre-fix.

### Documentation kept in lock-step

- `manage-execution-manifest.py` router docstring — the two→three fall-throughs.
- `_manifest_rules.py` `_VERB_TO_PHASE_5_STEP` comment — the build-phase-canonical carve-out.
- `manage-execution-manifest/standards/decision-rules.md` § routing predicate — the carve-out.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **Python changed**
(`manage-execution-manifest.py`, `_manifest_validation.py`, `_manifest_rules.py`,
and the test file). Full path taken.

- **Targeted pre-fix run** (behavioral files stashed to HEAD):
  `./pw module-tests plan-marshall/manage-execution-manifest/test_compose_execution_tier.py`
  → 4 failed, 39 passed — the 4 failures are exactly the new unroutable + D3 tests
  (empirical D0 reproduction / D4 "seen to fail pre-fix").
- **Targeted post-fix run** (fix restored): same command → **43 passed**.
- **Full `./pw verify plan-marshall`** (`UV_HTTP_TIMEOUT=600`): **`=== verify: SUCCESS ===`**
  — `16448 passed, 1 skipped in 482.22s`; coverage line confirms all sub-steps ran:
  mypy(production) 278 files, ruff, SPDX headers, mypy(test) 588 files, module-tests.

No `uv.lock` churn (checked `git status` before staging; staged the 5 deliverable
paths explicitly, never `git add -A`).

## Findings

### Pre-PR verification sub-agent (round 1) — 5 findings

All three code deliverables verified PASS by the independent sub-agent (router
carve-out correct and registry-derived; D3 error genuinely diagnosable; D4 matched
pair valid, unroutable half seen to fail pre-fix). Findings were documentation +
one low-severity code edge:

1. **[fixed]** `manage-execution-manifest/SKILL.md:569,571` — the "every parseable
   verb generalizes to `verify:{verb}` / no leaf ever runs an orchestrator-tier
   command inline" claim was made false by the carve-out. Rewrote § "Command-level
   execution_tier routing" to name the two kept-with-task cases. (commit `53c9926`)
2. **[fixed]** `manage-execution-manifest/SKILL.md:174,449` — the `unresolvable_step`
   message docs asserted it always names the "original marshal.json key". Updated to
   describe the marshal.json-authored vs derive-verification-routed provenance split.
   (commit `53c9926`)
3. **[fixed]** `test_compose_execution_tier.py` `TestRouteUnmappedOrchestratorVerbs`
   docstring (L603–605) — "Only an unparseable command survives per-task" now false.
   Clarified it covers only the custom-verb generalization; pointed to
   `TestBuildPhaseCanonicalCarveOut`. (commit `53c9926`)
4. **[fixed]** `_manifest_validation.py::check_emitted_steps_resolvable` — the
   routed-provenance branch was phase-agnostic but named derive-verification (a
   phase-5-only routing path), so an unresolvable phase-6 step absent from the map
   would be misattributed. Scoped the derive-verification attribution to `phase_5`;
   phase_6 gets a neutral "composer-injected" note. New test
   `test_phase_6_absent_step_is_not_attributed_to_derive_verification`. (commit `53c9926`)
5. **[addressed by ongoing report]** The sub-agent read an early report snapshot with
   `_Pending._` sections. The report is written as the run proceeds; the D1–D4 /
   build-gate / findings sections are now filled.

Remediation re-verified: `./pw verify plan-marshall` → SUCCESS (16449 passed, 1
skipped). A round-2 re-verification of the remediation was dispatched to the same
sub-agent.

### CI / PR review findings

_Pending PR creation._

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
