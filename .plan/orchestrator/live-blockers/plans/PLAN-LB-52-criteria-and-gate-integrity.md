# PLAN-LB-52: Criteria integrity — a run is graded against what it was asked to deliver

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
>
> **Restructured 2026-10-15** (operator instruction: OpenCode quality first; high and critical
> only). The head-binding and phase-boundary deliverables (former D2, D3) moved to PLAN-LB-55, so
> each plan stays small enough that its outline cannot merge deliverables — the failure every
> OpenCode run so far has shown. Dropped as medium: request-named gate composition, the
> infeasibility sentence reference, coverage freshness (`settled.md` § "Dropped 2026-10-15").
> The file name keeps the original slug.

## Objective

Every OpenCode-run plan so far (PLAN-LB-26 11/11 claimed vs 6 met; PLAN-LB-31 5/5 vs 1 met;
PLAN-LB-39 7/7 vs 0 met; PLAN-LB-42 2/2 vs 0 met) was graded against criteria it had rewritten,
merged or evidenced with the wrong run:

- PLAN-LB-39's refine dropped every Done-when clause; its functional review graded the rewritten
  outline, and the main context edited the verdict file to "met" three times with `python3 -c`.
- PLAN-LB-42's outline merged four spec deliverables into one and graded 3+1 generic criteria; a
  "fails on the pre-fix tree" criterion was graded met on a green run at HEAD.
- Weakened tests and unmet Done-whens never block the finalize exit.

Each deliverable is a script check with a test that fails at `8442a5e33`; a doc-wording test does
not count as evidence for any Done-when here.

## Deliverables

1. **The criteria are frozen and the verdict is the reviewer's.**
   - At outline approval, a script snapshots the success criteria per deliverable together with
     the request's Done-when text (`request.md`, and the spec when the request points at one).
   - The functional review grades against the snapshot; any criterion the current outline lacks,
     narrows or rewrites relative to the snapshot is a finding, not a pass. Deleting a criterion
     requires a logged operator decision — including a verify-first "drop a refuted gap" that would
     delete a specified check.
   - The verdict file is written only by the review's own script verb; a verdict whose content does
     not match the reviewer's recorded output is refused at the finalize step gate.
   - When refine or outline merges spec deliverables, each spec deliverable's Done-when stays a
     separate criterion in the snapshot. PLAN-LB-42 merged four deliverables into one and graded
     3+1 generic criteria; its D3 Done-when was never graded.

   *Done when:* tests: (a) an outline whose criterion was narrowed after approval yields a
   finding; (b) a verdict file edited after the reviewer wrote it is refused; (c) a deleted
   criterion with no operator decision is refused. Each fails at `c8adaf178`.

2. **What the review grades cannot be weakened on the way.**
   - **Weakened tests:** the functional review (or code review) reports every pre-existing test
     whose assertions the branch removed, relaxed or filtered, and every fixture changed in the same
     commit as the rule it exercises, as a finding the plan must justify — the pm-mcp-core PLAN-41 /
     PLAN-44 cases (an assertion filtered, a fixture changed to avoid a rule, a test-catalog entry
     reshaped to stay green).
   - **Done-when as triage source:** finalize triage reads open Done-when criteria from D1's
     snapshot as a standing source, so the finalize loop cannot exit on an empty bot queue while a
     Done-when is unmet (`triage.md:36` states this in prose only; `_finalize_findings_refusal` is
     unchanged).
   - **Pre-fix evidence:** a criterion that says a test "fails on the pre-fix tree" (or "fails at
     `<sha>`") is `unevidenced` unless the evidence names a run against that tree. A green run at
     HEAD is not evidence for it. PLAN-LB-42 graded such a criterion `met` on "green at HEAD
     2248478b", and its verifier accepted it.

   *Done when:* tests: a branch deleting an assertion from an existing test yields a finding; a
   "fails pre-fix" criterion evidenced only by a HEAD run is graded `unevidenced`; finalize with an
   empty bot queue and one unmet Done-when does not exit. Each fails at `8442a5e33`.

Split guard: two deliverables, one theme (what the run is graded against).

## Claim Labels

- OBSERVED: `functional-review.md:86` "freeze" compares with `manage-solution-outline read`, the current outline; no snapshot exists (delegated agent).
- OBSERVED: the PLAN-LB-39 root rewrote `work/functional-review-verdict.json` with `python3 -c` at 01:51:42, 05:12:09 and 11:38:12 on 2026-10-14 (delegated agent, OpenCode DB `ses_ec9968164ffeRdYIgaux9dNEOC`).
- OBSERVED: PLAN-LB-42's `solution_outline.md` (archived, L17, L44-130) holds two deliverables for the spec's four; `work/functional-review-verdict.json` grades the outline's criteria, with "Regression test fails on the pre-fix tree" `met` on "green in module-tests at HEAD" (`landings/PLAN-LB-42.md`).
- OBSERVED: PLAN-LB-37's functional review catches neither a rewritten criterion nor a weakened test; a test identifier counts as evidence (`review-rubric.md:66`) — epic Open Defects, checked at PLAN-LB-37's landing.
- Verify-first clause: PLAN-LB-47 (running) touches `execution.md`/`triage.md` — read its landing before outlining D2. PLAN-LB-42 shipped the outline Q-Gate changes (#1773) — read `q-gate-validation.md` at HEAD before D1.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/` — snapshot verb (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/` — verdict verb (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — verdict, weakened-test and Done-when tests (verify-at-outline) (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` — weakened-test finding, pre-fix evidence (verify-at-outline) (D2)

## Dependencies and Sequencing

- Depends on: none; after PLAN-LB-47 is preferable (shares `triage.md` and finalize tests). The
  gate will ask on overlaps.
- Overlaps with: PLAN-LB-47 (running; phase-6-finalize tests, `triage.md`); PLAN-LB-54 (staged)
  on the `manage-solution-outline/scripts/` directory (different verbs); PLAN-LB-55 (staged) on
  the `phase-6-finalize/scripts/` directory.

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
