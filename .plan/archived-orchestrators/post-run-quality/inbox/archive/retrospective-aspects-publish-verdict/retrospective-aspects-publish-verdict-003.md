envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:25:56Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
title=compile-report drops any non-success fragment, losing the findings it carried

# compile-report drops any non-success fragment, losing the findings it carried

## Context

`compile-report.should_emit` refuses every conditional fragment whose `status` is not
`success` or absent:

```python
status = fragment.get('status')
if status not in (None, 'success'):
    return False
```

On this retrospective's first compile, the permission-prompt-analysis fragment honestly
reported `status: unmeasured` (its population was undeliverable — see the sibling
transcript-delivery lesson). The section was classified `sections_dropped` and its
findings — including an `error`-severity RECURRENCE finding — did not appear in the
report at all. The compile returned `status: warning`; had the workflow's "never treat a
compile-report warning as a clean pass" rule not been followed, the finding would have
been silently lost.

The evidence that this gap is general rather than incidental is already in the file:
chat-history-analysis needed a bespoke carve-out placed BEFORE the status guard
(lines 145-148), with a comment explaining that the guard would otherwise drop its
Tier-2 `status: skipped` fragment "making a post-guard branch dead code for the only
case it exists to serve". The same problem was solved once, for one aspect, by special
case.

## Root cause

The envelope `status` field is overloaded. For most aspects it means "the producer ran";
the guard reads it as "the measurement succeeded". An aspect with an honest could-not-look
result has no way to say so in the envelope without being deleted from the report.

## Proposed action

Two options, in preference order:

1. Make the guard render any fragment carrying a non-empty `findings` list regardless of
   status, and generalise the chat-history carve-out away. A fragment with findings has
   something to say by definition.
2. Failing that, document the idiom explicitly in the aspect references: the envelope
   `status` MUST stay `success` when the producer ran, and measurement degradation MUST
   be carried in a dedicated field — the pattern `outline-vs-shipped`
   (`comparison: inconclusive`), `manifest-decisions` (`footprint_resolution.status`) and
   `analyze-logs` (`change_attribution: unavailable`) already follow. Today that
   convention is discoverable only by reading the guard.

Add a test that registers a fragment with a non-success status and a non-empty findings
list, and asserts the findings reach the report.

## Evidence

- first compile: `sections_dropped[1]: Permission Prompt Analysis`, `status: warning`
- second compile after changing only the envelope status to `success`: `sections_dropped[0]`, identical findings rendered
- source: `scripts/compile-report.py` `should_emit` lines 145-152
