envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:03Z

component=plan-marshall:phase-6-finalize
category=improvement
source_plan=lb-22-finalize-loop-control
confidence=high

# Pass self-review candidates to the author by file path, not inline

## Context

`phase-6-finalize/workflow/pre-submission-self-review.md` Step 2 tells the dispatcher to hand the surfacer's whole output to the author inside the prompt:

```text
    candidates: |
      {candidates_toon}
```

On this plan a full-scope round surfaced 324 candidates over 53 files (233 user-facing strings, 223 schema-bearing files, 66 count-prose entries). The operator measured the candidate document at 40 to 50 KB; it was not inlined. It was written to a file and the author was given the path - the author's hand-back says "I read the candidates file in full (lines 1-721)".

## Root cause

The inline form was written for small candidate sets. The candidate-count gate in Step 1b sends exactly the large sets to dispatch, so the documented transport is the one that does not fit the case it is used for.

## Proposed action

- Document file transport as the dispatch form: the surfacer writes its output under the plan's `work/` directory (an output-file flag, or the dispatcher stages it), and the prompt carries the path.
- Keep the inline form only for the inline branch of the gate, where nothing is dispatched.

## Evidence

- source: lines 236-248 of `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` at main `6b00815e0`.
- aspect: chat_history_analysis - round-1 author hand-back: `counts_total: 324`, `files_in_scope: 53`, and the statement that it read the candidates file.
- not re-measured here: the 40 to 50 KB size is the operator's observation; the retrospective confirmed the candidate counts and the file transport, not the byte size.
