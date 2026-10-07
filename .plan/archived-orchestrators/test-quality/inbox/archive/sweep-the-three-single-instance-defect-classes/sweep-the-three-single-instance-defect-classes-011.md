envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:27:33Z

component=plan-marshall:tools-integration-ci
category=anti-pattern

# A comment naming a derivation's source is an unchecked claim, and it drifted from the code beside it

In `test/plan-marshall/tools-integration-ci/test_envelope_contract_plan_id_placement.py:92`
a comment and an assertion message both stated that `POST_VERB_SUBCOMMANDS` is derived
from `_CONTRACT_DOC`. It is not — it comes from `_build_full_parser()` via
`_derive_populations`, and `_CONTRACT_DOC` is read only by `_plan_id_cell`, which takes
no part in that derivation. No document-reading mechanism for this population exists in
the file at all.

The prose was not merely imprecise; it named a source the code never consults, and the
assertion **message** repeated the claim — so a future failure of this test would have
pointed its reader at the wrong file.

## Impact

This is the failure the reviewer's own path instruction names: *"Prose, a code comment,
or a summary table is not a mechanism."* A comment asserting provenance carries the
authority of a contract while being enforced by nothing. Two concrete costs:

- A reader trusting the comment believes the test is document-derived and concludes the
  contract doc is covered by CI. It is not.
- An assertion message that names the wrong source sends the next debugger to the wrong
  place, at the moment they are least able to tell.

The class is broader than comments: any prose that *claims a derivation* — a docstring,
a summary table, a README sentence, an assertion message — is a source-of-truth claim
with no enforcement behind it.

## Solution

1. When a comment names where a population comes from, name the **symbol** the code
   actually calls (`_build_full_parser()`), not the conceptual source you had in mind.
2. Treat an assertion message as part of the contract: it is read only on failure, when
   it is trusted most and checked least.
3. Where the claimed source is the *right* source and the code is what is wrong, fix the
   code — the choice between "correct the prose" and "implement the claimed derivation"
   is a real fork, and it must be made deliberately rather than by whichever is cheaper.
   Here the parser tree genuinely was the right source, so only the prose was wrong.
4. Prefer deriving the prose: where a test's population source can be named by the
   symbol itself in the failure message (`f'derived from {_build_full_parser.__name__}'`),
   the claim cannot drift.

## Provenance

Plan `sweep-the-three-single-instance-defect-classes`, PR #1486 (merged). Finding
`f18e9e` (`pr-comment`, `resolution=fixed`),
`test/plan-marshall/tools-integration-ci/test_envelope_contract_plan_id_placement.py:92`.
Reviewer: coderabbitai. Remediated by TASK-011 (prose corrected to name the parser tree).
