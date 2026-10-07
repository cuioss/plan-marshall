envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:59:15Z

# Candidate lesson: a nine-member universal consumer claim refuted by one of its own members

- source_signal: qgate / 6-finalize
- record_id: a9de78
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:77
- resolution: fixed (claim narrowed); residue carried forward as PR finding 44e446 + TASK-025

## What happened

A new section closed with "each has a live consumer that reads it ... via `extension_discovery._read_frontmatter_fields`" over nine named fields. A complete-coverage content sweep (5462 files, 0 unreadable, 0 elided, not truncated) showed `advances_main_via_rebase` appears in NO Python file at all — its only reader is an agent reading the step doc. The count and the membership were right; the universal was wrong.

This is the assert-completeness-instead-of-deriving-it archetype: a nine-member universal stated in one clause instead of enumerated per member. Note the residue: the DOCUMENT's claim was narrowed here, but the sibling TEST still encoded the same refuted premise and had to be caught later by a review bot.

## Candidate rule

Any "each of these N has X" claim must be derived per member, not asserted over the set. And when a refuted premise is corrected in a document, check whether a TEST encodes the same premise — correcting one half leaves a live guard asserting the refuted thing.
