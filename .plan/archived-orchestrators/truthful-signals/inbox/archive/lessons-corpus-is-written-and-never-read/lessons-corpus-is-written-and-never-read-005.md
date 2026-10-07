envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T19:25:20Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-07-28

# `automatic-review` and the unified triage ran inline where the roster requires dispatch

`standards/dispatch-inline-split.md` is the single source of truth for the
dispatched/inline split, and it rosters `plan-marshall:automatic-review` as
**dispatched** (`→ phase-6-finalize`, no `--role`). `SKILL.md` Step 3 item 7c
further specifies that once `automatic-review` has filed its `pr-comment`
findings, the dispatcher fires **one** `verification-feedback` dispatch with
`producer=finalize-feedback` to triage them.

On this plan's finalize run, `status.metadata.phase_steps["6-finalize"]` records
`automatic-review` with `outcome: done` and `display_detail: "3 comments triaged
(2 fixed, 1 noted), sourcery rate-limited"`. `logs/work.log` contains **14**
`[DISPATCH]` lines and **none** of them carries `automatic-review`, and none
carries `role=verification-feedback`. Both the rostered step and the mandatory
triage dispatch reached terminal outcomes with zero dispatch evidence.

This is the `dispatch_coverage_violation` category the retrospective's
execution-context dispatch audit exists to catch — the inverse-coverage half.

## Why it matters more than usual on this run

The findings that were triaged inline were not trivia. CodeRabbit filed a real
functional-correctness defect (an unvalidated negative `--max-per-component`
producing a spurious `truncated` flag and a from-the-wrong-end slice) that every
in-house gate had passed. The triage that adjudicated it, and the fail-closed
`invalid_cap` resolution that was chosen over CodeRabbit's proposed silent clamp,
were both decided outside the enforcement envelope the roster requires.

## Contrast — the rest of the run was clean

All 14 emitted `[DISPATCH]` lines carry `target=execution-context-level-3` or
`level-4`; there are zero `envelope_violation`s and zero `Task: general-purpose`
occurrences. Eight rostered dispatched steps (lessons-housekeeping, plugin-doctor,
pre-submission-self-review, simplify, create-pr, review-retrospective,
lessons-capture, plan-retrospective) each carry matching evidence. The gap is
specific, not systemic — which is what makes it worth fixing rather than
excusing.

## Secondary observation on the same audit

`architecture-refresh` is rostered dispatched as a **hybrid** whose Tier-1
fan-out is the dispatching tier. Tier 1 was legitimately skipped this run ("no
affected modules"), so zero `[DISPATCH]` is CORRECT for it. The inverse-coverage
rule as written cannot distinguish that legitimate zero from the
`automatic-review` defect — both present as "rostered dispatched, terminal
outcome, no evidence". Any scripted version of this check needs a
conditional-dispatch carve-out, or it will train readers to ignore its findings.
