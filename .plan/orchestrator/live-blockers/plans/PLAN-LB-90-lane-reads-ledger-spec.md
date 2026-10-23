# PLAN-LB-90: The runbook lane reads its spec from the ledger worktree when told to, and says which copy it read

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-90-lane-reads-ledger-spec.md` and is queued as one row file, `queue/PLAN-LB-90.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-23 from the consumer finding `pm-mcp-core-m2-m4-006` (revision 2), priority **high**, set by the
> operator on 2026-10-23. Source of the request: a landing of the consumer epic (`rb-25-waits-001`, #145) and a live
> test of `runbook_lane resolve` the same day.

## Objective

With `orchestrator.use_worktree` on, every spec edit lives only in the shared ledger worktree until a ledger land, but the
runbook lane reads its spec from the main checkout. A lane can therefore run on a spec other than the one the orchestrator
reports, and the only remedy today is a land (a pull request through the merge queue) before every emit that follows a
spec edit. This plan lets the lane read the spec from the ledger worktree when told to, falls back to the main checkout,
and makes the copy it read visible in `resolve` and in the landing.

## Deliverables

1. **`resolve` and the lane command accept a parameter that reads the spec from the ledger worktree first.**
   - The parameter is set per emit, so a round of emits needs no ledger land; its name and whether it also exists as a `marshal.json` knob beside `orchestrator.use_worktree` is the owner's design, decided at outline and recorded with the reason.
   - With the parameter set, the lane takes the spec from `{epic_dir}/plans/PLAN-NN-{plan_slug}.md`, where `epic_dir` comes from `orchestrator resolve-path --slug {slug}`, and falls back to the main checkout's copy when the worktree has none.
   - Slug, derived names, `{plan}` and `sender_id` resolve exactly as today. The default (parameter absent) is unchanged.
   - A spec that exists only in the worktree is readable under the parameter.
   - With `orchestrator.use_worktree` off there is no second copy and the parameter is a no-op, not an error.

   *Done when:* fixture tests show, for a spec present in both copies with different bodies:
   - the default reads the main checkout's copy;
   - the parameter reads the worktree's copy;
   - a spec present only in the worktree is read under the parameter and refused by default;
   - with `use_worktree` off the parameter reads the one copy without error.

   At HEAD `resolve --spec` given the worktree path answers `spec_outside_orchestrator` (HYPOTHESIS, see Claim Labels).

2. **The result and the landing say which copy was read.**
   - `resolve` returns `spec_source: ledger_worktree | main_checkout`, and when both copies exist and differ, says that they differ.
   - The landing's rule-check section carries the same two facts.
   - A silent read of the older copy is the failure this removes.

   *Done when:* a fixture with two differing copies reports `spec_source` for each mode and the differ marker; a fixture with one copy reports no differ marker. The lane text instructs the run to record both in its landing.

3. **The lane's write rule is unchanged by the new read.**
   - The lane still never edits the spec or any file under `.plan/orchestrator/`, and the worktree copy is read only.

   *Done when:* a test asserts that the worktree-read path performs no write and that the lane text keeps the rule verbatim.

Split guard: three deliverables, one surface (the lane's spec resolution). The orchestrator side, an emitted command that carries the parameter, is the epic's to change once the lane accepts it, and is not part of this plan.

## Claim Labels

- OBSERVED: `_SPEC_RE` matches the project-relative spec path as a whole and only `.plan/orchestrator/{slug}/plans/` at the project root qualifies; `_resolve_spec` raises `spec_outside_orchestrator` otherwise — read at `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` L110, L152-175.
- OBSERVED: the lane text reads the spec from the main checkout — `runbook-lane/SKILL.md` L103: "Read it from the **main checkout**; it is git-tracked there."
- OBSERVED: `orchestrator resolve-path --slug {slug}` publishes `epic_dir` and `store_checkout` — `plan-orchestrator/SKILL.md` § resolve-path.
- OBSERVED (consumer finding): a live `runbook_lane resolve --spec` with the worktree's absolute or relative path answered `spec_outside_orchestrator` on 2026-10-23; the consumer's PLAN-25, PLAN-26 and PLAN-87 ran on a spec older than the one the orchestrator reported. Not re-run here.
- HYPOTHESIS: `use_worktree` can be read by the lane from the same seam the orchestrator uses, without a new import path — confirm at `runbook_lane.py` and `tools-file-ops` (verify-at-outline).
- Verify-first clause: choose the parameter's name and home (flag of `resolve` and of the lane command, a `marshal.json` knob, or both) and record why; confirm that "ledger worktree first" is the right default order for a per-emit parameter.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_resolve_spec`, the `resolve` verb (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § 0 spec read, the rule-check section of the landing (D1, D2, D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` (D1, D2, D3)
- HYPOTHESIS: `test/plan-marshall/runbook-lane/test_runbook_lane_spec_source.py` — a new module (D1, D2, verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-73 landing first (it is running and edits the same lane sections and `runbook_lane.py`).
- Overlaps with: PLAN-LB-73 on `runbook-lane/SKILL.md`, `runbook_lane.py` and `test_runbook_lane.py` (the gate will ask).
- Adjacent to: `plan-orchestrator/workflow/orchestrate.md` Step 5, the emitted command, which stays untouched here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-90-lane-reads-ledger-spec.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
