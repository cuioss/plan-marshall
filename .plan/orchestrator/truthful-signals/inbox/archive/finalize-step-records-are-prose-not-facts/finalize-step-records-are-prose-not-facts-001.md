envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=landing
created=2026-08-02T11:37:51Z

## What landed

**Plan**: `finalize-step-records-are-prose-not-facts` — "Finalize step records are prose, not facts"
**PR**: #1076 (`fix(finalize): structured step facts, fix rebase action classifier`)
**Branch**: `feature/finalize-step-records-are-prose-not-facts`

### Shipped

- **D0 — per-step fact obligations.** `extension-api/standards/ext-point-finalize-step.md` now carries a
  `records_facts` frontmatter obligation, derived per-step from real consumer questions rather than as a
  uniform template. The obligation is **set-valued with a stated delta rule**: the declaration equals the
  UNION over a step's terminal `mark-step-done` call sites, and each call site records only the honest
  SUBSET. Two named directions guard it — no-orphan-declaration (existential) and no-undeclared-record
  (universal).
- **D1 — rebase classifier fixed at its true root cause.** `workflow-integration-git/scripts/git-workflow.py::cmd_worktree_rebase_to`
  previously returned `action: rebased` unconditionally on `rc == 0` in the `ahead` state, even when the
  rebase replayed zero commits. It now derives `action` from a pre/post HEAD SHA comparison and emits the
  two new payload fields `pre_sha` / `post_sha`; a zero-replay rebase reports `action: noop`.
- **D2 — structured step-record schema.** `manage-status mark-step-done` gained a repeatable
  `--fact key=value` surface, persisted into the `phase_steps` step record as a `facts` map, with an
  `invalid_fact` rejection for a malformed token (echoed as `offending_token`, rejected before any write).
  `finalize-step-sync-baseline.md`, `branch-cleanup.md`, and `sonar-roundtrip.md` are wired to populate it.
  `display_detail` is unchanged in contract and now RENDERS from those facts rather than solely holding them.
- **D3 — population-derived contract tests.** `test/plan-marshall/phase-6-finalize/test_step_records_facts_contract.py`
  (9 assertions: 1-7 population-derived over the discovered step population, 8-9 labelled targeted anchors)
  plus rebase-classifier tests that were verified to fail pre-fix.

### Self-demonstrating evidence

This plan's own finalize run is the proof: its `finalize-step-sync-baseline` step record reads

```text
facts: {action: noop, upstream_commit_count: 0, work_performed: true}
display_detail: "already current with origin/main, no commits replayed"
```

The pre-fix code would have recorded `action: rebased` for exactly this state. The defect the plan targeted
was retired inside the plan's own landing run, on the very step record the epic's Watch entry names.

### Root-cause relocation (positive signal worth keeping)

The request's D1 named `baseline-reconcile`'s return shape as the confirm/refute artifact. Step 3b
source-premise verification against code showed `_cmd_baseline_reconcile.py` has **no `action` field at all**
(it returns `classification` / `auto_reconciled` only) — the `action` field is produced by
`cmd_worktree_rebase_to`. The fix site moved before a line was written. The request's own split-guard
("fix the classifier, not the display string") anticipated this and held. Source-premise verification earned
its cost on this plan.

### Quality signals

| Signal | Value |
|--------|-------|
| Q-Gate outline findings | 2, both `taken_into_account` with the schema level-mismatch reconciled explicitly |
| Q-Gate execute findings | 1 test-failure, `fixed` (detector false positive on prose) |
| Pre-submission self-review | 2 contract-drift findings found and fixed |
| Simplify | 3 edits, 3 findings |
| Automated review | CodeRabbit: 2 comments (1 outside-diff, 1 nitpick), both fixed on-branch. PR-Agent: no actionable finding. |
| CI | all checks green |

### Residue the epic should track

1. **The epic condition is only PARTIALLY retired.** Three finalize steps got `records_facts` obligations
   (`sync-baseline`, `branch-cleanup`, `sonar-roundtrip`). Every other finalize step still carries prose-only
   `display_detail`. This is deliberate — D0's own constraint forbade a uniform schema and required per-step
   derivation from real consumer questions — but it means "finalize step records are prose, not facts" remains
   true for the majority of steps. A follow-on plan is needed to work the remaining population, and it should
   reuse D0's obligation-derivation method rather than templating.
2. **`sonar-roundtrip` step-execution-logging gap still open.** "Marker absence != step-did-not-run" was
   named as adjacent in the request and explicitly deferred to D0's own scope call. D0 did not absorb it.
   It belongs on the epic's Watch list as an unclaimed truthful-signals defect.
3. **One script-failure cluster** was observed by the finalize Signal Gate (`signal_script_failure_clusters_count: 1`)
   but is NOT itemised here: this body is barred from re-reading the work log, and the dispatcher forwards only
   the count, not the failing notation. The gate can therefore report that a script failed without any consumer
   being able to learn WHICH — a truthful-signals defect in the lessons-capture dispatch contract itself.
   Recommend the dispatcher forward the failing notations alongside the count.

### Gate counts as forwarded

`signal_qgate_pending_count: 3`, `signal_automated_review_count: 1`, `signal_script_failure_clusters_count: 1`.

Note for reconciliation: the forwarded pending-Q-Gate count of 3 did not reconcile against a per-phase
`qgate list --resolution pending` sweep at capture time — `2-refine` / `3-outline` / `4-plan` / `5-execute` /
`6-finalize` each returned `filtered_count: 0` for `pending`, because every finding had already been resolved
by the time this step ran. The count is a snapshot taken earlier in the dispatch loop, not a live figure.
Worth checking whether the gate should be re-evaluated at dispatch time or explicitly labelled as a snapshot.
