# PLAN-TRUTH-142: Phase 5 reports green over work it did not verify or commit

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-11 from the cross-repo lessons drain, two Token-Sheriff relays from the
`lessons-handling-26-09-04-01` sender, each a lesson first filed in Token-Sheriff's store:

- `lessons-handling-26-09-04-01-035` (origin `2026-09-08-09-001`, plan `refresh-2a-coverage-priorities`) —
  the integration-test canonical cannot be seeded as a phase-5 verification step.
- `lessons-handling-26-09-04-01-052` (Token-Sheriff PLAN-09, PR #731) — a phase-5 leaf reported its tasks
  done while skipping its Step 10a commit.

⭐ **Why one plan and not two**: both are the SAME skill (`phase-5-execute`) producing the same false
signal — a phase-5 green that covers less than it claims — at two different seams (what is verified, and
what is committed). Neither has an owner in this or any sibling epic; each is a single small deliverable.

## Objective

**Phase 5 can report a green verification sweep and completed tasks over work it never verified and never
committed.** (1) `phase-5-execute/standards/canonical_verify.md` names `integration-tests` (and `e2e`) as
whole-tree verification gates and as *"the prime candidates"* for the orchestrator tier, but its
machine-readable `canonicals:` frontmatter lists only `quality-gate`, `module-tests` and `coverage` — and
that list is the only thing the add-step discovery expands. So `default:verify:integration-tests` is
refused, and a plan whose work IS integration-test coverage is verified by a `verify` that runs no ITs:
green by construction. (2) The phase-5 task loop accepts a leaf's `status: success` as evidence that its
Step 10a commit happened; a leaf that skipped the commit left edits unstaged under a green report.
`phase-6-finalize` already observes the checkout on return for its `post_run_review` band — phase 5 has no
counterpart. Close both, so a phase-5 green means what it says.

## Deliverables

1. **D0 — re-ground at HEAD.** Re-verify both mechanisms against the implementing source and name the
   artifact each check read. Establish whether any other canonical named in `canonical_verify.md`'s body
   is likewise absent from `canonicals:` — the frontmatter list and the body must be reconciled as SETS,
   derived by enumeration, not by checking the two names the report happened to cite.
2. **D1 — make every canonical the step names seedable.** Add `integration-tests` and `e2e` (and any
   further gap D0 finds) to `canonicals:`, so `manage-config plan phase-5-execute add-step
   default:verify:integration-tests` is accepted. The existing *Unresolved-canonical skip* already makes
   this safe for a project without the profile (the step records `skipped`, not a failure). Add a guard —
   a test deriving the body's named canonicals and asserting set equality with the frontmatter list — so
   the next divergence is a red test, not a consumer report.
3. **D2 — observe the tree on a phase-5 leaf's return.** At the phase-5 task boundary, a leaf that
   declares its task done must be checked against the observable — the worktree's tracked-dirty state, or
   the change-ledger/commit the Step 10a commit would have written — rather than against its own report.
   A success returned over a dirty tracked tree is surfaced as an inconsistent state, never accepted.
   Reuse the `post_run_source_guard` mechanism phase 6 already has rather than building a second one.
4. **D3 — controls.** For D1: the add-step call accepted for `integration-tests`, and the set-equality
   guard shown red against the unfixed frontmatter. For D2: a leaf return of `success` over a dirty tree is
   refused, with a matched positive control proving a genuinely committed task is admitted.

## Claim Labels

- OBSERVED: `canonicals:` lists exactly `quality-gate`, `module-tests`, `coverage` — read at `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` § frontmatter, at `356973d80`.
- OBSERVED: the same document's body names `integration-tests` at four sites (the canonical→role table, the whole-tree-gates sentence, the unresolved-canonical skip, and the orchestrator-tier "prime candidates" sentence) — read at `canonical_verify.md` lines 26, 46, 81, 86, at `356973d80`.
- HYPOTHESIS: `_discover_all_verify_steps()` expands only the `canonicals:` list into accepted `default:verify:{canonical}` step ids — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py` § `_discover_all_verify_steps` (verify-at-outline).
- HYPOTHESIS: the phase-5 task loop accepts a leaf's success without observing the tree — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` § Step 10 / Step 10a (verify-at-outline).
- HYPOTHESIS: phase 6's `post_run_source_guard` is reusable at the phase-5 task boundary — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py` § its entry point and inputs (verify-at-outline).
- Verify-first clause: D0 settles the three HYPOTHESIS claims before D1/D2 are scoped; a refuted D2 mechanism (the loop already observes the tree) drops D2 and D3's second half.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` — the `canonicals:` frontmatter (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py` — `_discover_all_verify_steps`, read to confirm the expansion (expected READ-ONLY) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — the Step 10 / 10a task-boundary check (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py` — reused, possibly generalised (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-5-execute/` — the D3 controls (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-config/` — the add-step acceptance control (D3) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-TRUTH-105` reasons about `mutates_source` / commit instrumentation at phase 6; D2
  here is the phase-5 counterpart and must not re-implement that seam — reuse it. `PLAN-TRUTH-132` owns the
  frozen `step_execution_tier` stamp at the phase-5 runner; D2 touches the task boundary, not the tier
  resolution. Check disjointness at emit.
- Adjacent to: `PLAN-TRUTH-122` (Maven's test-jar / reactor canonical that cannot pass) — a separate
  defect in which command a canonical resolves to; this spec only makes the canonical seedable.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-142-phase-5-reports-green-over-work-it-did-not-verify-or-commit.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-147-a-lane-reports-green-yields-or-transitions-without-the-artifact-its-own-gate-requires.md` (PLAN-TRUTH-147)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
