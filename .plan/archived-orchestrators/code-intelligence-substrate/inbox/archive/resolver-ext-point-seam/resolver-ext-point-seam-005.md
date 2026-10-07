envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T15:18:12Z

component=project:finalize-step-review-retrospective
category=bug
title=A finalize artifact not regenerated after a loop-back ships a confident claim the plan's own history refutes

# A finalize artifact not regenerated after a loop-back ships a confident claim the plan's own history refutes

Found by `plan-retrospective` on PR #1067, after the plan had merged. Not remediated.

## What happened

`project:finalize-step-review-retrospective` ran once, at 11:45:22–11:46:44, and wrote
`review-retrospective.md`. Its content was **accurate at that moment**:

> **A green finalize on this PR is not evidence that CodeRabbit or Sourcery
> saw the diff — 2 of 3 configured reviewers produced no review at all.**

and, on CodeRabbit specifically:

> No assessment possible — the bot never reviewed this diff (rate-limited
> refusal). Zero comments, zero findings, zero signal of any kind. This is a
> **coverage gap**, not a clean bill of health.

At **13:40:11Z** CodeRabbit reviewed commit `371854d14` and filed 5 actionable inline
comments plus a review body. All 6 are persisted in this plan's own findings store as
`pr-comment` records authored by `coderabbitai`. They produced TASK-010 through TASK-014,
a loop-back to `5-execute` at 13:49, and 5 fix commits.

The step never re-ran. `review-retrospective.md` shipped uncorrected.

## The resulting contradiction is internal to one plan directory

| Source | Claim |
|---|---|
| `status.json` → `phase_steps[6-finalize].automatic-review` | `coderabbit reviewed and 5 findings fixed - 0 new at this HEAD` |
| `review-retrospective.md` | `coderabbit … never reviewed this diff … zero signal of any kind` |
| `manage-findings list --type pr-comment` | 7 records, 2 distinct authors, 6 of them `coderabbitai` |
| `review-retrospective.md` "Deterministic Metrics (Step 2 — authoritative, not recomputed)" | `total_findings: 1`, `reviewer_count: 1` |

The block labelled **authoritative** is the one that is wrong.

## Root cause

The step derives reviewer participation from the **live bot-completion state at the
current HEAD** rather than from the **accumulated `pr-comment` findings ledger**. Live
state is a point-in-time reading and goes stale under exactly the event the loop-back
exists to produce. The ledger is append-only and cannot.

A second, independent contributor: the finalize step roster treats a step as terminal once
`outcome=done` is recorded, so a loop-back re-enters `5-execute` and returns without
re-running any already-done `6-finalize` step. That is correct for idempotent steps and
wrong for any step that **produces a persisted artifact describing the state of the PR**.

## Why the epic should care

This is the epic's theme running in reverse. Every other instance catalogued so far is a
confident GREEN concealing a caveat. This is a confident RED — an emphatic, bolded,
correctly-reasoned assertion of a coverage gap — that became false while sitting on disk,
and that a future auditor reading the archived plan will take at face value. The failure
mode is not "the signal was too confident for its evidence"; it is "the signal was exactly
as confident as its evidence warranted, and then the world moved".

Note the second-order effect: inbox message `resolver-ext-point-seam-004` was written from
this same 11:51 snapshot and inherits the same defect. See the accompanying `finding`
message.

## Proposed action

1. Derive `reviewer_count` / `total_findings` / per-author rows from
   `manage-findings list --plan-id {id} --type pr-comment` — a deterministic query over an
   append-only store — instead of from live bot state. This removes the staleness class
   entirely rather than patching one instance of it.
2. Mark artifact-producing finalize steps as **loop-back-dirty**: any step whose output is
   a persisted document describing PR or review state must be re-run when the plan
   re-enters `6-finalize` after a loop-back, even though its prior `outcome=done` stands.
3. Generalizable rule worth adding to the standing set: **a persisted artifact that
   describes external state must carry the HEAD it describes, and any consumer must
   compare that HEAD against the current one before trusting it.** `review-retrospective.md`
   carries no HEAD stamp at all, which is why the staleness is invisible on inspection.

## Evidence

- `review-retrospective.md` (whole file) vs `logs/work.log:453-460` and the `pr-comment`
  findings store.
- `logs/work.log:399-401` — the single review-retrospective dispatch and its completion.
- `logs/work.log:460` — `Loop-back iteration 1/3 - CodeRabbit review at rebased HEAD
  371854d14 produced 5 FIX tasks (TASK-10..14)`.
- `status.json` `phase_steps[6-finalize]` — 20 steps, all terminal, review-retrospective
  recorded once.
