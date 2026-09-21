envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T16:09:04Z

component=plan-marshall:manage-status
category=anti-pattern

# Undeclared-flag rejection on manage-status read inside the review-retrospective envelope

## Observation

During `project:finalize-step-review-retrospective`, a call to `plan-marshall:manage-status:manage-status read` was rejected with exit 2:

```
failure_kind=argparse_rejection
detail=Use a declared flag for `plan-marshall:manage-status:manage-status read`: ['plan-id', 'store']
```

`manage-status read` declares exactly two flags. The caller supplied a third — the natural move when reaching for a narrowed read (a phase, a section, a step) on a verb that returns the whole status document. `manage-status read` has no narrowing flag; the caller reads the whole document and selects from it.

This is the flag-side twin of the verb-paraphrase signature: the flag name is plausible, reads correctly in workflow prose, and is absent from the argparse declaration.

## Recommended rule

Structural, not exhortative — the standing rule was already in force:

1. The rejection message enumerates the DECLARED flags, which is right, but a caller who reached for a narrowing flag needs to be told the verb does not narrow at all. Where a verb deliberately has no filter surface, say so in the rejection ("`read` returns the whole document; it declares no narrowing flag") so the caller stops looking for the right spelling.
2. Consumers that need one field of `status.json` are the population that produces this failure. Check whether the recurring narrow reads (current phase, a `phase_steps` row, a metadata key) deserve a declared selector on `read`, or whether the consuming workflows should carry the read-then-select shape explicitly.

## Evidence

- Plan: `output-volume-standard` (epic `operator-ux`)
- Work log 2026-09-03T10:57:21Z, inside `execution-context.finalize-step-review-retrospective`
- The step still completed `outcome=done` and produced `review-retrospective.md`
- One of 4 distinct failing script notations on this run
