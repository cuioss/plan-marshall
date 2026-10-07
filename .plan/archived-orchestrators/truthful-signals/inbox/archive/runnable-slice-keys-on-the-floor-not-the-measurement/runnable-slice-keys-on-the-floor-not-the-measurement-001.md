envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=landing
created=2026-07-29T04:54:17Z

## What landed

PLAN-89 (WS-01) — "Runnable-slice rule keys on the floor, not the measurement".
PR #1044 is OPEN (not yet merged; branch-cleanup has not run) on
`feature/runnable-slice-keys-on-the-floor-not-the-measurement`, HEAD `63d9a1a63`.

- `PYTEST_OUTER_FLOOR_SECONDS` lowered 600 -> 330 (330+30=360, under the 600 harness
  ceiling, still > pytest's 300s inner backstop).
- `execution_tier` re-keyed onto the MEASUREMENT: tier = `per_task` if
  (measured and not exceeds) else `orchestrator`. `_lookup_bash_timeout` now returns
  `tuple[int, bool]`; `_compute_execution_tier_fields(stamp, measured)` takes
  `measured` REQUIRED WITH NO DEFAULT.
- New `run_config.timeout_measured()` accessor (`timeout_get` could not distinguish
  unmeasured from measured).
- New third hint token `_HINT_UNMEASURED`, selected on the
  `(execution_tier, exceeds_bash_ceiling)` PAIR rather than `exceeds` alone.
- Fail-closed uniformly across all four engines: unmeasured => `orchestrator`.
- Two-sided floor invariant documented at all three declaration points plus a
  population-derived guard test parameterised over the engine list.

## Live proof

The runnable slice is restored: compile/quality-gate/module-tests/verify all moved
630/orchestrator -> 360/per_task and ran INLINE during this very finalize; coverage
(1897s) correctly stayed 1927/orchestrator.

## Residue for the epic

10 candidate lessons are riding as separate `candidate-lesson` messages in this same
drain batch (theme: confident-signal-hides-a-caveat). Also flagging: this plan's
execution-manifest step-params snapshot still carries the legacy `enabled_bots` key
(never migrated to `required_bots`/`optional_bots`), and two of three review bots
(sourcery, coderabbit) refused to review this PR (quota/window), so the 0-actionable
review count reflects absence of review, not validation.
