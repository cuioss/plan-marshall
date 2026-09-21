envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:07Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
bundle=pm-plugin-development

# A control that transcribes a SUBSET of the live constant disagrees with it in BOTH directions — assert with the constant itself

The control added at `test_orchestrator_dispatch_workflow_pin.py:724` declared a
local `sentence_scoped` pattern transcribing a 6-token SUBSET of the shipped
14-token `_NEGATION_RE`, which also carries bars, barred, prohibited, prohibits,
forbidden, forbids, without and outside. The boundary therefore disagreed with the
vocabulary it stood in for in both directions — and this is the exact vacuity its own
assertion message claimed to prevent:

- **False green**: remove or rename the token `not` from `_NEGATION_RE` and the
  fixture phrase "may not" stops being a negation for the real scan, so the
  superseded sentence-scoped code would have found this grant too and the control no
  longer witnesses clause-scoping at all — yet `sentence_scoped` still matches `not`
  and the assertion stays green.
- **False red**: rephrase the fixture's second clause as "touching epic.md directly
  is prohibited" and the live scan still suppresses that clause on "prohibited", so
  the fixture remains a valid clause-scoping witness while the assertion fails
  against it.

Source record: Q-Gate finding `5a3891`, phase `6-finalize`, defect_class
`regex_overfit`, resolution `fixed` in commit `d8eeb2bd6`.

## Solution

Assert with `_NEGATION_RE` itself. The discriminator that decides whether a
transcription is legitimate is WHICH HALF is historical:

- Only the SCOPE was historical here, while the VOCABULARY is live — so the
  vocabulary must be read from the live constant.
- The sibling superseded pattern at line 677 IS justified, because it reproduces a
  narrow affirmative pattern that no longer exists in the module, so there is no live
  constant to read.

Rule: a test may transcribe a pattern only when the thing it reproduces is absent
from the module. If any part of it is still live, reference the live definition and
transcribe only the difference.

## Impact

A control whose job is to witness a historical fix is itself a claim about current
behaviour, and it inherits every drift risk of a duplicated constant. This finding
arrived in a LATER round than the fix it was guarding, so it also demonstrates that
newly-added controls need the same review as newly-added production patterns.
