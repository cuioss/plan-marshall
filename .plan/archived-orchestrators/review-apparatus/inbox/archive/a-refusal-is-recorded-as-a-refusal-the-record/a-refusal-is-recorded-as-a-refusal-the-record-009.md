envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:18:37Z

component=plan-marshall:automatic-review
category=bug
title=A CodeRabbit refusal no arm recognised was credited as participation for a HEAD the bot had explicitly declined

# A CodeRabbit refusal no arm recognised was credited as participation for a HEAD the bot had explicitly declined

## Context

Mid-run on PR #1368, CodeRabbit answered the plan's own re-review command invocation with:

```text
<!-- CodeRabbit review command invocation: v2:aa7f7bd4... -->
<details>
<summary>⚠️ Action not completed</summary>

Review rate limited.

> Note: CodeRabbit is an incremental review system and does not re-review
> already reviewed commits. This command is applicable only when automatic
> reviews are paused.
</details>
```

That is a **refusal**. It was filed as finding `12ce1a`, a pending actionable `pr-comment` finding, and remediated in-run by TASK-016. The remediation registered the command-reply literal in `coderabbit.md`'s `refusal_patterns`.

## Root cause — three arms, three different reasons for missing it

Every arm of the refusal-recognition stack declined this notice, each for its own structural reason:

- **Registry arm** — holds only the literal `Review limit reached`. This notice says `Review rate limited`.
- **Structural arm** — needs a limit-exceeded verb the notice does not contain.
- **Enumerative arm** — inert (no measured threshold), and additionally **vetoed by the `<details>` code-anchor marker** the notice is wrapped in.

## Impact — one cause, two wrong outcomes

1. The refusal was filed as an **actionable review finding**, so the triage pass was handed a notice with nothing in the diff to action.
2. `github_re_review` credited it as an **issue_comment completion signal** — participation recorded for a HEAD CodeRabbit had *explicitly declined to review*. That is the precise false signal this plan shipped to abolish, occurring inside the plan's own finalize run against its own PR.

It is worth stating plainly because it is the sharpest available instance of the epic's theme: the merge barrier's participation evidence read a refusal as a review.

## Why the shipped fix is a patch, not a class fix

Registering one more vendor literal closes this wording and only this wording. The three arms failed for three *independent* structural reasons, so the next wording change re-opens the same hole — and the failure mode is silent, because an unrecognised refusal does not error, it counts as participation. The `<details>` veto is the sharpest edge: a vendor wrapping a refusal in a disclosure block disables an arm that would otherwise have a chance.

## Proposed action

1. Treat "a bot reply to our own command invocation" as its own recognised class. The `CodeRabbit review command invocation: v2:` marker is a **structural** signal, present regardless of the human wording, and it identifies the message as an answer to the trigger this stack posted.
2. Make the `<details>` code-anchor veto conditional rather than absolute for bodies carrying that marker — the veto exists to avoid matching quoted code, and a vendor's own disclosure-wrapped notice is not that.
3. Fail closed on the participation axis: a comment that answers our command invocation and matches no arm should be recorded as `refusal_unrecognised` — surfaced, never credited as a completion signal — so an unregistered wording costs a report rather than a false green.
4. Add a matched negative control for each arm over this exact notice body, so a future wording drift is a failing test rather than a merge that proceeds unreviewed.

## Evidence

- finding: `12ce1a` (`pr-comment`, `issue_comment`, coderabbitai, reviewed_commit_sha `d02f8c16`), resolution `fixed` via TASK-016; resolution detail records both wrong outcomes verbatim
- source: `automatic-review/standards/coderabbit.md` `refusal_patterns` — held only `Review limit reached` before the in-run fix
- source: the enumerative arm's code-anchor veto and the structural arm's limit-exceeded verb requirement
- context: signal `signal_automated_review_count: 1` for this plan is this remediated-in-run finding class
