envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T22:43:26Z

component=plan-marshall:plan-retrospective
category=bug
title=check-routing-decisions posture_cutoff regex no longer matches the emitter line it claims to copy verbatim - false mis_prune on every standard-posture plan

# A consumer regex that claims to be copied verbatim from its producer, and is not

## Observation — a live false FAIL in this run's own report

`check-routing-decisions.py` emitted:

```
mis_prune_checks[2]{check,status,predicate,removal_cause,detail}:
  "mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,
    sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code
```

That verdict is **false**. `sonar-roundtrip` was never pruned by `no_code_delta`. The
plan's own decision log says why it went:

```
[STATUS] lane_resolution — dropped sonar-roundtrip from phase_6.steps
  (execution_profile=standard): effective tier full exceeds the standard posture cutoff
```

A **posture-tier drop**, not a predicate drop. The script has an enumeration built
precisely to catch that — `_REMOVAL_CAUSE_PATTERNS` — whose `posture_cutoff` member is:

```python
r'lane_resolution\s+—\s+execution_profile=[^,]+,\s+dropped\s+(?P<steps>.+?)'
r'\s+from\s+phase_6\.steps\s+\(tier above posture cutoff\)'
```

The emitter's real shape — and the shape `manage-execution-manifest/standards/decision-rules.md`
line 418 documents as the contract — is:

```
lane_resolution — dropped {step} from phase_6.steps (execution_profile={posture}): {reason}
```

Different field order, different trailing clause. The regex cannot match. `removal_cause`
falls through to `predicate_evaluated`, the `no_code_delta` predicate is re-evaluated
against a footprint containing `.py` files, and the check FAILs.

## Why this one is worth recording

The comment above the pattern tuple states:

> Each line shape is **copied verbatim** from `manage-execution-manifest/standards/decision-rules.md`
> (the emitter contract).

and the module docstring states that a step matched by one of these mechanisms is SKIPPED
because *"its predicate never fired, so its absence proves nothing about the footprint"*.
So the guard **documents the exact defect it just produced**, and asserts a
verbatim-copy property that is false on disk. Nothing observes the copy.

This is the vacuous-authority / defending-documentation shape again, but with a sharper
edge than usual: the drift is not in prose describing behaviour, it is in a **regex whose
correctness is asserted by a comment and checked by nobody**. A producer/consumer pair
where the consumer parses the producer's free-text log line is a contract with no
compile-time and no test-time coupling.

## Rule

- **A consumer that parses a producer's log line must be pinned by a test that feeds it a
  line the producer actually emits** — generated from the producer, not hand-written into
  the test. A hand-written fixture drifts in lock-step with the wrong copy.
- **"Copied verbatim from X" is an assertion, not a guarantee.** Where a doc and a regex
  claim to agree, something must fail when they stop agreeing. Prefer: emit the line
  through a shared formatter both sides import, so the shape has exactly one home and the
  consumer parses what the producer produced.
- Scope: this affects **every standard-posture plan**, because `standard` always drops
  `sonar-roundtrip` by posture. Every such retrospective since the emitter's line shape
  changed has been reporting a false `mis_prune` — the highest-severity output this aspect
  produces, per its own docstring.
- Re-derive the OTHER three members of `_REMOVAL_CAUSE_PATTERNS`
  (`unresolved_ask_provider_drop`, `simplify_inactive`, `ceremony_finalize_selection`)
  against the live emitter in the same pass. One member drifted; the sample of one says
  nothing about the other three — and the tuple's own re-derivation obligation comment
  names exactly this risk.

## Impact

`plan-marshall:plan-retrospective:check-routing-decisions`, the `mis_prune` verdict in
every routing-decisions fragment, and the `manage-execution-manifest` decision-log emitter
contract in `standards/decision-rules.md`.
