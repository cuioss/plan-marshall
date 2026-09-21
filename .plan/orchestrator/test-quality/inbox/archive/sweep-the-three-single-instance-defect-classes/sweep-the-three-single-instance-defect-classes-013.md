envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:29:14Z

component=plan-marshall:phase-6-finalize
category=bug

# The lessons-capture Signal Gate hit the documented `qgate list` argparse rejection, inside the framework that documents it

At `2026-09-14T03:23:01Z`, while phase-6-finalize was evaluating the lessons-capture
Signal Gate for plan `sweep-the-three-single-instance-defect-classes`, this landed in the
work log:

```text
[ERROR] (plan-marshall:execute-script:2) script_failure
  notation=plan-marshall:manage-findings:manage-findings
  exit_code=2 failure_kind=argparse_rejection
  detail=Add the required flag(s) to
    `plan-marshall:manage-findings:manage-findings qgate list`: ['phase']
```

This is **recurrence signature #5** verbatim, from
`persona-plan-marshall-agent/standards/agent-behavior-rules.md` § "Never invent script
subcommands — recurrence signatures":

> *Missing required `--phase` … omitting the mandatory `--phase` on phase-scoped finding
> verbs. Example: `manage-findings qgate list --plan-id X` → canonical
> `manage-findings qgate list --plan-id X --phase {phase}` (`--phase` is required).*

The signature is documented, named, numbered, and has a plugin-doctor rule cluster aimed
at it — and the gate that decides whether lessons get captured tripped it anyway.

## Why this one matters more than an ordinary argparse slip

`exit_code: 2` means argparse rejected the call **before the script body ran**. The
Signal Gate sums pending Q-Gate findings across five phases; a rejected call for one
phase yields no findings for that phase. If the gate treats a failed call's absent output
as "zero pending findings for this phase", then:

- `signal_qgate_pending_count` is understated by whatever that phase held, and
- at the limit, all three signals read zero and lessons-capture is **skipped entirely** —
  the step recording `outcome=skipped --display-detail "no lesson-bearing signals"` over
  a population it never successfully queried.

That is the clean-zero failure mode this codebase has systematically abolished elsewhere
(`findings_store_state`, `store_resolution`, `inbox_state`, `plans_root_state`,
`scope_resolved`, `preference_admissibility_basis`). The Signal Gate is a counting
surface with the same obligation and, on this evidence, without the same discriminator.

In this run the forwarded counts were `qgate_pending=0`, `automated_review=1`,
`script_failure_clusters=0`. The gate dispatched on the automated-review signal, so the
skip did not occur here — the defect was masked by an unrelated non-zero signal, not
avoided.

## Solution

1. **Fix the call.** Supply `--phase {phase}` on every `manage-findings qgate list`
   invocation in the Signal Gate's per-phase loop.
2. **Make the gate's zero say which zero it is.** A signal count derived from calls that
   may fail must distinguish *queried and found none* from *the query was rejected*. Any
   non-zero-exit call in the loop should force the gate to treat the count as
   indeterminate and dispatch, rather than resolving it to zero and skipping — fail
   toward capturing a lesson, never toward silently dropping one.
3. **Cover it.** A test that exercises the gate with one phase's query failing, asserting
   the step is NOT skipped, would make this class unable to recur silently.

## Provenance and a caveat on how this was found

Plan `sweep-the-three-single-instance-defect-classes`, PR #1486 (merged).

This candidate is **outside the forwarded signal population** and is flagged as such:
the dispatcher forwarded `signal_script_failure_clusters_count: 0`, and that is not
contradicted — the failing call is timestamped `03:23:01`, after the gate scan that
produced the counts and before this step's dispatch at `03:23:29`, so the scan could not
have seen it. It surfaced while reading the work log to establish the provenance of
pre-existing inbox messages. It is emitted rather than dropped because suppressing an
observed in-run script failure on the strength of a count computed seconds earlier is
the same clean-zero reasoning the lesson is about.

## Note for the drain — expected overlap in this sender's queue

Messages `-001` through `-007` from this sender were written by the
`plan-marshall:plan-retrospective` step (03:21:37–03:21:57); `-008` through `-013` are
this `lessons-capture` step's. Both emitters draw on the same run, so some content
overlap between the two groups is expected and is left for orchestrator-side dedup —
per the contract, the plan transmits candidates and does not judge them.
