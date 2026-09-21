envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T12:59:09Z

component=plan-marshall:build-pyproject
category=anti-pattern
bundle=plan-marshall

# A 2-second incremental type-check green is a cache hit, not a verification result

## What happened

The local pre-push test-compile gate passed in **2-5 seconds** across several consecutive rounds.
CI, on the same tree, checked **660 files** and found **2 real type errors**.

The local runs were reading a stale mypy incremental cache. The gate was answering "nothing I
have cached changed" and the answer was being consumed as "the tree type-checks". After the
relevant edit was made, the local run reproduced the CI failure — so the tool was never broken;
the *duration* was the tell that it had not done the work.

## The signal that was available and ignored

**Implausible duration is a failure signal.** A whole-tree type check that returns in 2 seconds
has not checked the whole tree. The green was confident, fast, and repeated — three properties
that read as reassurance and are in fact the symptom.

This is the same shape as the routed-build false-green archetype: an outer status that is
structurally incapable of being anything but green, quoted as though it were a measurement.

## Rule

- **Calibrate every gate against a known-cost baseline.** If you know a full check touches N files,
  know roughly what that costs. A run an order of magnitude under baseline is a cache hit and must
  be re-run cold before its result is quoted.
- **Never treat an incremental type-check green as a pre-push gate result** without either a cold
  run or an explicit file-count in the output. Prefer a gate that reports *how much it checked*
  (`660 files`) over one that reports only pass/fail — a count makes the vacuous run self-evident.
- **When local and CI disagree, suspect the local cache first**, before suspecting an environment
  difference. The cheap discriminator is a cache-cleared local re-run, which reproduced the failure
  here on the first attempt.
- **A repeated green is not corroboration** when every repetition reads the same cache. N passes
  of a cached check is one cached answer returned N times.

## Fix

No code change shipped for this in `correct-review-scores-as-maximally-wrong` (PR #1078) — it was
worked around by editing and re-running. The durable fix is a gate-level one: make the pre-push
type-check report its checked-file count, or run it cold, so a cache hit cannot masquerade as a
verification.
