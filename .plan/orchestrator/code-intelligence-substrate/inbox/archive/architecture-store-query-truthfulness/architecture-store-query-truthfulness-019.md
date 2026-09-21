envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:52:49Z

component=plan-marshall:phase-4-plan
category=improvement

# The module-mapping validator has no shape for a cross-bundle drift-rule test

Source: Q-Gate finding 2fd432 (4-plan, resolution=accepted).

D7's module_testing task declared a test under module pm-plugin-development while its
sibling implementation task wrote docs under module plan-marshall. No documented
test-to-impl mapping entry covers that cross-module pair, so the validator flagged it.

The pairing is architecturally correct: the test verifies a cross-bundle
documentation-drift rule by re-running the plugin-doctor drift check against the corpus
(the deliverable's own criterion is that the rule's live finding count AND its
denominator are both published). Same-module unit coverage is not the applicable shape —
the rule inherently spans plan-marshall's docs and pm-plugin-development's code.

## Solution

The validator has one legitimate cross-module case it cannot express. Either give the
mapping a declared "cross-bundle linter verification" relationship, or require the
Design notes to state the relationship explicitly so the acceptance is recorded at
plan time instead of re-argued at Q-Gate time.

## Impact

Recurs for every plan that fixes documentation which a linter in another bundle
polices.
