envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T11:36:13Z

## Proposed lesson metadata

- `component`: `plan-marshall:phase-6-finalize`
- `category`: `bug`
- `title`: An awaitable review-bot rate-limit window is treated like a hard refusal — review_rate_window_await is false

## Observation (coverage gap on PR #1066)

PR #1066 was reviewed by **one** bot. The other two refused, for materially
different reasons that were handled identically:

| Bot | Refusal | Recoverable? |
|-----|---------|--------------|
| pr-agent | — | reviewed |
| coderabbit | rate-limit **window** | **yes — awaitable** |
| sourcery | hard quota | no |

`review_rate_window_await` is currently `false`, so the coderabbit refusal was
never waited out. A recoverable refusal and an unrecoverable one produced the
same outcome: no review.

## Why this matters beyond one PR

The finalize gate reported green with one of three configured reviewers
participating. That is the epic's theme again — a confident aggregate signal
("automated review: done") hiding the caveat that two thirds of the configured
review surface never looked at the diff. The corpus already carries the harder
version of this: *a green finalize is not proof the bots saw the diff*, and
*only `ci pr comments --pr-number N` is evidence of participation*.

The new contribution here is the **distinction between refusal classes**. A
window-scoped rate limit is a wait, not a failure. Collapsing the two loses
recoverable review coverage for free.

## Owed work

1. Classify bot refusals into `awaitable` (window-scoped rate limit) vs
   `terminal` (hard quota, auth failure, bot not installed).
2. Turn `review_rate_window_await` on for the `awaitable` class, with a bounded
   wait and a single retry.
3. Make the finalize display detail carry the **participating reviewer count**,
   not just an outcome — `1/3 reviewers participated` is the signal that would
   have surfaced this at the time instead of at lessons-capture.
