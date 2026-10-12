envelope_version=1
sender_type=plan
sender_id=lb-32-head-dependent-step-refire
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T03:27:55Z

component=finalize-step-lessons-housekeeping
category=bug
source_plan=lb-32-head-dependent-step-refire
confidence=high

# Name the non-active records when housekeeping reports an empty corpus

## Context

At the first outline pass of plan `lb-32-head-dependent-step-refire`, the lessons consult surfaced 18 active lessons, all on `plan-marshall:phase-6-finalize`. At the second outline pass, roughly half an hour later, the same consult surfaced 0 and the agent reported "the corpus holds no lesson for `plan-marshall:phase-6-finalize` any more (a listing in any status returns none; corpus total is 1)". The plan's request cites 64 retained lessons on an earlier plan.

All 11 lessons-housekeeping firings then read `manage-lessons list --full` as `total: 1, filtered: 0` and took the empty-corpus exit. Eight of those returns flagged that the zero means "zero active lessons", not "zero files", and each said it could not look further because the workflow documents no step for it. Nobody established what the one non-active record is, or where the 18 lessons went.

The consequence for this plan: the delta rule, carry-over and the aggregate decision-log entry it ships were never exercised against a real corpus. They rest on test evidence alone.

## Root cause

The step's empty-corpus exit reports a count without the population behind it, so a corpus that was emptied or relocated mid-plan is indistinguishable from one that was always empty. The cause of the 18-to-0 change was not investigated in this pass and is not known. The 2-refine to 3-outline boundary shows a `main_sha` drift (ledger landings on the base branch); no link to the corpus change was established.

## Proposed action

- On the empty-corpus exit, have the step run the all-status listing and put the non-active count and ids in its return and its work-log line, so "0 active, N superseded or removed" is stated.
- When a consult at outline surfaced lessons and a later firing finds zero active, have the step say so explicitly rather than report a clean zero.
- Separately, establish what happened to the 18 `plan-marshall:phase-6-finalize` lessons on this machine between the two outline passes.
- Run the delta rule once against a corpus with real lessons before relying on its cost claim.

## Evidence

- aspect: chat_history_analysis — outline pass 1: "18 active lessons surfaced"; outline pass 2: "`surfaced_count: 0` ... corpus total is 1"; housekeeping returns: "`total: 1, filtered: 0` ... I did not look at that file - the workflow documents no command for it"
- aspect: request_result_alignment — deliverable 2 fulfilled by task status, gap recorded: not validated end to end
- aspect: plan_efficiency — 11 housekeeping firings, each `work_performed: false`
