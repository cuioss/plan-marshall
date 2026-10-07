envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T13:59:13Z

component=plan-marshall:manage-architecture
category=anti-pattern
created=2026-08-02
bundle=plan-marshall

# A precedence branch that discards a producer's output must say so on that producer's report

The graph merge implements a declared-wins precedence: when a module carries a declaration, the
declaration replaces the resolver-derived edges. That overwrite was **silent**. The consequence
is the exact confident-signal-hides-a-caveat shape:

- The resolver report said `markdown,24,ok` · `maven,0,ok` · `python,5,ok` — 29 edges,
  every resolver healthy.
- The merged graph said `edge_count: 0`.
- **Both statements were true, and nothing in either surface referenced the other.**

An operator reading the resolver report has no way to learn that the consumer threw the work
away, and an operator reading the empty graph has no way to learn that 29 edges existed
upstream. The discard is invisible from both ends, so the defect survived a prior plan
(PLAN-CIS-003 / #1074) that specifically set out to prove the graph non-empty.

## Solution

Whenever a merge/precedence stage discards one input in favour of another, write the
suppression back onto the **losing producer's own report** — not only into the winner's output
and not only into a log. Here: a declaration that actually discards derived edges appends a
`declared:`-prefixed suppression note to the losing resolver's report entry (ADR-014).

Two properties make this work and are the reusable part:

1. **The note lands where the *producer's* consumer already looks.** A note in the merged
   output would be read by people already looking at the empty result; the person who needs it
   is the one reading `ok, 24 edges`.
2. **The note is emitted only on an actual discard**, not on every declared module — otherwise
   it becomes noise and stops being evidence.

## Impact

Applies to every precedence, override, fallback, or dedup stage in the substrate — anywhere one
source silently wins over another. Recognition signature: two adjacent surfaces both report
success with mutually incompatible quantities, and no third surface reconciles them. A
disagreement that no artifact records is a disagreement no test can catch.
