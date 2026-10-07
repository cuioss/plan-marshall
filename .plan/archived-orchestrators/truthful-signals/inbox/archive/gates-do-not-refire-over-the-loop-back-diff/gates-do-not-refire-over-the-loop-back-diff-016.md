envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:49:19Z

component=plan-marshall:phase-6-finalize
category=bug

# The head-dependent re-fire worked and left no audit trail — only a stamp timestamp betrays it

## Observation

PLAN-TRUTH-001 built the derived head-dependent step set so a gate whose verdict depends on HEAD cannot certify a diff it never examined. **The mechanism fired during the plan's own finalize run.** It is also invisible in both logs.

**The re-fire is real.** `pre-push-quality-gate` is on the derived head-dependent set. Its records:

| Signal | Value |
|--------|-------|
| `[STEP] Executing step: default:pre-push-quality-gate` | 16:04:27Z — one occurrence |
| `record-step pre-push-quality-gate outcome=executed` | 16:09:09Z — one occurrence |
| `phase_steps[...].head_at_completion` | `3dcfab234e45096ba0e8734777031c462429e246` |
| commit time of `3dcfab` | **17:26:46Z** |

The recorded HEAD postdates the step's only logged execution by **77 minutes**. `3dcfab` is `finalize-step-simplify`'s own commit ("drop tautological head-SHA assertion in loop-back test"), created at 17:26:46Z. The build-server job cluster at 17:27:29Z–17:42:17Z sits between that commit and the push barrier at 17:44:18Z.

So the sequence is exactly the one the plan was built for: a `mutates_source` step advanced HEAD after a head-dependent gate had already passed, and the gate re-fired over the new HEAD before the push. **The fix caught its own author's later commit.**

**Nothing recorded it.** The re-fire emitted no second `[STEP]` line, no second `record-step` row, no decision entry. The only reconstructible evidence is the arithmetic above — comparing a git commit timestamp against a log timestamp. A reader of either log alone would conclude `pre-push-quality-gate` ran once, at 16:04, and passed against whatever HEAD was current then.

**The same emission gap is broader.** Three of the 17 steps that reached a terminal outcome emitted no `[STEP] Executing step:` marker at all:

- `ci-verify` — the green pass-through
- `lessons-capture` — `--role post-run-review`
- `plan-marshall:plan-retrospective` — `--role post-run-review`

Marker coverage is 14/17 (82%), and the omissions are shaped rather than random: the green early-return path and the `post-run-review` role pair.

## Root cause

`[STEP]` emission and `record-step` are bound to the *first* entry into a step's execute branch, not to each execution of it. A re-entry driven by the head-dependence comparison takes a different path — the comparison decides to re-run and re-stamps `head_at_completion` — without passing back through the emission site.

The result is a gate that is correct and unauditable. For an epic about truthful signals this is the inverse of the usual failure: the verdict is now honest, but there is no record proving it was recomputed. A future reader cannot distinguish "re-fired and passed" from "stale green retained" — which is the exact distinction the plan set out to make legible.

## Proposed action

1. Bind `[STEP]` emission and `record-step` to each *execution* of a step, not to the first entry. A head-dependence re-fire must produce its own pair.
2. Emit an explicit decision entry when the head-dependence comparison fires, naming the step, the stale HEAD, the current HEAD, and the verdict (`re-fire` / `retain`). Today the comparison is silent in both outcomes, so a *retained* green is equally unauditable — and that is the failure mode the plan exists to prevent.
3. Close the three `[STEP]` marker gaps. `ci-verify`'s green pass-through and the `post-run-review` role pair should announce themselves like every other step; a step that runs unannounced is indistinguishable from one that was skipped.
4. Consider asserting the pairing in the retrospective: for every step carrying `head_at_completion`, the stamp's commit time must not postdate the step's last logged execution. That inequality is the mechanical detector for this whole class, and it is what found this instance.

## Evidence

- aspect: logging_gap_analysis — `refire_audit_trail.lag_minutes: 77`
- `status.metadata.phase_steps["6-finalize"]["pre-push-quality-gate"].head_at_completion` = `3dcfab234e...`
- `git log -1 3dcfab234e` → `2026-08-01 19:26:46 +0200` (17:26:46Z), subject `chore(simplify): drop tautological head-SHA assertion in loop-back test`
- `logs/work.log:200` — the single `[STEP]` line at 16:04:27Z; `logs/decision.log` — the single `record-step` row at 16:09:09Z
- `logs/work.log:260-276` — build-server jobs 17:27:29Z–17:42:17Z, immediately before `[STEP] default:push` at 17:44:18Z
- aspect: logging_gap_analysis — `step_marker_coverage: 14/17`, `missing_step_markers: [ci-verify, lessons-capture, plan-marshall:plan-retrospective]`
