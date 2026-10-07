envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:42:46Z

component=plan-marshall:automatic-review
category=bug
created=2026-09-05
bundle=plan-marshall

# review_completeness exit-1 cause IS established: malformed_bot_flag, both tokens

## Context

This message **closes an evidence gap a sibling candidate from this same plan explicitly
left open.** The plan-retrospective candidate on `review_completeness` (message 002)
recorded:

> The exit-1 group is an unhandled internal exception. `script-failure-analysis` captured
> no stderr excerpt for it, so the exception itself is not in the retrospective's evidence
> and must be reproduced.

It does not need reproducing. Both exit-1 occurrences carry their full diagnostic in the
work log, and neither is an unhandled exception — both are **deliberate, well-argued
caller-error refusals** with the error code `malformed_bot_flag`:

`da3353` @ 2026-09-05T15:19:20Z:

> `--participated-bots` expects `bot_kind:evidence_kind` pairs but received the token
> `'cuioss-review-bot'`, which is not a pair. A bare bot_kind neither proves participation
> nor is a valid absence: silently dropping it would resolve the bot to absent (a blocking
> state) and manufacture a false merge block, so it is rejected as a caller error.

`ee3749` @ 2026-09-05T15:19:26Z:

> `--refused-causes` expects `bot_kind:value` pairs but received the token
> `'sourcery=quota'`, which is not a pair. A bare bot_kind carries no value; silently
> dropping it would lose the remedy signal the overlay exists to carry — and for a size
> cause it would also lose the state, silently re-classifying a structural refusal as a
> temporal one.

## Root cause

The script is behaving correctly and the **call site** is wrong, in two different ways
within six seconds of each other:

- `--participated-bots cuioss-review-bot` — a bare `bot_kind` where a
  `bot_kind:evidence_kind` pair is required. The caller knew *which* bot participated but
  supplied no evidence discriminator.
- `--refused-causes sourcery=quota` — the right two components joined by the **wrong
  separator**: `=` where the contract specifies `:`.

So this is the same call-site/declared-surface family as the three exit-2 rejections on
the identical notation (filed separately as the argparse-rejection population candidate),
not a distinct internal-failure class. All five failures on this notation share one cause:
the caller does not hold the flag contract.

The `=`-vs-`:` slip is the more instructive of the two, because `sourcery=quota` carries
completely correct *information* in an incorrect *shape* — exactly the input a
forgiving parser would have accepted and a strict one refuses.

## Why the refusals are right and should stay

Both messages spell out what silent tolerance would have cost, and both consequences are
the failure mode this whole epic exists to remove:

- dropping a bare `--participated-bots` token resolves the bot to `absent`, a **blocking**
  state — manufacturing a false merge block from a bot that did participate;
- dropping a bare `--refused-causes` token silently re-classifies a **structural** refusal
  as a **temporal** one, losing the remedy signal.

Both are "a signal that could not be read presenting as a signal that was read". The
scripts refuse rather than fail open. Do not soften them.

## Additional context: this gate failed while gating its own subject

The plan was itself an investigation into the required reviewer returning an empty list on
a correct full review. During its finalize the completeness gate that decides required-bot
participation failed **five times** on
`plan-marshall:automatic-review:review_completeness check` (3 x exit 2, 2 x exit 1), and
the `automatic-review` step re-fired 7 times with one `failed` outcome. Both exit-1
failures fired at 15:19Z, i.e. **while the merge lock was held** (`lock-owned` at
15:19:04Z) — on the post-merge re-review path, at the moment the gate's answer mattered
most.

## Proposed action

1. Reconcile the `review_completeness check` call site against the pair-shaped flag
   contract for `--participated-bots`, `--refused-causes`, and every sibling overlay flag.
   The declared surface is enumerated in the executor's own exit-2 rejection at `ea325d`.
2. Make the pair separator unmistakable at the call site — the `=` slip suggests the
   `:`-pair convention is not obvious where these arguments are assembled.
3. Retire sibling candidate 002's "must be reproduced" action item: superseded by the
   evidence above. Its remaining action item (a failed completeness check must not present
   to its caller as an absence of findings) stands unaffected and is the more important
   half.

## Evidence

- work log `da3353` — exit 1, `malformed_bot_flag`, `--participated-bots 'cuioss-review-bot'`
- work log `ee3749` — exit 1, `malformed_bot_flag`, `--refused-causes 'sourcery=quota'`
- work log `ea325d` — exit 2 on the same notation, enumerating the 14 declared flags
- work log `3d6e10` (x2) — exit 2 on the same notation at 11:15:59Z and 14:15:22Z
- work log `9bcf0a` — merge lock `lock-owned` at 15:19:04Z, 16s before the first exit-1
- `status.metadata.phase_steps["6-finalize"].automatic-review` — `firing_count: 7`, one prior `failed`
- sibling inbox message `required-reviewer-returns-empty-list-002.md` — the gap this closes
