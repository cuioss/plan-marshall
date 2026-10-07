envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:57:09Z

# Trigger-A re-review gate reads `matched` only, discarding `head_sha_verified`

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=hook-timeout-unit-confusion
source_pr=1131

## Context

`phase-6-finalize/standards/branch-cleanup-rereview.md` drives the trigger-A re-review — the check
that a rebased, force-pushed HEAD has been reviewed before the pre-merge barrier. Its step 3 says:

> Read both `matched` AND `timed_out` from the returned TOON. **When `matched: true`**, the fresh
> review is now on the PR.

That claim is stronger than the envelope supports. `github_re_review.py`'s `await_fresh_review`
returns **eight** decision-bearing fields — `matched`, `matched_signal`, `head_sha_verified`,
`refusal_detected`, `refusal_class`, `refusal_eta`, `refusals[]`, `timed_out` — and its own module
docstring states the distinction plainly:

> 2. An **issue comment** authored by the awaited `bot_kind` … Reported as
>    `matched_signal: issue_comment` with `head_sha_verified: false` — a comment carries no
>    reviewed-commit SHA, so it establishes that the bot **responded**, NOT that it reviewed the new
>    HEAD.

The consumer reads two of the eight. An inventory content sweep over the crawled corpus finds
`matched_signal`, `head_sha_verified` and `refusal_detected` in the producer, in
`workflow-integration-github/SKILL.md`, in `automatic-review/standards/pr-agent.md`, in
`automatic-review/SKILL.md` (`refusal_detected` only) and in the producer's tests — **and in no
consumer**. `branch-cleanup-rereview.md` is provably in that corpus (it matches a
`github_re_review` sweep with 7 hits) and matches none of the three field sweeps, so the negative is
a clean one rather than an uncrawled path.

Two consequences follow, and both fired on this plan:

1. **The gate cannot distinguish a verified review from an unverified comment.** The entire timeout
   branch — the `AskUserQuestion`, the `rereview-timeout-override` grant, the defer path — is gated
   on `timed_out: true AND matched: false`. A comment-only match therefore skips the operator gate
   entirely and advances to the pre-merge confirmation gate with an unverified HEAD.
2. **The record cannot adjudicate it afterwards.** The step's log line (line 61 of the sub-standard)
   hard-codes `matched={matched}` and emits nothing else. The line this run produced reads:

   ```
   [2026-08-09T20:04:08Z] Branch cleanup: re-reviewed rebased HEAD d3e76976000060d7fea408ad32f976d4b249fce4 (bot_kind=coderabbit, matched=true)
   ```

   From that record it is structurally impossible to recover whether the new HEAD was actually
   reviewed, or whether a refusal notice was detected and skipped.

## A correction worth carrying

The observation that prompted this was reported as *"the sub-standard has no refusal branch"*. The
producer **does** have one, in both discriminators, and it is careful: `_refusal_record` applies a
two-layer rule (the bot's registry `refusal_patterns` first — CodeRabbit declares
`"Review limit reached"` — then a structural `_is_rate_limit_notice` fallback), never counts a
refusal as a completed review, and records every skipped refusal on the envelope specifically so the
caller can arm a recovery instead of seeing a bare timeout.

The defect is one layer down and more actionable for it: the producer's refusal machinery is
**complete and unconsumed** on this path. Its docstring even asserts a consumer that does not exist
here —

> the caller branches on `matched: false` AND `refusal_detected: true` to enter the recovery sequence

— and `refusal_detected` appears in `automatic-review/SKILL.md`'s opt-in rate-window recovery, not in
`branch-cleanup-rereview.md`. So trigger-A has no refusal branch **at the consumer**, while the
producer's docstring reads as though it does.

## Proposed action

1. Gate the "the fresh review is now on the PR" claim on `head_sha_verified: true`. A
   `matched_signal: issue_comment` result should route to the same operator gate the timeout branch
   uses, with its own description text ("the bot responded but no review is recorded against this
   HEAD"), rather than falling through silently.
2. Read `refusal_detected` / `refusal_class` / `refusal_eta` on this path and branch on them — the
   producer already computes exactly what the recovery needs, and CodeRabbit's registry declares
   `rate_limit_class: awaitable_window`, which makes waiting the productive response.
3. Widen the log line to carry `matched_signal`, `head_sha_verified` and `refusal_detected`. A merge
   gate's persisted record should not be weaker than the envelope it read.

## Evidence

- `phase-6-finalize/standards/branch-cleanup-rereview.md` lines 50, 61, 64, 68.
- `workflow-integration-github/scripts/github_re_review.py` — module docstring lines 26–67;
  `await_fresh_review` return dict lines 251–274 (`'head_sha_verified': matched_signal == 'review'`).
- `automatic-review/standards/coderabbit.md` — `refusal_patterns: ["Review limit reached"]`,
  `rate_limit_class: awaitable_window`.
- `logs/work.log` `20:04:08Z` — the produced line, carrying `matched=true` and nothing else.
- `architecture search --content` over the inventory: `head_sha_verified` → 8 hits, `matched_signal`
  → 8 hits, `refusal_detected` → 6 hits; no consumer among them.

## Why this belongs to truthful-signals

`matched: true` is a confident signal whose caveat lives in a sibling field nobody reads, and whose
log line drops that field. The plan that produced this run merged on a re-review the record cannot
prove happened — not because the check is absent, but because the strongest thing it computed was
thrown away twice: once at the gate, once at the log.
