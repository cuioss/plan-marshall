envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:17Z

component=plan-marshall:phase-2-refine
category=improvement
bundle=plan-marshall

# An all-100 confidence score is a prompt to corroborate, not a score to defend

The refine gate flags a request whose six confidence dimensions (correctness,
completeness, consistency, non-duplication, ambiguity, module_mapping) all score
100 as suspicious by design. On this run the flag fired and the correct response
was not to argue the score down but to discharge the corroboration obligation
with first-party evidence.

Source record: Q-Gate finding `55ac8d`, phase `2-refine`, resolution `accepted`.

## Solution

Answer the all-100 flag by naming independently checkable evidence rather than by
restating confidence:

- Verify every OBSERVED code-reference claim against the live tree (4 of 4 valid
  here).
- Resolve every concrete affected file to a module via `architecture
  which-module` (8 of 8 resolved to `plan-marshall`).
- Check whether the request labels its own unverified assumptions — this one
  marked them `HYPOTHESIS` with explicit verify-at-outline markers instead of
  asserting them as fact.

A 100% that survives that check reflects a self-auditing source narrative. A 100%
that cannot produce the evidence is the defect the gate is looking for.

## Impact

Applies to every refine-phase run that trips the all-dimensions-maximal check.
The candidate is informational: it carries a discharge procedure, not a code fix.
The orchestrator should judge whether a procedure-shaped observation of this kind
belongs in the corpus at all, or whether it is already covered by the refine
gate's own documentation.
