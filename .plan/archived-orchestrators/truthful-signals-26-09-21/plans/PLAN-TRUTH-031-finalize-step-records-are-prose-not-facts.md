# PLAN-TRUTH-031: finalize step records are prose, not facts — and the one structured field lies

epic: truthful-signals
workstream: WS-01

## Objective

Finalize steps record their outcome as free-text `display_detail`. The consequence is not cosmetic:
**questions about the finalize hot path cannot be answered from the ledger at all**, and the one field
that looks structured — `sync-baseline`'s `action=` classifier — **mislabels a no-op as a rebase**.

Make the finalize step record carry the derivable facts as fields, and fix the classifier that is
already wrong.

## Provenance

Operator request, 2026-08-01 (items 4 and 5 of the finalize-improvement set), **merged into one plan**
because they share a root cause: the step record does not carry trustworthy structured facts. Both were
surfaced by the orchestrator's D0 measurement over the 39-plan archived corpus, which hit each defect
while trying to answer a different question.

## The two defects, both measured

**A — the late rebase's action is unrecoverable.** `branch-cleanup`'s `display_detail` is free prose:
of ~35 archived records, only ~10 mention rebasing at all (*"rebased onto base, merged via queue,
cleanup complete"*); the rest say only *"merged via queue, main pulled, branch + worktree removed"* or
name a PR number. ⇒ **`sync-baseline.md`'s claim that the late rebase "degrades to `action: noop` in the
common case" is UNVERIFIABLE from the ledger.** ⚠ It is **NOT refuted** — the orchestrator initially
said so, then corrected itself: the 39/39 `action=rebased` figure measures the **early** rebase
(`sync-baseline`, order 3), a different step from the late one (`branch-cleanup`, order 70). The
correction is recorded in `logs/decision.log`.

**B — `action=rebased` does not mean a rebase happened.** Two archived records read
`action=rebased, 0 upstream commits` (`daemon-audit-logs-interactions-not-job-lifecycles` and
`manage-lessons-mixes-local-time-and-utc`). A rebase with zero upstream commits **is** a no-op, yet the
classifier stamps `rebased`. ⇒ **The `action` field conflates "a rebase operation ran" with "the rebase
did work".**

⛔ **Defect B retroactively weakens the corpus.** Because 26 of the 39 `sync-baseline` records carry a
bare `action=rebased` with **no upstream count at all**, and 2 of the 13 that do carry one report zero,
**the corpus cannot say how often the early rebase was necessary.** The orchestrator's "39 of 39 always
rebased" reading is therefore an artefact of a mislabelling classifier, not a finding — corrected here
before anyone builds on it.

## Deliverables

1. **D0 — GATE (mutates nothing): derive which finalize steps owe which facts.** Enumerate the finalize
   steps and, per step, the facts a consumer needs (did it act; what did it act on; how much). ⛔ **Do
   not design one schema for all steps** — `branch-cleanup` owes a rebase action and a merge mechanism;
   `sync-baseline` owes an upstream-commit count; `ci-verify` already returns structured TOON. Derive
   the per-step obligation from real consumer questions (the epic's Watch entry lists the ones that
   could not be answered), not from a uniform template.
2. **D1 — fix the `action` classifier (defect B).** A rebase that moves nothing reports `noop`, not
   `rebased`. ⛔ **Fix the classifier, not the display string** — the same wrong value is what any
   future consumer reads. ⚠ Check whether `baseline-reconcile`'s own return carries the correct
   distinction and only the display drops it; if so the fix is at the display site and the classifier is
   exonerated. **Read the implementing source before aiming the fix** — this epic has a standing rule
   that a corrective is a hypothesis until the named site is read.
3. **D2 — carry the derived facts as fields on the step record (defect A).** Add the per-step structured
   fields from D0 to the finalize step record so `display_detail` becomes a *rendering* of facts rather
   than the only place they exist. ⚠ **Do not break the existing `display_detail` contract** — the
   `mark-step-done --display-detail` surface and the ≤80-char convention are consumed elsewhere.
4. **D3 — tests, each verified to FAIL pre-fix.** (a) A zero-upstream rebase records `noop`. (b) A
   `branch-cleanup` run records its rebase action as a field, retrievable without parsing prose.
   (c) The D0 obligation set is asserted non-empty and covers the steps named in the Watch entry.

Four deliverables — under the split guard.

## Claim Labels

- **OBSERVED**: two archived `finalize-step-sync-baseline` records read
  `"rebased onto origin/main (action=rebased, 0 upstream commits)"` — plans named above, read this pass.
- **OBSERVED**: the `sync-baseline` display strings across 39 records take **8 distinct free-text
  shapes** (bare `action=rebased` ×26, `2 upstream commits` ×4, `2 upstream` ×2, `1 upstream commit` ×2,
  `0 upstream commits` ×2, `2 conflicts resolved` ×1, `3 conflicts merged` ×1, `1 upstream commit, no
  overlap` ×1). ⇒ **The same fact is expressed four different ways** (`2 upstream commits` vs
  `2 upstream`), which is what makes prose unparseable even in principle.
- **OBSERVED**: `branch-cleanup` display strings — ~10 of ~35 mention rebasing; the remainder record
  only the merge and cleanup.
- **OBSERVED**: finalize step-execution logging is itself incomplete — the `Executing step` marker
  appears 33× for `sync-baseline` but 1× for `sonar-roundtrip` across 39 plans, so **marker absence does
  not imply the step did not run.** ⚠ This is adjacent to D2 and may share a fix; **D0 decides whether
  it is in scope** rather than this spec assuming it.
- **HYPOTHESIS**: the mislabelling is in the classifier rather than the display formatting.
  **Confirm/refute at D1** — confirm/refute artifact: `baseline-reconcile`'s return shape and the
  `sync-baseline` executor's display-string construction.
- **Verify-first clause**: D2 assumes the finalize step record has room for structured per-step fields
  alongside `outcome` / `display_detail`. Confirm against the `phase_steps` schema in
  `manage-status/standards/status-lifecycle.md` before scoping; if it does not, the deliverable becomes a
  schema change and D0 must re-evaluate the split.

## Expected Surface

- **OBSERVED**: `plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md`
- **OBSERVED**: `plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- **HYPOTHESIS**: `plan-marshall/skills/workflow-integration-git/**` — `baseline-reconcile`'s classifier
  (verify-at-outline; D1 names the exact symbol)
- **HYPOTHESIS**: `plan-marshall/skills/manage-status/**` — only if D2's fields need a schema change
- **HYPOTHESIS**: `test/plan-marshall/{phase-6-finalize,workflow-integration-git}/**`

## Dependencies and Sequencing

- ⛔ **CANNOT EMIT WHILE PLAN-TRUTH-001 IS RUNNING** — it holds `phase-6-finalize`.
- ⚠ **PLAN-TRUTH-006** (`baseline-reconcile-persists-merge-commit`) owns the same
  `sync-baseline` + `baseline-reconcile` surface. ⭐ **Evaluate folding this plan into TRUTH-006 at
  outline** — they may be one change; the orchestrator kept them separate because 006's concern is a git
  mutation contract while this is an observability contract, but that boundary is worth re-testing
  against the code rather than the descriptions.
- ⭐ **Prerequisite-in-spirit for PLAN-TRUTH-030** — 030's D0 attribution works off the CI manifests
  today, but this plan is what makes that answer re-derivable rather than a one-off orchestrator pass.
  **Prefer this first if both are queued.**
- ⚠ **PLAN-TRUTH-028** also edits `phase-6-finalize` standards — sequence, do not pair.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-031-finalize-step-records-are-prose-not-facts.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
