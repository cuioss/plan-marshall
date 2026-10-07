envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T22:45:33Z

component=plan-marshall:phase-6-finalize
category=bug
title=A finalize step recorded outcome=done with zero [STEP] log lines - the handshake and the log emission are independent obligations

# `mark-step-done` and `[STEP] Completed` can disagree, and nothing notices

## Observation

`default:finalize-step-preference-emitter` executed in `PLAN-CIS-028` and recorded a full
terminal outcome:

```
finalize-step-preference-emitter:
  outcome: done
  display_detail: "1 pattern promoted, owed hint to epic inbox"
```

It also demonstrably did its work — inbox message `…-008.md` was written at `21:57:41`.

But `work.log` contains **no** `[STEP] Executing step: default:finalize-step-preference-emitter`
and **no** `[STEP] Completed step: …`. The two adjacent lines are consecutive:

```
21:56:27  [STEP] Completed step: default:lessons-capture
21:57:58  [STEP] Executing step: default:branch-cleanup
```

The absent `[DISPATCH]` line is **correct** — `dispatch-inline-split.md` classifies this
step as inline, so it is owed none. The absent `[STEP]` pair is not: every other inline
step in this run (`push`, `ci-verify`, `architecture-refresh`, `branch-cleanup`,
`project:finalize-step-era-stamp-fill`) emitted both.

## Why it matters beyond one missing line

The `phase_steps_complete` invariant is satisfied by the `mark-step-done` handshake alone.
The `[STEP]` emission is a separate instruction in workflow prose. So a step can be
**fully compliant with the invariant while leaving no trace in the operational log** — and
the two records are exactly the pair a retrospective, an audit, or a debugging operator
cross-checks against each other. The `execution-context-dispatch-audit` aspect's
inverse-coverage half depends on that cross-check; here it had to fall back on `status.json`
to establish that the step ran at all.

The failure is invisible at the site: nothing reads back the log to confirm the emission,
so the omission is discoverable only by someone counting steps in two places.

## Rule

- **Fuse the emission to the handshake.** `mark-step-done` already receives `--step`,
  `--phase` and `--outcome`; it can emit the `[STEP] Completed step: {step}` line itself.
  A prose instruction to log, sitting beside a script call that already knows everything the
  line needs, is a duplication that can only ever drift in one direction — toward silence.
- **A record that satisfies an invariant is not the same as a record that is observable.**
  Two independent obligations describing one event will disagree; the one nobody checks is
  the one that goes missing.
- Generalises to the peer pair: an outcome record that omits `head_at_completion` is
  likewise unverifiable on re-entry. This run paid a full re-dispatch of
  `project:finalize-step-lessons-housekeeping` at `17:10` for exactly that
  (*"Prior verdict UNVERIFIED — done record carried no `head_at_completion`"*). Same shape:
  a terminal record that is well-formed enough to pass and thin enough to be useless.

## Impact

`plan-marshall:phase-6-finalize` (Execute Step Pipeline `[STEP]` emission),
`plan-marshall:manage-status:mark-step-done`, and the
`execution-context-dispatch-audit` retrospective aspect that consumes the pair.
