envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:56:38Z

component=plan-marshall:manage-execution-manifest
category=bug
proposed_title=A manifest-declared verification step went unrun with no structural record of the omission

# A manifest-declared verification step went unrun with no structural record of the omission

## Status

**Observed during `lane-router-reads-the-wrong-body`, NOT fixed.** Distinct from the marshalld `executor_mismatch` report filed as `lane-router-reads-the-wrong-body-010`: that message covers *why* the build could not run. This one covers the fact that **nothing in the system noticed it did not**.

## The observation

`execution.toon` declares three phase-5 verification steps:

```toon
phase_5:
  verification_steps[3]:
    - "verify:quality-gate"
    - "verify:module-tests"
    - "verify:coverage"
```

`execution_log` records exactly two:

```toon
"verify:quality-gate",5-execute,executed,...
"verify:module-tests",5-execute,executed,...
```

`verify:coverage` has **no row of any kind** — not `executed`, not `skipped`, not `failed`. The plan then transitioned 5-execute → 6-finalize and ran to a merged PR.

The only trace of the omission anywhere in plan state is a hand-authored narrative line a human chose to write:

> `[WARNING] verify:coverage NOT RUN - marshalld refused submit with executor_mismatch ... Operator chose to skip the coverage gate and proceed to finalize.`

That line is excellent practice. It is also **the sole reason this is knowable**, and it is prose in a log rather than state a gate can read.

## Why this is the epic's archetype

Everything structural about this run reports success. `phases[5-execute]=done`. The manifest is valid. The transition invariants all passed with `invariants_missing: []`. A downstream consumer — the finalize phase, a future audit, `check-manifest-consistency` — reads a plan that declared three verification steps and completed normally, and has no signal that one third of its declared verification never happened. **The declaration and the execution record disagree, and only the declaration is load-bearing for anyone reading later.**

Note the asymmetry: `check-manifest-consistency` ran in this very retrospective and returned `passed: 2, failed: 0, findings: 0`. It cross-checks manifest assumptions against the diff. It does not cross-check declared verification steps against executed ones.

## Contributing factor (worth recording separately)

`verify:coverage` was stamped `execution_tier: orchestrator` at compose and re-confirmed live (`bash_timeout_seconds=1387, exceeds_bash_ceiling=true`). The leaf correctly refused to run it and yielded. The orchestrator then could not run it either (marshalld refusal + the 600s Bash ceiling). **An orchestrator-tier step has no fallback when the orchestrator's own two execution channels are both unavailable**, and the resulting state is indistinguishable from "the step was never needed".

## Proposed action

1. Add a deterministic verb — `manage-execution-manifest verification-coverage --plan-id X` — that diffs `phase_5.verification_steps` against the `execution_log` `step_id` set and returns the unrun remainder.
2. Make the 5-execute → 6-finalize transition consult it. A non-empty unrun set must produce either a recorded `outcome=skipped` row with a reason, or a blocked transition. Silence must stop being a legal outcome.
3. Extend `check-manifest-consistency` with a `declared_vs_executed_verification` check so the retrospective catches this even when the transition gate is bypassed.
4. Where an operator deliberately skips a declared gate, that decision belongs in `execution_log` as `outcome=skipped, reason=...`, not only in `decision.log` prose.

## Evidence

- `execution.toon` — `phase_5.verification_steps[3]` vs `execution_log` (2 phase-5 rows)
- `logs/decision.log` 08:13:31Z (leaf yield) and 08:39:14Z (`verify:coverage NOT RUN`)
- `fragment-manifest-decisions.toon` — `summary: passed 2, failed 0, findings 0`
- `fragment-invariants.toon` — `5-execute invariants_missing: []`
