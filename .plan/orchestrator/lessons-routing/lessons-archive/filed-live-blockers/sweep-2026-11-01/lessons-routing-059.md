# The no-progress rule records a hand-back the workflow itself prescribes as `error`

Severity: **high (operator ruling, 2026-11-01 sweep)**. Bundle: `plan-marshall` (`phase-5-execute`).
Source: 2 lessons from the API-Sheriff checkout, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/API-Sheriff/`: `2026-10-12-16-007`, `2026-10-12-07-007`. Not re-verified at HEAD.

## Observed

- **`2026-10-12-16-007`** (plan-24, PR #430): several phase-5 hand-offs ended in a yield the workflow prescribes (control returns so the main context can do what only it can). The deterministic no-progress rule cannot tell that from a stalled hand-off and recorded `error`. Those reclassifications also count toward the script-failure signal that decides whether lessons capture runs, so a plan with no real failure can trigger it.
- **`2026-10-12-07-007`** (plan-25, PR #408): the `integration-tests` module build resolves to the orchestrator tier (about 1140 to 1160 s), so every task ended its hand-off after compiling. After TASK-1 and TASK-2 the second yield was reclassified as an error (`in_progress=1`, `completed_delta=0`, 536031 tokens). The operator settled one full module build per deliverable.

## Ask

Give the no-progress rule a way to recognise a prescribed yield (for example a declared return signal the workflow emits and the rule exempts). Consider detecting at planning time that a module's test build always exceeds the per-task limit and stamping the long build per deliverable.

Until then an `error` from the no-progress rule on a phase-5 hand-off is not evidence that the hand-off failed.
