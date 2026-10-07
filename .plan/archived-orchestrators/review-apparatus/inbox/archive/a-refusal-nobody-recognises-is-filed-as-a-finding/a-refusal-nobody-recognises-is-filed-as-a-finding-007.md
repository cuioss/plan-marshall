envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:23:26Z

component=plan-marshall:manage-references
category=bug
title=affected_files is written once at outline and never rewritten when scope moves, so the read is faithful to a stale write

# The affected_files defect is a missing WRITE path, not a bad read — which is why re-reading it never surfaced the drift

## Context

Lesson `2026-08-25-05-001` filed during this run records that `affected_files` "returns status success while under-recording the footprint (14 of 19)". That framing attributes the defect to the read. The session transcript refutes it.

The 14 was **correct and operator-ratified at outline**. The gate question was: *"The spec declared 5 affected files; discovery found 14 ... Accept 14 files (Recommended)"*. At that moment, 14 was the truth.

Scope then widened twice more, both times deliberately and both times through an operator gate:

1. At 4-plan: *"e2ad54 verified: `test_bot_participation_contract.py:105-110` carries a comment D5 falsifies ... Fix it in this plan"*.
2. At 6-finalize entry: *"Two findings are pending ... Fix both in this plan"*.

The realized footprint reached 19. `references.affected_files` was never rewritten at any of the three widenings.

## Root cause

There is a write path into `affected_files` at outline and no write path out of any later phase. Three separate later consumers read the key faithfully and each got an outline-era answer. Re-reading a stale value three times cannot detect staleness — only comparing it against the live footprint can, and no consumer is required to.

## Proposed action

1. Rewrite `affected_files` at each scope-widening gate (the same gate that already asks the operator to accept the widening), or
2. Better: have `manage-references` return `declared[]`, `realized[]` and a coverage verdict on every read, so no consumer has to remember to cross-check. This removes the LLM judgement that `finalize-step-plugin-doctor` performed on its second firing and skipped on its first.

Treat this as a **merge_into** against lesson `2026-08-25-05-001` rather than a new lesson — it corrects that lesson's root-cause attribution.

## Evidence

- aspect: chat_history_analysis — three operator-ratified widenings, none followed by a rewrite
- aspect: artifact_consistency — `declared: 17` (outline headings), `references.affected_files: 14`, realized 19
- `work.log` 05:48:27 — the one consumer that DID cross-check named the exact five missing files
