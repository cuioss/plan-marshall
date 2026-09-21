# Landing Analysis: PLAN-05 — Make the AskUserQuestion standard testable, and enforce it

epic: operator-ux
workstream: WS-03-prompt-quality
pr: #1378 — https://github.com/cuioss/plan-marshall/pull/1378

> Landing record for one shipped plan. Lives at `landings/PLAN-05.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Ground truth checked before any ledger write: `ci pr view --pr-number 1378` returns
`state: merged`, `merge_commit_sha: 80d9691aca2e0ef7526a8eef9cb4436367f9edcb`;
`git merge-base --is-ancestor 80d9691a main` confirms the commit is in `main`'s history;
`git show --stat 80d9691a` reports 10 files, +966 / −212. The spec staged five
deliverables; the plan reported and shipped two, because deliverables 3–5 were absorbed
into the two it names (the rule registration, the blind-spot scope statement, and the
tests are constituents of deliverable 2's landed diff, not dropped work).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. `askuserquestion-patterns.md` restructured into testable obligations | shipped-as-specified | File rewritten in `80d9691a` (291 lines changed); six numbered-obligation headings present at HEAD |
| 2. `plugin-doctor` rule for the mechanically checkable subset | shipped-as-specified | New `_analyze_askuserquestion_prompt_quality.py` (+467), registered in `_rule_registry.py` and `_runner.py` |
| 3. Rule registered in `rule-catalog.md` with severity and fix classification | shipped-as-specified | `askuserquestion-prompt-quality` present at `rule-catalog.md:120`, `severity: warning, fixable: false`, scoped to the analyze surface only |
| 4. Stated scope for what the rule CANNOT catch | **shipped-partial** | Blind spots stated for obligations 3 and 4; the STRUCTURAL gap (four underived restatements of the enforcement matrix) is not closed — filed as a finding, see Follow-Ups |
| 5. api-sheriff prompt as negative fixture; conformant rewrite passes | shipped-as-specified | `test_analyze_askuserquestion_prompt_quality.py` (+349) and `_plugin_doctor_fixtures.py` (+18) |

**Deliverable-count reconciliation.** The `landing-facts` block declares
`deliverables_total=2, deliverables_done=2` against a five-deliverable spec. This is a
re-grouping by the executing plan, not a shortfall: every spec deliverable is accounted for
above. Recorded here because a reader comparing the spec's five to the landing's two would
otherwise read three dropped deliverables.

## Metrics and Anomalies

- Tokens: 3,899,218 total. Finalize carries ~52%; the pre-submission self-review loop alone
  is 677,934 (~43% of the phase-6 dispatch total) across 5 rounds / 11 findings.
- Duration: 64,130 s wall (~17h49m elapsed), 2h56m worked.
- **Anomaly — the phase-6 figures are floors, not measurements.** The plan's own ledger
  integrity check found only **8 of 20** finalize rows pair with a boundary row. Any
  per-phase cost figure derived from a single ledger is therefore a lower bound. Do not
  quote the 52% or the 43% as measured shares; they are the measurable fraction of a
  partially-paired ledger.
- **Anomaly — 2 of 5 self-review rounds were avoidable and are an executor-discipline
  failure, not a tooling gap.** Round 1's own finding text stated *"Convergent fix is
  DELETION of the over-claiming clause"*; the executor narrowed the clause instead, repeated
  the narrowing in round 2, and round 4 then filed the replacement as still false. The rule
  that would have prevented two rounds was written inside the finding being read. No
  mechanism change addresses this.
- **Anomaly — `automatic-review` recorded its decline verdict as a false negative**, and
  `head_sha_verified` misread a bot that re-reviews by editing one comment in place, forcing
  a spurious operator escalation this run.

## Routing and Merge Behavior

- Review: CodeRabbit raised the enforcement-matrix mirror finding (thread
  `PRRT_kwDOQ3xasM6eYroJ`, Maintainability / Minor) — triaged, deliberately not fixed in
  plan, routed to this epic. `review-retrospective` measured 2 of 3 reviewers. Five
  review-machinery defects were found by *running* the machinery and recorded rather than
  fixed.
- CI/merge: all checks green; merged via the **merge queue** as squash `80d9691a`. No rebase
  conflicts, no re-verify signals.
- **Surface-collision check: the gate predicted correctly.** PLAN-05 was emitted in parallel
  with PLAN-01 on the strength of carrying zero corpus-spec overlap rows. The landed diff
  touches 10 files, every one under `pm-plugin-development` or
  `test/pm-plugin-development/` — inside the declared surface and disjoint from PLAN-01's
  `manage-config` cluster as predicted. No under-declaration correction is owed.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-05 --status shipped`
- [x] row `pr` stamped — `#1378`
- [x] row `landing` stamped — `landings/PLAN-05.md`
- [x] row `plan_marshall_plan_id` stamped — `prompt-standard-and-doctor-rule`
- [x] epic.md narrative reconciled; queue table regenerated from status.json
- [x] Open Defect opened — the enforcement-matrix mirror (derive vs collapse), a fork for the operator
- [x] Open Defect opened — the corpus-knew-and-the-run-committed-anyway gap
- [x] Watch opened — phase-6 cost figures are unreliable pending ledger pairing
- [x] 9 inbox messages drained, each with a recorded disposition, and archived
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **Enforcement-matrix mirror (inbox 001, `kind=finding`)** — the checked/blind-spot sets are
  stated in four places and derived from nothing, so the docs can drift from the analyzer
  silently. Two directions offered by the plan: *derive* (analyzer-owned coverage constant
  plus a rule or test asserting agreement — closes the class, costs a new seam) or *collapse*
  (one authoritative site, others cross-reference — cheaper, no new mechanism, matches the
  deletion-over-correction convergence, but does not mechanically prevent recurrence). The
  generalisable question — whether the marketplace wants a standing derived-doc mechanism for
  rule coverage — is an epic-level call. **Recorded as an Open Defect; surfaced to the
  operator as a decision, not folded into a spec.**
- **Two corpus lessons recurred (inbox 003, 004)** — `2026-08-25-09-002` and
  `2026-08-25-09-007`, both confirmed `active` in the corpus at analysis time, and both
  reviewed and RETAINED by this run's own lessons-housekeeping step on 2026-09-01 as "surface
  untouched by this plan". Second independent instance of each. Folded onto the existing
  corpus entries per the dedup discipline; the structural signal is recorded as its own epic
  Open Defect because it is about the housekeeping step, not about either lesson.
- **Five new machinery lessons (inbox 002, 005, 006, 007, 008)** — promoted to the global
  lessons corpus. None is operator-UX work, so none is staged as a spec in this epic.
