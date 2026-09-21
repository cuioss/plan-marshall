envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:45Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development

# A matched positive control drawn from the vocabulary under test cannot fail on the dimension it guards

`_AFFIRMATIVE_RE` covered only `(may|can|writes|write|calls|invokes|performs)`, and
`_leaf_write_grants` required it to match. So
`test_no_dispatch_doc_grants_a_leaf_a_write_path` — an ABSENCE claim over every
derived dispatch doc — could see a grant only when the grant happened to be phrased
with one of those seven verbs.

Negative example that should be caught and was not: "The leaf appends the drafted
row via orchestrator queue." It names a leaf, names the forbidden target, carries
no negation, and is an unambiguous grant — yet matches no affirmative token, so
`_leaf_write_grants` returned `[]` and the assertion passed green. The same holds
for "is responsible for writing", "records", "authors", "sets", "mutates", "shall
write".

The asymmetry is load-bearing: `_NEGATION_RE` carried 13 tokens with a recorded
rationale while the affirmative side carried 7. And every fixture in
`test_a_leaf_granted_a_write_path_is_detected` was built from those SAME seven
tokens ("may call", "writes", "calls", "invokes") — so the matched positive control
was drawn from the very vocabulary it would need to expose, and could not fail on
this dimension. A missed grant produces no output at all, unlike a
population-narrowing regex which at least shrinks a visible count.

Source record: Q-Gate finding `0b51ec`, phase `6-finalize`, defect_class
`regex_overfit`, resolution `fixed` in commit `72738c8ec`.

## Solution

- Draw at least one control fixture's vocabulary from OUTSIDE the token set under
  test. A control built from the pattern's own alternations tests the regex against
  itself.
- Prefer inverting the detector where the safe default allows it: treat
  leaf + forbidden target + no negation as a grant, and require an explicit
  PROHIBITION token to clear it. An absence claim should fail open, not closed.
- When two sides of one guard have asymmetric vocabularies (13 vs 7), treat the
  asymmetry itself as the finding.

## Impact

Generalizes to every set-guarding detector whose positive fixtures are authored
alongside its pattern. See also the follow-on candidate: the FIX for this finding
introduced a fresh defect of the same class.
