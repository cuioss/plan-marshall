envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:27:54Z

## Finding: a routed build's outer status misreports in BOTH polarities

**Observed in**: main, during execution of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.

### What was observed

Two observations, opposite in sign, from the same outer-status surface:

1. **Failure reported as a different failure, with the duration erased.** An inner result
   of `status: timeout`, `exit_code: -1`, `duration: 345` surfaced at the outer layer as
   `error: execution_failed`, `duration_seconds: 0`. Both the failure *class* and the
   duration were lost — and a `duration_seconds: 0` on a build that actually ran for 345
   seconds is itself a false signal.
2. **Success reported as failure.** A genuinely green suite that ran for **474 seconds**
   was reported as `timeout`.

### Why it matters

The outer status is the field every caller routes on. When it is wrong in *one* direction
a caller can at least adopt a conservative reading; when it is wrong in **both**
directions there is no safe conservative reading available — neither green nor red at the
outer layer carries information, and the only trustworthy value is the inner result the
outer layer is supposed to be summarizing.

This confirms and generalizes the existing standing rule "never trust a routed build's
outer status": the rule was derived from the false-green polarity, and this observation
adds the false-red polarity. A detector built only against the known polarity would be a
population-derived detector built on half the population.

### Note on the duration signal

`duration_seconds: 0` paired with a real inner duration of 345s is an independently useful
detector input — an implausible duration is a failure signal in its own right, and here it
is *produced by* the misreport rather than merely correlated with it.

### Suggested shape of a fix (not implemented)

- Make the outer layer **forward** the inner `status`, `exit_code`, and `duration` rather
  than re-deriving them; a re-derivation that can disagree with the inner result is the
  defect.
- Where re-derivation is unavoidable, emit both values and let the disagreement be
  visible, rather than silently picking one.
