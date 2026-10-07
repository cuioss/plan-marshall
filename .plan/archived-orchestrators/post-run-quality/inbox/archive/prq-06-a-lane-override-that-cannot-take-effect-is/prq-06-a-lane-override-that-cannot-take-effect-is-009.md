envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:49Z

component=plan-marshall:phase-5-execute
category=anti-pattern
confidence=medium
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=logging_gap_analysis,log_analysis

# Agent-initiated re-dispatch is the dominant execute termination mode

## Context

`work/metrics-dispatch-boundaries-5-execute.toon` records seven dispatches for this plan:

| Timestamp | termination_cause | total_tokens | tool_uses | duration_ms |
|-----------|-------------------|-------------:|----------:|------------:|
| 2026-09-18T12:22:45Z | voluntary_checkpoint | 842,044 | 313 | 3,568,695 |
| 2026-09-18T13:49:11Z | voluntary_checkpoint | 404,256 | 192 | 2,484,495 |
| 2026-09-18T14:33:08Z | voluntary_checkpoint | 0 | 0 | 0 |
| 2026-09-18T14:33:25Z | voluntary_checkpoint | 209,506 | 33 | 309,296 |
| 2026-09-18T15:10:31Z | clean_exit_queue_empty | 118,141 | 19 | 138,024 |
| 2026-09-19T13:55:33Z | voluntary_checkpoint | 328,872 | 132 | 1,367,016 |
| 2026-09-19T14:09:57Z | clean_exit_queue_empty | 0 | 0 | 0 |

`voluntary_checkpoint` accounts for 5 of 7 (71%), crossing the `> 50%` threshold the `DISPATCH_TERMINATION_CAUSE` rule exists to catch. Neither documented exclusion applies: `budget_yield` is 0, so these are not bin-packer envelope boundaries, and `returned_with_findings` is 0, so none is a productive findings-bearing loop-back.

Two rows (`14:33:08Z` and `14:09:57Z`) record `total_tokens: 0`, `tool_uses: 0`, `duration_ms: 0` — dispatches that yielded having done nothing measurable at all.

## Root cause

The execute leaf is choosing to checkpoint and hand back rather than draining its task queue, and it is doing so as the normal case rather than the exception. Each checkpoint costs a fresh envelope on re-entry; the phase was re-entered three times (`close_count: 3`) and its wall span reached 26h50m against 2h23m of worked time.

The two zero-cost rows suggest a second, distinct shape: a dispatch that terminates immediately on entry, recording a boundary without performing work. That is either an immediate re-yield or a boundary recorded on a path that did nothing, and it is worth separating from the genuine checkpoints before tuning anything.

## Proposed action

1. Investigate the two zero-token, zero-tool-use `voluntary_checkpoint` / `clean_exit_queue_empty` rows first — a boundary recorded for a dispatch that did nothing is either a wasted envelope or a mis-recorded one, and which it is changes the remedy.
2. For the genuine checkpoints, raise the bar for yielding: a leaf should drain its queue unless it is actually near a context or time budget, and when it does yield it should record *why* (budget pressure vs. blocked dependency) so the cause distribution stops collapsing every reason into one token.

## Evidence

- aspect: logging_gap_analysis — `phase-5-execute DISPATCH_TERMINATION_CAUSE: voluntary_checkpoint 5 of 7 (71%)`, `budget_yield 0`, `returned_with_findings 0`
- aspect: log_analysis — `5-execute` `dispatch_boundaries` rows above; `re_entered_phases: [5-execute]`, `close_count: 3`
- `metrics.md` — 5-execute wall 26h50m against worked 2h23m
