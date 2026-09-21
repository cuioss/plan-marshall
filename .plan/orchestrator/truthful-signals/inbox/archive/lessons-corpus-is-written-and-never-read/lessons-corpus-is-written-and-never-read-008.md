envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T19:26:37Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-28

# Finalize-step mode resolution keys on `--iteration`, so a real finalize dispatch degrades to user-invocable

`plan-retrospective/SKILL.md` § "Mode resolution" declares two rules that
disagree with each other:

1. Primary: "`--plan-id` provided, **invoked by `phase-6-finalize`** →
   finalize-step mode (emit `mark-step-done` tail)."
2. Heuristic: "when `--iteration` is present alongside `--plan-id`, treat as
   finalize-step mode; **otherwise user-invocable live mode**."

The mode carries a real consequence: only finalize-step mode emits the
`manage-status mark-step-done --phase 6-finalize --step
plan-marshall:plan-retrospective` handshake that the `phase_steps_complete`
invariant needs before the phase can transition.

**Observed this run.** `logs/work.log` records the dispatch verbatim:

```
[DISPATCH] (plan-marshall:phase-6-finalize) target=execution-context-level-3
  level=level-3 role=post-run-review workflow=plan-marshall:plan-retrospective
  plan_id=lessons-corpus-is-written-and-never-read
```

Unambiguously rule 1: invoked by `phase-6-finalize`. But the prompt body carried
no `--iteration`, so rule 2 classifies it **user-invocable** — and the workflow's
own Prohibited-actions block says "Never call `mark-step-done` in archived mode
**or user-invocable live mode**". A body that follows the documented heuristic
literally will skip the handshake on a genuine finalize dispatch and stall the
invariant.

The failure is silent in both directions: nothing in the prompt body announces
the mode, and the skipped handshake surfaces only later, as an incomplete
`phase_steps` map.

## Root cause

The mode is inferred from an *optional* forwarded field rather than declared. The
authoritative signal (who dispatched me) is available and already logged; the
proxy signal (`--iteration`) is not required by the input contract — its own row
says "Forwarded by `phase-6-finalize`", but nothing enforces the forward.

## Solution

Pick one and make it binding:

- **Preferred**: add an explicit `mode` (or `finalize_step: true`) prompt-body
  field that `phase-6-finalize` MUST forward, and have Step 1's contract
  validation reject a `phase-6-finalize`-sourced dispatch that omits it —
  refusing loudly, the way `pre-submission-self-review` refused its missing
  `candidates` field on this same run.
- **Or**: make `--iteration` a *required* field for the finalize-step dispatch
  and validate its presence, so its absence is an error rather than a silent
  mode flip.

Either way, the "otherwise user-invocable" default must stop being reachable from
a `phase-6-finalize` dispatch.

## Impact

Every orchestrated finalize run that dispatches `plan-retrospective` without
`--iteration` — including this one — is one literal reading away from leaving
`phase_steps["6-finalize"]["plan-marshall:plan-retrospective"]` unwritten. This
run emitted the handshake anyway, on the strength of the `[DISPATCH]` evidence
overriding the heuristic; that judgement call should not be load-bearing.
