# Landing Analysis: PLAN-LB-14 — The launch gate judges each candidate against the plans that can collide with it

epic: live-blockers
workstream: WS-03
pr: #1715 (https://github.com/cuioss/plan-marshall/pull/1715)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-14.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-14-launch-gate-scope-005.md` (kind `landing`, `landing-check`
`complete: true`). Checked against `ci pr queue-state --pr-number 1715` (`pr_state: merged`,
`merge_commit_sha: 3fe828c84633c65b86ec9bd6a086132fecc652c9`, merge-group run concluded
`success`) and against `git show --stat 3fe828c84` (14 files, 2832 insertions, 350 deletions).
The PR description was read as the plan's own account; the code itself was not read line by
line for this record.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the gate compares against in-flight work only and says what it left out | shipped-as-specified | `orchestrator.py` changed (698 lines); the PR states the gate population (active epic, row `launched` or `running`, live plans), exclusions counted per reason, unreadable input kept in. The verify-first decision was settled as recommended: `staged` and `parked` siblings do not block |
| D2 — the verdict is per candidate spec | shipped-modified | `spec_comparisons[]` shipped. The epic-wide roll-up is `gate_candidates_indeterminate == 0`, which the PR calls deliberately STRICTER than the conjunction of the rows; the spec asked for the roll-up to equal the conjunction |
| D3 — a live plan with no captured footprint is compared through its source spec | shipped-as-specified, with one addition | `surface_source: affected_files / source_spec / none` shipped. Added after review: a live plan whose captured footprint cannot be read stays indeterminate and blocks (landing message, Residue) |
| D4 — `next` reads the per-candidate row; documents state the new contract | shipped, wider than specified | `orchestrate.md`, `SKILL.md`, `orchestration-model.md`, `cleanup.md` changed as specified. The overlap conjunct was changed as the clause added on 2026-10-08 asked: overlap is read against in-flight work only. It goes further than the clause: the conjunct fires only on more than one shared entry, and then puts the overlap to the operator instead of refusing |
| D5 — a regression fixture shaped like the observed store | shipped-as-specified | `test_orchestrator_corpus.py` (2230 lines changed) and `_ledger_fixtures.py`; the PR describes both the determinate case and the flipped-to-`launched` refusal |

Realized surface beyond the declaration (seven files): `plan-orchestrator/workflow/analyze.md`,
`persona-plan-orchestrator/SKILL.md`, `manage-config/standards/api-reference.md`,
`manage-config/standards/data-model.md`, `manage-config/scripts/_config_defaults.py`,
`extension-api/standards/marshal-json-reference.md` — all wording corrections under the
operator's "fix all sites" decision — and `plan-orchestrator/templates/plan-spec.md`, which the
spec had listed as a hypothesis. No other live spec of this epic declares any of the six
undeclared files. Declared and untouched: `manage-status/scripts/_cmd_sibling_collision.py`,
`test_orchestrator_read_boundary_contract.py` (both hypotheses in the spec).

## Metrics and Anomalies

- Tokens: 9,457,242 (landing facts). The plan's retrospective puts finalize at 58 percent of
  its own 7.92M count; the two totals were measured at different points and were not reconciled.
- Duration: 26,023 seconds wall time (about 7.2 hours).
- Anomalies:
  - `pre-submission-self-review` fired nine times, passed the five-round ceiling twice, and was
    closed by operator decision with `may_close=no`. The last fix commit was not re-reviewed.
    This is the defect PLAN-LB-22 exists to fix, observed on this epic's own first landing.
  - `finalize-step-lessons-housekeeping` and `finalize-step-plugin-doctor` each fired five
    times with identical verdicts (message `-001`).
  - 15 of the 18 self-review findings were wording drift between ten restatements of one rule
    (message `-002`).
  - Build time is unmeasured: 84 routed builds, no ledger row for the plan (message `-004`).
  - The landing message itself says its `emit-landing` and `archive-plan` step entries were
    written as `done` before those records existed.

## Routing and Merge Behavior

- Review: both required reviewers took part; `cuioss-review-bot` published a review with no
  findings. One review-bot comment led to a behaviour fix after the PR was opened (the
  unreadable-footprint rule). Sourcery, optional, refused the diff on size.
- CI/merge: merged through the merge queue; `finalize-step-sync-baseline` rebased onto one
  upstream commit. No conflict reported.
- Sequencing breach, recorded: the ledger held this plan until PLAN-LB-29 had landed, because
  both edit `plan-orchestrator/scripts/orchestrator.py` and `plan-orchestrator/SKILL.md`. It
  ran and landed while PLAN-LB-29 was running. Nothing collided at this merge, because this
  plan merged first; PLAN-LB-29 now has to rebase onto `3fe828c84` in those two files.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-14 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-14 --field pr --value 1715`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-14 --field landing --value landings/PLAN-LB-14.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-14 --field plan_marshall_plan_id --value lb-14-launch-gate-scope`
- [x] epic.md narrative reconciled against the queue rows (queue annotations)
- [x] Open Defect added: the outline leaf has no signal for an ambiguous change type (from PLAN-LB-22's finding)
- [x] Watches added: PLAN-LB-29 must rebase onto this landing; the new gate is not yet in the installed executor; the archived-epic tree left `main`
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated and committed with the row change

## Follow-Ups

- Message `-001` (settled steps re-fire): folded into PLAN-LB-22 as a recurrence, recorded in
  `epic.md` Queue annotations and not in the spec, because that plan is in flight.
- Message `-002` (one canonical statement, pointers elsewhere): promoted to the lessons corpus
  as `2026-10-08-15-001`.
- Message `-003` (retrospective counts a superseded exclusion): promoted as `2026-10-08-15-002`.
- Message `-004` (routed builds missing from the change ledger): folded into PLAN-LB-23 as a
  hypothesis and a verify-first clause on PLAN-LB-12 D5; no surface added.
- The new gate still refuses while a live plan has no captured footprint and no orchestrated
  source spec. Three such plans were in flight at the regrouping; whether they still are was
  not re-read here.
