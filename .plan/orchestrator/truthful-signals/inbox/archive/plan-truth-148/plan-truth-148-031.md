envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:56Z

# Candidate lesson: a complete-coverage sweep had a known blind spot, and the run closed it by hand

- source_signal: qgate / 5-execute (D1 gate verdict)
- record_id: 6bb8e4
- component: plan-marshall:extension-api
- resolution: taken_into_account — discharged by exemption, NO EDIT, which was the correct complete outcome

## What happened

The declaration sweep for four dispatcher-owned prompt-body fields reported complete coverage (count 8, 4 files, 5452 scanned, 0 unreadable, not truncated, no elision) — but the inventory does not walk `.claude/skills/**`, where six `project:` step docs live. The run named the gap explicitly and read all six directly, so the "no surviving declaration across all 26 implementors" claim was actually complete rather than merely reported complete.

## Candidate rule

Keep as a positive pattern. `architecture search --content` is inventory-scoped: a clean zero means "not in any inventoried file", never "not in the tree". When the target population includes `.claude/**`, `.github/**` or any gitignored path, the sweep's zero must be paired with an explicit direct read of those paths — and the completeness claim must name both halves.
