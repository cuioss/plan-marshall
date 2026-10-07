envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:12:25Z

component=plan-marshall:manage-status
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# mark-step-done accepts a head_at_completion SHA it never resolves

## Context

Twice in this plan's finalize chain a full 40-character SHA was written into
`mark-step-done --head-at-completion` from context rather than resolved from git. The
second occurrence came immediately after the correction for the first had been logged.
Both were caught by re-resolving with `git rev-parse` and re-stamping.

`head_at_completion` is not decorative. It is the anchor the next
`pre-submission-self-review` round consumes as `--since-ref`, so a wrong value does not
fail loudly — it silently redefines the diff the next round reviews. This run fired
`pre-submission-self-review` eight times (seven `failed`, one `done`), so the anchor was
consumed seven times.

## Root cause

Nothing on the write path checks that the value names an object. `manage-status
mark-step-done` stores the string it is handed. A fabricated 40-hex string is
shape-valid, renders identically to a real SHA everywhere the ledger is displayed, and
is distinguishable from a real one only by asking git.

The abbreviated form is safe in a way the full form is not, and that asymmetry is the
trap. A short SHA written from context is resolved by git at use time and fails loudly
when wrong. A full SHA is consumed verbatim, so it can be wrong while looking right.

## Proposed action

- Have `mark-step-done` validate `--head-at-completion` with
  `git rev-parse --verify {value}^{commit}` and REFUSE a value that does not resolve.
  This is a tool-layer fix in a component we own, on a flag with exactly one legal
  shape, and it converts a silent corruption into an argparse-class rejection.
- Apply the same guard to any other flag that carries a commit-ish into persisted plan
  state.

Agent-side rule, should the tool-layer guard not land: a full SHA is only ever produced
by `git rev-parse`. An abbreviated SHA may be written from context precisely because
git resolves it.

## Verification performed here

All six `head_at_completion` values persisted for this plan resolve:

```
git -C . log --no-walk 024ac6e28 dd55c6f8e 4f8e68aa1 cb38d5ae6 031e5293e 91bbe7470
```

returns six commits. The ledger is correct — but only because both fabrications were
noticed by hand and re-stamped. Nothing structural made that outcome the default, and
the two that were caught are not evidence about the ones that were not.

## Evidence

- `status.metadata.phase_steps["6-finalize"]` — six steps carry `head_at_completion`
- `pre-submission-self-review` `firing_count: 8`, `prior_firings[7]` all `failed`
- two in-run corrections, the second immediately following the first correction's log entry
