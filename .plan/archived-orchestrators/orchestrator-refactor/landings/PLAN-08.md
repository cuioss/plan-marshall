# Landing Analysis: PLAN-08 — Scope the Re-Grounding Verdict Field's staleness check to content, not raw HEAD

epic: orchestrator-refactor
workstream: WS-04
pr: #1585

> Landing record for one shipped plan. Lives at `landings/PLAN-08.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Verified against `plans/PLAN-08-verdict-staleness-scoping.md`, the merge commit
`b5d0ef7e6922e38caa4cdc8fdaaca31530c9ccd0` (confirmed as `main`'s current HEAD and an
ancestor via `git merge-base --is-ancestor`), and a live re-run of `corpus verdicts` against
this epic's own corpus post-landing.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — content-scoped staleness derivation | shipped-as-specified | `orchestrator.py` diff replaces both `_current_head_sha()` equality sites with a declared-surface tree-diff. Live-verified: a fresh `corpus verdicts` run reports `staleness_basis_tally` with 20 `declared_surface_touched` and 3 `declared_surface_unchanged` rows over this epic's own 23 claims — the mechanism is observably working, not merely present in source. |
| D2 — explicit, named fallback for non-`declarative` specs | shipped-modified (exceeds spec) | Spec asked for a named basis; shipped code publishes a full **closed six-member vocabulary** (`head_unchanged`, `declared_surface_unchanged`, `declared_surface_touched`, `surface_not_declarative`, `tree_diff_unavailable`, `verdict_unparsed` — `orchestrator.py:466-502`) with a per-row `staleness_basis` and a whole-corpus `staleness_basis_tally`, going beyond the spec's minimum ask. |
| D3 — regression tests | shipped-as-specified | New `test/plan-marshall/plan-orchestrator/test_orchestrator_verdict_staleness.py` (752 lines) plus extensions to `test_orchestrator_corpus.py` (596 lines added) — not independently re-read line-by-line, but existence, size, and the PR's own green `verify` gate corroborate the claimed coverage. |
| D4 — staleness prose updated | shipped-as-specified | `persona-plan-orchestrator/standards/orchestration-model.md` changed (+17/-notated lines in the diff stat); `plan-orchestrator/SKILL.md` and `workflow/orchestrate.md` also updated to align the consuming surface with the new per-row basis — a scope addition the spec didn't explicitly call out but is a direct, correct consequence of D2. |

Realized footprint: 6 files, 1856 insertions / 56 deletions — matches the spec's declared
Expected Surface (`orchestrator.py`, `orchestration-model.md`, `test/plan-marshall/plan-orchestrator/**`)
with two additional in-surface files (`SKILL.md`, `orchestrate.md`) that fall within the
already-declared `plan-orchestrator/**`-adjacent scope; no under-declaration.

Both of PLAN-08's own Claim Labels entries requiring settlement — the HYPOTHESIS on
`_verdict_row`/`_spec_verdict_rows` extensibility and the Verify-first line-shift clause —
were re-grounded and stamped `corroborated` against this merge commit as part of this
analysis (`corpus set-verdict`, claim_index 5 and 6).

## Metrics and Anomalies

- Tokens: 5,231,563 total across 5 measured phases. `6-finalize` (1,938,678) essentially
  matched `5-execute` (1,950,288) — the finalize gate cost as much as the change it was
  gating, against a `single_module`/`bug_fix` anchor row that warns at 800K/errors at 1.3M
  (3.9x over). Filed as candidate-lesson `2026-09-23-05-003`.
- Duration: 54,426s (~15h7m) wall time.
- Anomalies: `loop_back_iteration` reached 4; `pre-submission-self-review` fired 6 times (2
  loop-backs, 1 failure). The original CI failure at push-time was a REAL bug (an R5
  test-harness shape-guard defect), fixed in-plan rather than a false start. Two
  review-driven loop-back rounds followed a CodeRabbit finding (git-config-injection
  hazard, `5ed953`) — see Follow-Ups.

## Routing and Merge Behavior

- Review: CodeRabbit and `cuioss-review-bot` participated at an earlier HEAD; CodeRabbit's
  re-review of the final loop-back commit (TASK-010, head `8ecbc4fc`) timed out under
  hourly quota rate-limiting. Actionable finding `5ed953` (git-config-injection) was
  partially addressed — the test fixture's env scrub was hardened in-plan; broader
  production-seam hardening across `_git_read`/`_git_tree_diff`/`_resolve_anchor_sha` was
  deliberately held out of scope as a ~20-script repo-wide cross-cutting change. A
  round-2 verification-feedback triage mis-dispositioned finding `e79ee5` as `accepted`
  though its own `resolution_detail` shows it was a false positive — self-flagged by
  `review-retrospective`, not independently re-verified here.
- CI/merge: CI green at `8ecbc4fc`. Merged via the merge queue to `b5d0ef7e6`
  (**verified**: `main`'s current HEAD, ancestor-confirmed) under an explicit operator
  `barrier-ask-override` merge-authorization grant after CodeRabbit's quota timeout —
  the operator judged the staleness immaterial given prior-HEAD review participation.
  `cleanup_owed=false`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-08 --status shipped`
- [x] row `pr` stamped → `#1585`
- [x] row `landing` stamped → `landings/PLAN-08.md`
- [x] row `plan_marshall_plan_id` stamped → `verdict-staleness-scoping`
- [x] epic.md queue reconciled from status.json (PLAN-08 removed from live Ordered Queue,
      Queue annotation updated with the shipped outcome)
- [x] PLAN-07's "Depends on" note already named PLAN-08 (added when PLAN-08 was staged) —
      now satisfied; PLAN-07 is unblocked with respect to this dependency (still parked on
      operator discretion for its other reasons)
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated
- [ ] Open item: route the held-out git-config-injection production hardening (see
      Follow-Ups) — operator decision needed, not auto-resolved here

## Follow-Ups

- **Git-config-injection production hardening (~20 scripts repo-wide), CodeRabbit `5ed953`.**
  This epic's `orchestrator.py` is one instance of the pattern (`_git_read`,
  `_git_tree_diff`, `_resolve_anchor_sha`); the plan's own residue note names this epic OR
  `truthful-signals` as the two candidate homes and did not pick one. Not staged as a new
  spec here — recorded as an Open Defect in `epic.md` pending an operator routing decision,
  since a repo-wide security-hardening sweep across ~20 scripts is not obviously this
  epic's scope, and unilaterally staging it here or silently dropping it both risk being
  wrong.
- **Mis-triaged review finding `e79ee5`** (round-2 verification-feedback, this same plan) —
  recorded as a Watch: worth a spot-check if `plan-orchestrator:verification-feedback`
  triage quality is later audited. Low urgency, self-flagged by the plan's own retrospective.
- 8 candidate-lessons from this plan's retrospective, covering `platform-runtime`,
  `plan-retrospective`, `phase-6-finalize`, `manage-change-ledger`, and
  `ext-self-review-plan-marshall` — none owned by this epic, all **promoted** to the global
  lessons corpus (`2026-09-23-05-001` through `-008`) for `lessons-routing` to route onward.
