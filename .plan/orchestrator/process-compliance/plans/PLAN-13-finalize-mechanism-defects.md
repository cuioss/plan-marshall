# PLAN-13: Finalize-mechanism structural defects

epic: process-compliance
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-13-finalize-mechanism-defects.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a
> one-line pointer and carries no brief, so every per-plan carry is authored here and
> nowhere else.

## Objective

Close four structural contradictions in the phase-6-finalize dispatcher — a fail-closed
epic guard that contradicts archive-plan's irreversibility, a documented archive path
missing its `local/` segment, a forked subagent that inherits a worktree-pinned cwd and
cannot finish `branch-cleanup`, and a `pr_title` that is never re-derived after a gate
deliverable removes scope — and settle the unconfirmed `session_binding` orphan-sweep
hypothesis before treating it as a live defect.

## Deliverables

1. `emit-landing`/`archive-plan` contradiction: when the dispatcher omits orchestration
   inputs, `emit-landing`'s fail-closed epic guard currently blocks in a way that
   contradicts `archive-plan`'s irreversibility (archive already moved the plan directory
   by the time the guard fires) — reconcile the ordering or the guard so the two steps
   cannot disagree about whether the plan is still recoverable.
2. `archive-plan` SKILL.md doc-path fix: the documented archive destination is
   `.plan/archived-plans/{date}-{plan_id}`; the actual resolution walks to the nearest
   `.plan/local` ancestor per ADR-002, landing at `.plan/local/archived-plans/{date}-{plan_id}`.
   Correct every documented instance and add a doc-vs-resolver parity test.
3. Forked finalize subagent worktree-cwd fix: a forked finalize subagent inherits the
   parent's worktree-pinned cwd and cannot complete `branch-cleanup` from it — give the
   fork an explicit cwd re-anchor (or document why the fork must not run branch-cleanup)
   with a regression test.
4. `pr_title` re-derivation: `pr_title` is settled at refine (Step 13) and never
   re-derived after a gate deliverable removes scope later in the run — add the
   re-derivation trigger (or an explicit staleness check) so a shrunk scope cannot ship
   under a title that no longer describes it.
5. `session_binding` orphan-sweep investigation (unconfirmed hypothesis): the author who
   filed this flagged it unconfirmed — confirm or refute whether the orphan classifier
   ever treats the `by-cwd` cwd-lookup index directory as an orphan and removes it. If
   confirmed, fix it as a fifth deliverable; if refuted, close with the refutation
   evidence and no code change.

(5 deliverables, one investigation-gated. Evaluated against the Scope-Bloat Split Guard:
kept unsplit because deliverables 1-4 share one dispatcher-ordering root cause and
deliverable 5 is a small, independently-gated investigation on an adjacent surface —
splitting would leave four single-defect plans with no shared verification pass.)

## Claim Labels

- OBSERVED: `emit-landing`'s fail-closed epic guard contradicts `archive-plan`'s
  irreversibility when the dispatcher omits orchestration inputs — read at
  `.plan/orchestrator/process-compliance/inbox/lessons-handling-26-09-22-01-001.md`
  § Finalize-mechanism structural defects (lesson 2026-09-20-08-003, primary)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: ledger cite (lessons-handling drain message); dispatcher ordering not traced this pass
- OBSERVED: `archive-plan`'s SKILL.md documents `.plan/archived-plans/{date}-{plan_id}` as
  the archive destination, omitting the `local/` segment the ADR-002 cwd-walk actually
  resolves to — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
  § archive_path (line 1765) and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` § `{archive_path}` (line 54)
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: both files state `.plan/archived-plans/...`; `tools-file-ops/scripts/file_ops.py` :63-71 states archived-plans stays main-anchored under the `.plan/local` cwd-walk (ADR-002), and `constants.py` `DIR_ARCHIVED = 'archived-plans'` is composed onto that base, not onto `.plan/` directly
- OBSERVED: a forked finalize subagent inherits a worktree-pinned cwd and cannot finish
  `branch-cleanup` — read at
  `.plan/orchestrator/process-compliance/inbox/lessons-handling-26-09-22-01-001.md`
  § Finalize-mechanism structural defects (lesson 2026-09-20-08-010)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: ledger cite (lessons-handling drain message); fork/cwd inheritance not traced this pass
- OBSERVED: `pr_title` settled at refine Step 13 is never re-derived after a gate
  deliverable removes scope — read at
  `.plan/orchestrator/process-compliance/inbox/lessons-handling-26-09-22-01-001.md`
  § Finalize-mechanism structural defects (lesson 2026-09-21-13-004); grounding symbol
  at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md`
  § `pr_title` grounding (line 238)
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: create-pr.md :238-245 grounds `pr_title` against the refine-time `status.metadata.pr_title` value and treats an empty read as an invariant-bypass error, with no re-derivation trigger after a later scope change
- HYPOTHESIS: `archive-plan`'s session-binding orphan sweep may classify the non-UUID
  literal `by-cwd` as an orphan and remove it, deleting its own cwd-lookup index
  directory every finalize — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py`
  § orphan classifier (verify-at-outline; explicitly flagged unconfirmed by its author,
  lesson 2026-09-20-08-005)
- Verify-first clause: the consuming phase settles the HYPOTHESIS against the
  implementing source before scoping deliverable 5 — refutation closes deliverable 5
  with the refutation evidence and no code change; it does not block deliverables 1-4.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` — fail-closed epic guard
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` — archive-path documentation and irreversibility ordering
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — archive_path documentation instance
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md` — `pr_title` grounding and re-derivation trigger
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md` § forked-subagent dispatch shape — exact seam for the cwd-inheritance fix (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py` § orphan classifier — exact seam for deliverable 5 (verify-at-outline; contingent on the HYPOTHESIS above)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — regression tests for deliverables 1-4

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-11 (declares `phase-6-finalize/` as a bare directory, which by containment covers every file this spec names — `SKILL.md`, `archive-plan.md`, `dispatch-inline-split.md`, `emit-landing.md`, `create-pr.md`; confirmed via `corpus cross-check` — sequence, do not parallelize); PLAN-06 (`dispatch-inline-split.md` — sequence, do not parallelize)
- Adjacent to: PLAN-07-opencode-repairs (opencode-specific finalize gaps stay in WS-06, untouched here)

## Folded inbox material (same act)

- `lessons-handling-26-09-22-01-001.md` (candidate-lesson): finalize-mechanism cluster (4 lessons) plus the session-binding hypothesis (1 lesson) — staged as this spec

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-13-finalize-mechanism-defects.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
