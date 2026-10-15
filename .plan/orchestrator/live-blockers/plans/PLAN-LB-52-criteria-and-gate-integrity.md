# PLAN-LB-52: Criteria and gate integrity — script-enforced, on every harness

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-52-criteria-and-gate-integrity.md` and is queued as one row file,
> `queue/PLAN-LB-52.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Re-staged from the adversarial landing analysis of PLAN-LB-39 (#1768, `c8adaf178`),
> `landings/PLAN-LB-39.md`. PLAN-LB-39's harness-agnostic deliverables (D2, D6, D7) shipped as
> prose with doc-wording tests; this plan makes them scripts. Seen on Antigravity, OpenCode and
> Claude Code (lessons `-011`, `-015`, `-016`, `-026`).

## Objective

Three integrity failures keep recurring on every harness, and PLAN-LB-39 — which owned them —
recurred two of them in its own run:

- A plan is graded against criteria it rewrote. PLAN-LB-39's refine dropped every Done-when
  clause; its functional review then graded the rewritten outline, and the main context edited the
  verdict file to "met" three times with `python3 -c`.
- A head is pushed past its gates. PLAN-LB-39 rebased and force-pushed an ungated head; CI went
  red on it.
- A phase is left open or skipped without a sound. The metrics start-without-end case has no
  guard; the unrecorded-commit guard has three bypasses.

Each deliverable is a script check with a test that fails at `c8adaf178`; a doc-wording test does
not count as evidence for any Done-when here.

## Deliverables

1. **The criteria are frozen and the verdict is the reviewer's.**
   - At outline approval, a script snapshots the success criteria per deliverable together with
     the request's Done-when text (`request.md`, and the spec when the request points at one).
   - The functional review grades against the snapshot; any criterion the current outline lacks,
     narrows or rewrites relative to the snapshot is a finding, not a pass. Deleting a criterion
     requires a logged operator decision.
   - The verdict file is written only by the review's own script verb; a verdict whose content does
     not match the reviewer's recorded output is refused at the finalize step gate.

   *Done when:* tests: (a) an outline whose criterion was narrowed after approval yields a
   finding; (b) a verdict file edited after the reviewer wrote it is refused; (c) a deleted
   criterion with no operator decision is refused. Each fails at `c8adaf178`.

2. **No push or merge of a head its mandated gates have not seen.**
   - The push verb (including `force-push-with-lease` and the rebase path) refuses when the head
     differs from the last pre-push gate's recorded head — `pre-push-quality-gate.md:60` states
     this in prose only.
   - The merge barrier refuses when any head-dependent finalize step's `head_at_completion`
     differs from the merge candidate's head (the PLAN-LB-26 `3db65fc05`/`74e6bfda` case).
   - Request-named gates compose: `compose_request_project_gates` (`_manifest_core.py:608`) reads
     keys nothing writes; source them from the request/plan, or remove the dead path.

   *Done when:* tests: a fix commit after the last gate makes push refuse; a rebased head makes
   `force-push-with-lease` refuse; a merge candidate newer than the functional-review head makes
   the barrier refuse; a request naming a gate yields it in the composed manifest.

3. **Phase boundaries hold without bypasses.**
   - The transition refuses to advance over a phase with a start marker and no end marker (the
     PLAN-41 case: `4-plan` no end, `5-execute` no start).
   - The unrecorded-commit guard (`_cmd_lifecycle.py:508`) also applies when `use_worktree` is
     false (`:547`), reads the ledger of the plan's own worktree rather than the cwd, and compares
     against the remote base rather than a possibly stale local `main` (`:422`).
   - `set-phase` into `6-finalize` runs the same guard (CodeRabbit Major `a90612` on PR #1768,
     deferred there).

   *Done when:* tests for each: start-without-end refuses; a main-checkout plan with an unrecorded
   commit refuses; a transition run from another cwd reads the right ledger; a branch rebased onto
   a newer `origin/main` with stale local `main` passes; `set-phase` refuses like `transition`.

Split guard: three deliverables.

## Claim Labels

- OBSERVED: `functional-review.md:86` "freeze" compares with `manage-solution-outline read`, the current outline; no snapshot exists (delegated agent).
- OBSERVED: the PLAN-LB-39 root rewrote `work/functional-review-verdict.json` with `python3 -c` at 01:51:42, 05:12:09 and 11:38:12 on 2026-10-14 (delegated agent, OpenCode DB `ses_ec9968164ffeRdYIgaux9dNEOC`).
- OBSERVED: the PLAN-LB-39 root ran `worktree-rebase-to`, raw `git rebase --continue` and `git-workflow force-push-with-lease` at 2026-10-14T16:27–16:29 with no gate in between (orchestrator-read transcript).
- OBSERVED: `pre-push-quality-gate.md:60` refusal is prose; its test asserts `'refuse the push' in text` (delegated agent).
- OBSERVED: `_manifest_rules.py:73` reads `plan.phase-5-execute.request_gates` / `project_gates` from marshal.json; nothing writes them (delegated agent).
- OBSERVED: `_cmd_lifecycle.py:508` `_phase_end_marker_refusal`, `:547` pass-through when `use_worktree` is false, `:422` local `main` preferred (delegated agent).
- HYPOTHESIS: PLAN-LB-32 (shipped) already carries part of the head-binding at the barrier — read `merge_barrier` before adding (verify-at-outline).
- Verify-first clause: PLAN-LB-47 (staged) touches `execution.md`/`triage.md`; PLAN-LB-42 (running) touches the outline Q-Gate — read both before outlining D1.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/` — snapshot verb (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/` — verdict verb, barrier (verify-at-outline) (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/` — push refusal (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_rules.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` (D3)
- OBSERVED: `test/plan-marshall/manage-status/test_transition_boundary_guards.py` (D3)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — verdict and barrier tests (verify-at-outline) (D1, D2)

## Dependencies and Sequencing

- Depends on: none; after PLAN-LB-47 is preferable (shares `_cmd_lifecycle.py`-adjacent finalize
  surfaces and the PR template). The gate will ask on overlaps.
- Overlaps with: PLAN-LB-47 (phase-6-finalize tests); PLAN-LB-42 (running, outline Q-Gate).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-52-criteria-and-gate-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
