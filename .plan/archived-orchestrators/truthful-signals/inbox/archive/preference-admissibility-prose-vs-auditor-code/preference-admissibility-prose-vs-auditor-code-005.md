envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:10:44Z

component=plan-marshall:manage-locks
category=bug
bundle=plan-marshall

# A read verb that ACCEPTS a scoping flag and ignores it answers confidently about the wrong scope

## Rule

When a write verb scopes its state by a compound key and its sibling read verb accepts the same
scoping flag, the read MUST apply it. A flag that is declared, documented, and silently unused is
worse than an absent flag: an absent flag makes the caller supply the scope some other way, while an
accepted-and-ignored flag makes the caller believe it already did.

## Observation

`merge_lock.py rate-window` declares `--pr-number` on the SHARED subparser, so all three actions
accept it, with help text *"PR the recovery attempts are counted against (required for claim)"*.

- `claim` scopes the recursion cap per `(bot_kind, pr_number)` — the documented contract is a cap of
  `_RECOVERY_ATTEMPT_CAP` "recovery events **per bot per PR**".
- `_run_rate_window_check` accepts `--pr-number` and **ignores it**, returning `record['attempts']`
  unconditionally — i.e. per `bot_kind` only.

Observed live in PLAN `preference-admissibility-prose-vs-auditor-code`: a check scoped to
`--pr-number 1398` returned **`2/2, remaining 0`** read out of a record naming **PR 1399**. The true
attempt count for PR 1398 was **0**. The plan believed its own recovery budget was exhausted when it
had never used any of it.

The module docstring compounds it: it says the cap is enforced "per bot per PR" and that
`check` "is a pure read", without disclosing that the read's scope is narrower than the cap's. Both
statements are individually true and jointly misleading — the epic's confident-signal theme exactly.

## Relationship to the already-filed finding

The single instance is already transferred to the **`review-apparatus`** epic inbox as a finding.
This message is the **generalisable shape**, which is distinct from that instance and belongs to a
different epic:

> A parameter accepted by a handler that never references it is a silent scope lie. It is
> mechanically detectable — an argparse `dest` with no read in its handler's body — and does not
> depend on this call site.

The orchestrator should treat the two as one root cause with two dispositions (fix the instance in
`review-apparatus`; consider the detector in `truthful-signals`), not as two independent items.

## How to apply

- **Immediate**: either honour `--pr-number` in the rate-window check, or move it off the shared
  parser onto `claim` alone so `check` rejects it. Silently accepting it is the one option to
  exclude. Whichever is chosen, correct the docstring's "per bot per PR" claim to match.
- **Generalisable detector**: for each argparse `dest` declared on a subparser, assert the handler
  body references it. A declared-but-unreferenced `dest` is a finding.
- **Reviewer side**: when a flag is documented "required for X", check what the *other* actions
  sharing that parser do with it. "Required for X" describes X, and says nothing about Y and Z.
- **Caller side**: a scoped read returning a surprising count is a scope question before it is a
  state question. Confirm the record the answer came from names the scope you asked about.
