envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T14:28:58Z

# A zero finding-fetch means not-reviewed, never reviewed-and-clean

component: plan-marshall:automatic-review
category: bug
confidence: high

## Context

During finalize of `arm-the-refusal-recovery-that-has-never-run` (PR #1431, merged as `29a3dad1c`), the orchestrator reported that "CodeRabbit round 4 came back clean". CodeRabbit had never run on that commit. Two separate misreadings combined: a finding fetch returning `count_stored: 0` was read as "reviewed, nothing found" when it equally means "no review happened", and a *fresh* `cause=quota` refusal comment was dismissed as a known stale comment already seen in an earlier round.

The plan's own participation ledger corroborates the absence. At the merged head `9d47652e5cd0714615f4f32c59667088b239b76f` the ledger carries two `cuioss-review-bot` rows and **zero** `coderabbit` rows.

The error was caught only by `project:finalize-step-review-retrospective`, i.e. after the merge had already been authorised, and recovery required opening scaffolding PR #1440 to obtain the missing review post hoc. That review found a Major (`parse_toon` deleting the first character of a shallow-indented block-scalar payload) plus a Minor, both fixed in PR #1441 and merged as `05ca6fe7b`.

## Root cause

`count_stored: 0` is a single observable standing for two mutually exclusive states — *reviewed and clean* and *not reviewed* — and the merge gate treats the benign reading as the default. Nothing in the fetch return distinguishes them, so the caller must infer participation from a different signal, and under an unattended run it inferred wrongly. This is the confident-signal-hides-a-caveat archetype, committed by the very plan that was shipping guards against it.

## Proposed action

Make the fetch verb unable to express the ambiguity: return participation state and finding count as separate fields, so that `reviewed: false` is structurally distinguishable from `reviewed: true, count: 0`. A merge gate must be able to fail closed on `reviewed: false` without consulting a second source. Additionally, refusal-comment recognition must key on the comment's own currency (its `updated_at` relative to the current head) rather than on whether the comment id has been seen before — an in-place-edited refusal is a *new* refusal wearing an old id.

## Evidence

- aspect: chat_history_analysis — the session ran effectively unattended after the outline gate; `operator_turn_count` reduces to a single free-form turn (`status?`) across the whole execute-and-finalize arc.
- artifact: `artifacts/pr-participation-currency-ledger.jsonl` — merged head `9d47652e` carries `cuioss-review-bot` rows only; no `coderabbit` row exists for it.
- artifact: `review-retrospective.md` — `project:finalize-step-review-retrospective` is the step that detected the gap, post-merge.
- consequence: PR #1440 (scaffolding, closed unmerged) and PR #1441 (`05ca6fe7b`) exist solely to recover the missed review.
