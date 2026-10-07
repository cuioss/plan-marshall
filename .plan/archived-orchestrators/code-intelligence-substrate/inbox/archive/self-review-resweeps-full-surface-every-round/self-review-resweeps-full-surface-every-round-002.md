envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:21:11Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_aspects=execution-context-dispatch-audit,log-analysis,plan-efficiency

# Emit a [DISPATCH] line on every loop-back re-dispatch, not only on first entry

`pre-submission-self-review` spawned **six** times during PR #1126's finalize and emitted **one** `[DISPATCH]` work-log line (`2026-08-09T00:37:14Z`). `project:finalize-step-plugin-doctor` spawned **twice** and emitted **one** (`00:34:11Z`). Every spawn after the first is invisible in the canonical dispatch trail.

The spawns are not in doubt — two independent ledgers record them:

- Six `[STATUS] (plan-marshall:execution-context.pre-submission-self-review) Complete` lines at `00:47:36`, `01:07:11`, `01:18:36`, `01:29:11`, `01:44:39`, `01:56:26`.
- Six rows in `work/metrics-dispatch-boundaries-6-finalize.toon` totalling **1,528,196 tokens**.

## Root cause

The `[DISPATCH]` emission is wired to *first entry into a step*, not to the re-fire from the resumable re-entry check. Every step that ran once is correctly instrumented; every step that looped back is instrumented once regardless of how many times it actually spawned.

## Solution

Move the emission to the spawn site (or add one at the loop-back re-fire path) so the `[DISPATCH]` count equals the spawn count. The `dispatch-logging.md` emission contract already specifies the line shape; only the placement is wrong.

## Impact

`dispatch-logging.md` names `work.log` `[DISPATCH]` lines as the audit's primary evidence, and the execution-context dispatch audit's `shape_violation` check is built on them. On this plan the trail undercut the single most expensive step 6:1 — an auditor reading `work.log` alone sees ONE self-review round costing ~250K tokens, where the truth is six rounds costing 1.53M. The gap was only detectable because a *second* ledger existed to contradict the first; on a step with no dispatch-boundary rows it would be undetectable.

This is a confident-signal-hides-a-caveat instance: the trail is not silent about the missing spawns, it is confidently complete-looking.
