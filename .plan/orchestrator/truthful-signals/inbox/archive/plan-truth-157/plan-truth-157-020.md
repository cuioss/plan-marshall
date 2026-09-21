envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:01Z

component=plan-marshall:plan-orchestrator
category=bug
bundle=plan-marshall

# Derive a return shape's cardinality from the iteration contract, and cross-check the siblings in the same group

`analyze.md` declared the landing-report drafting return as
`landing_report{plan,body}` — a SINGULAR object with no cardinality marker. Two
lines above, the same document states the drafting envelope is "ONE envelope that
iterates internally over the drain's messages, never one envelope per message", and
Step 3's routing table sends EVERY `kind: landing` message to Step 4, whose item 1
writes one `landings/PLAN-NN.md` per landing.

Concrete failing input: a drain carrying two `kind: landing` messages needs two
landing-report bodies, and the declared shape holds one. The Output block's
`drained[D]` rows and `messages_scanned` already admit multiple landings per drain,
so the document contradicted itself.

The two sibling drafting returns in the SAME bullet group were correctly cardinal —
`proposals[N]{message,disposition,rationale}` and `spec_drafts[M]{plan_slug,body}` —
which is what identifies this one as the drifted member.

Source record: Q-Gate finding `662b26`, phase `6-finalize`, defect_class
`contract_drift`, resolution `fixed` in commit `04f12a22b` (to
`landing_report[L]{plan,body}`, a fresh cardinality letter per the N/M convention).

## Solution

- Read cardinality off the ITERATION contract, not off the intuition that one step
  produces one thing. A one-envelope-iterates-internally contract makes every
  return in that envelope potentially plural.
- When a bullet group declares several returns, cross-check them against each
  other. A group where two of three members carry cardinality markers and one does
  not is a drift signal available at zero cost.
- Allocate a FRESH cardinality letter rather than reusing a sibling's, so the
  independence of the collections stays visible.

## Impact

Applies to every structured return declaration in a dispatch contract. The
sibling-disagreement heuristic is the cheap, generalizable half.
