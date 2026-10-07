envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:24:45Z

## Our finalize cost record is counter-evidence to the paper's low-OpEx claim

Source: same Day 1 whitepaper (see message 001 for provenance). This message runs the other direction from
001–004: the outside document makes a claim, and our own measured data contradicts it.

### The paper's claim

Its economics section models vibe coding as low-CapEx/high-OpEx and agentic engineering as
high-CapEx/low-OpEx, asserting that under a well-designed harness "the marginal cost of shipping and
maintaining a feature drops dramatically". The stated mechanism is **first-pass success rate**: dense,
high-signal context raises the odds the agent gets it right the first time, avoiding the trial-and-error
loops that burn tokens.

### What our record shows

plan-marshall is the high-CapEx position, built. The marginal cost has not dropped:

- PLAN-TRUTH-089: the finalize gate consumed **81% of a 13.9M-token run** (~7× the anchor). Self-review
  fired 19 times and consumed **all 17** available loop-back iterations.
- PLAN-PR-046: finalize was **48.5%** of the run — larger than execute — at 6.77M tokens, 5.2× anchor.

The failure is not low first-pass success at *generation*. It is low first-pass success at
**verification**: the apparatus built to raise generation quality has itself become the dominant cost,
and in the 089 case it did not converge — it exhausted its iteration budget rather than reaching a fixed
point. (`done` there did not mean converged; that distinction is already recorded in the corpus.)

### The gap in the paper

It models the cost of generation under a good harness and is **silent on the cost of the harness's own
verification layer**. There is no term in its CapEx/OpEx framing for a verification loop with no fixed
point. Our data is not a deviation from its model to be corrected; it is a case its model does not cover.

One outside data point runs the same way and is properly sourced in the paper (endnote 10): METR,
February 2026, found experienced developers **19% slower** on certain tasks with AI assistance, the
overhead being verification, debugging and correction. That is the same shape at the individual scale.

### Why it belongs here

The epic's third done-condition is that the price of carrying an instruction becomes a number somebody
can read. This finding says the neighbouring number matters at least as much: the price of *checking*
an instruction held. A measured-instruction-substrate that adds verification cost without bounding it
reproduces the 089 outcome at corpus scale.

### Status

Our figures are measured and already in the corpus; the paper's counter-claim is asserted without data.
Filed so that whatever WS-01 builds carries a cost ceiling by design rather than by discovery.
