envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T15:03:10Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-08-02
bundle=plan-marshall

# Read the recorded removal cause before re-evaluating a prune predicate

`check-routing-decisions` reported a mis-prune that did not happen, using inputs it was already
carrying that disproved it.

## Context

The aspect emitted:

```
mis_prune:sonar-roundtrip,fail,no_code_delta,predicate_evaluated,
  sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
```

The realized footprint **did** touch production code (`_cmd_client_query.py`,
`extension_base.py`), so the predicate re-evaluation is arithmetically correct. But
`sonar-roundtrip` was never removed by the `no_code_delta` predicate. The decision log records the
actual cause verbatim:

```
[STATUS] lane_resolution — dropped sonar-roundtrip from phase_6.steps
  (execution_profile=standard): effective tier full exceeds the standard posture cutoff
```

The step was removed by the **operator-configured posture**, not by a footprint predicate.
`execution_profile=standard` prunes every `lane: full` element by design; dropping
`sonar-roundtrip` is the configuration working, not a routing defect.

The disproving fact was **already inside the aspect's own fragment**. `check-routing-decisions`
emits `recorded_lane_decisions[4]`, and entry `9e1b0f` in that very list is the posture-cutoff
record. The aspect loaded the contradicting evidence, rendered it, and did not consult it.

## Precision, not just noise

Two sibling steps were dropped by the same posture pass in the same run —
`finalize-step-security-audit` (`5c142b`, tier-full cutoff) and `adr-propose` (`67c383`, explicit
`off` override) — and **neither was flagged**. So the check does not flag posture drops in general;
it flags exactly those posture drops that happen to have a `prunable_when` predicate the footprint
refutes. That is an arbitrary population, which makes the finding neither reliably present nor
reliably absent.

## Root cause

The check re-evaluates **every** absent prunable step's `prunable_when` predicate unconditionally,
without first asking *why* the step is absent. A step removed for reason X gets its predicate for
reason Y evaluated anyway, and any predicate the realized footprint refutes becomes a reported
mis-prune.

## Proposed action

Branch on the recorded removal cause before re-evaluating:

1. Parse the `lane_resolution` decision-log entries the aspect already loads into
   `recorded_lane_decisions`.
2. Re-evaluate `prunable_when` **only** when the recorded removal was predicate-driven.
3. Report a posture-cutoff or explicit-`off` removal as **intentional** — surface it in the
   fragment as a configuration outcome, with no mis-prune verdict.

The fix requires no new input; it is a consumption change over data the aspect already reads.

## Secondary note (not this lesson's fix)

Independent of the false positive: this plan was a `bug_fix` touching production code in
`manage-architecture` that shipped without a Sonar roundtrip, because `execution_profile=standard`
prunes it. That is the designed behaviour of the standard posture and is recorded here as an
observation for the operator, not as a defect.

## Evidence

- aspect `routing_decisions` — `mis_prune:sonar-roundtrip,fail,no_code_delta,predicate_evaluated`
- aspect `routing_decisions` `recorded_lane_decisions[1]` — the same fragment carries the contradicting entry `9e1b0f`
- decision.log `9e1b0f` — posture-cutoff drop of `sonar-roundtrip`
- decision.log `5c142b`, `67c383` — two sibling posture/override drops the check did **not** flag
- `execution.toon` — `execution_profile: standard`; `sonar-roundtrip` absent from `phase_6.steps`
