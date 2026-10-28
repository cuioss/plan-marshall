# PLAN-LB-102: The runbook lane reads its spec from the ledger worktree first and falls back to the main checkout, by default

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-102-ledger-first-spec-read.md` and is queued as one row file, `queue/PLAN-LB-102.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the operator's instruction on the open HIGH item "the emitted lane command cannot read a spec from the ledger
> worktree". The operator's ruling on the design: **it should be the other way around — look in the ledger worktree first, and
> only if the spec is not there, look in the main checkout.** PLAN-LB-90 shipped the opposite default (main checkout, with an
> opt-in flag); this plan reverses it.

## Objective

With `orchestrator.use_worktree` on, every spec edit lives only in the shared ledger worktree until a ledger land. The orchestrator
emits `/plan-marshall-runbook-lane plan=<path>` as a one-line pointer with no flag, so the lane reads the main checkout's copy and
can run on a spec older than the one the orchestrator reports; the only remedy is a land before each emit that follows a spec edit.
This plan makes the worktree copy the default read and the main checkout's copy the fallback, so an emitted command needs no flag and no land.

## Deliverables

1. **The default read order is the ledger worktree, then the main checkout.**
   - `_resolve_spec` takes the worktree's `plans/PLAN-NN-{plan_slug}.md` when it exists and the main checkout's copy only when the worktree has none.
   - The staged-spec shape check accepts a path inside the ledger worktree's store without any flag; a path outside both stores is still `spec_outside_orchestrator`.
   - A spec that exists only in the worktree is readable by default; a spec that exists only in the main checkout is still readable.
   - With `orchestrator.use_worktree` off there is no second copy, and the read takes the one copy without error.
   - Slug, derived names, `{plan}` and `sender_id` resolve exactly as today.

   *Done when:* fixture tests, for a spec present in both copies with different bodies, show the default reads the worktree's copy; for a spec only in the worktree, it is read by default; for a spec only in the main checkout, it is read; with `use_worktree` off, the one copy is read without error. The first two fail at HEAD, where the default reads the main copy and refuses a worktree-only spec.

2. **`--spec-from-ledger` stays accepted and means what the default now means.**
   - A command written for the previous lane text, which carries the flag, still runs and reads the same copy the default reads.
   - Whether the flag is kept as a documented no-op or removed after a deprecation is the owner's design, decided at outline and recorded with the reason; removing it must not turn an old emitted command into `unrecognized arguments`.

   *Done when:* a test runs `resolve` with and without the flag on the same fixture and gets the same `spec_source`, and the lane text names the flag's status.

3. **The result and the landing still say which copy was read, and the lane text states the new order.**
   - `resolve` still returns `spec_source: ledger_worktree | main_checkout`, and `spec_differ: true` when both copies exist and differ; `spec_differ` keeps meaning "the copy NOT read says something else", which is now the main checkout's copy.
   - `runbook-lane/SKILL.md` § 0 no longer says "Read it from the **main checkout** by default" and states the worktree-first order and the fallback.
   - The landing's rule-check section keeps carrying both facts.

   *Done when:* tests report `spec_source` and the differ marker for both copies, for the worktree-only and main-only cases, and for `use_worktree` off; a text test pins the new wording and that the old default sentence is gone.

4. **The lane's write rule is unchanged by the changed read.**
   - The lane still never edits the spec or any file under `.plan/orchestrator/`, and the worktree copy is read only.

   *Done when:* a test asserts the worktree-read path performs no write and the lane text keeps the rule verbatim.

Split guard: four deliverables, one surface (the lane's spec resolution). The orchestrator side needs no change: the emitted command stays the one-line pointer.

## Standing Constraints

- A copy is read only if its RESOLVED location stays under its store root (the existing containment check); a link planted at the derived location must not hand the lane a file from outside the store while the result claims a store copy.
- The `spec_source` label comes from where the file actually resolves, never from a flag or from the order alone.
- Sonar is not enabled for this project and is ignored.

## Claim Labels

- OBSERVED: the default read is the main checkout's copy and the ledger copy is chosen only when `from_ledger` is set — `_resolve_spec` at `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` L276-327 (`if from_ledger and ledger_copy is not None`), at HEAD `3aad286fb`.
- OBSERVED: a path inside the ledger store is accepted by the shape check only under `from_ledger` — `runbook_lane.py` L226-237; otherwise `spec_outside_orchestrator`.
- OBSERVED: `_resolve_spec` already resolves the ledger copy on BOTH paths so the differ marker can report an unread newer copy (L299-326), and anchors the fallback on the main checkout the ledger worktree belongs to (`_main_store_dir`, L240-256).
- OBSERVED: `runbook-lane/SKILL.md` L181-187 says to read the spec from the main checkout by default and to add `--spec-from-ledger` for worktree-first; L193 shows the verb with the flag.
- OBSERVED: the orchestrator's emitted lane command is the one-line `/plan-marshall-runbook-lane plan=.plan/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md` with no flag — `plan-orchestrator/workflow/orchestrate.md` Step 5.
- OBSERVED: `test_runbook_lane_spec_source.py` exists and references the flag three times; `test_runbook_lane.py` references it zero times.
- HYPOTHESIS: the `/plan-marshall` lifecycle lane reads its pointed-at spec by cwd-relative path at `phase-1-init` and therefore also reads the main checkout's copy — confirm at `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` (verify-at-outline). If confirmed, record it in the landing as a finding and do not widen this plan.
- HYPOTHESIS: other docs describe the old default or the land-before-emit workaround — confirm by searching `marketplace/bundles/plan-marshall/skills/plan-orchestrator/` and `doc/` for `spec-from-ledger` and "land the ledger before" (verify-at-outline).
- Verify-first clause: decide the flag's fate (D2) and record why; confirm no installed lane text of an earlier version emits a form the new default rejects.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_staged_spec_shape`, `_resolve_spec`, the `resolve` verb and its argparse surface (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § 0 spec read, the rule-check section of the landing (D2, D3, D4)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_spec_source.py` (D1, D2, D3, D4)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` (D3, D4)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: parked PLAN-LB-89 on `runbook-lane/SKILL.md` (it is parked).
- Adjacent to: `plan-orchestrator/workflow/orchestrate.md` Step 5, the emitted command, which stays untouched; PLAN-LB-100 and PLAN-LB-101, which share no file with this plan, so all three can run together.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-102-ledger-first-spec-read.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
