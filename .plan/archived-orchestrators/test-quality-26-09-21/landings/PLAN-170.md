# Landing Analysis: PLAN-170 — Make the Attribution Usable

epic: test-quality
workstream: WS-06
pr: #1385 — https://github.com/cuioss/plan-marshall/pull/1385

> Landing record for one shipped plan. Lives at `landings/PLAN-170.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

The spec staged **four** deliverables (D1–D4); the landing reports **three** shipped
(`deliverables_total=3`, `deliverables_done=3`). The plan re-entered `3-outline` from
`5-execute` on a recorded loop-back before task planning, and the re-scope folded D3
into D1/D2's own verification rather than carrying it as a separate deliverable. That is
a legitimate re-scope, recorded here because the spec-to-landing count does not match and
would otherwise read as a dropped deliverable.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — stop resolving a `HYPOTHESIS: … (verify-at-outline)` entry into a declarative claim | shipped-as-specified | `script-shared/scripts/epic_spec_parser.py` +258; `test_epic_spec_parser.py` +679. `corpus surfaces` now resolves entry shape per entry — PLAN-140 is `derived` and PLAN-100 `prose` rather than every spec resolving alike. |
| D2 — give the attribution a sweep-plan concept | shipped-as-specified | `_epic_partition.py` +709; live `partition --epic test-quality` returns `sweep_plans[3]` = PLAN-110, PLAN-130, PLAN-135. |
| D3 — validate against the baseline the epic could not reproduce | folded into D1/D2 | Not carried as a separate landed deliverable. The validation rides D1/D2's own tests (`test_epic_report_reproducibility.py` +114). |
| D4 — report the seven root claims and the per-entry classification | shipped-as-specified | `epic-surface-derivation.md` +352; `epic-surface-partition.py` +430 (`report` verb); live partition returns `root_claims[7]`. |

**Surface under-declaration.** The spec declared four files under
`tools-epic-surface-partition/` plus its test mirror. The merge touched **15 files**,
including `plan-marshall/skills/script-shared/scripts/epic_spec_parser.py`,
`script-shared/SKILL.md`, `plan-orchestrator/templates/plan-spec.md` and
`test/plan-marshall/script-shared/`. None of those appear in `## Expected Surface`. The
plan did not collide — PLAN-150 ran entirely under `test/plan-marshall/` in directories
this diff does not touch — so the under-declaration cost nothing this round, but the gate
would have mis-predicted any pairing against a `script-shared` claimant.

## Metrics and Anomalies

- Tokens: **6,431,582** total. `6-finalize` alone is **4,000,238 — 59%** of the run on a
  15-file change, tripping all four fallback ratio thresholds with
  `retryable_total_tokens: 0`, so none of it is infrastructure retry.
- Duration: 100h36m wall, 7h12m worked (`total_wall_seconds=362167`).
- Anomalies:
  - One loop-back iteration of five, auto-continued; `5-execute` re-entered `3-outline`.
  - Three self-review rounds (3, 4, 5) each dismissed the same `_read_baseline` defect by
    reasoning from a remembered gloss rather than re-reading the text; CodeRabbit
    overturned it. Filed as corpus lesson `2026-09-03-01-001`.
  - The run bypassed the CI abstraction twice (`gh pr view --json body`) because
    `ci pr view` exposes no `body` field — a hard-rule violation the plan self-reported.
    The `direct-gh-glab-usage` detector structurally cannot see it: it reads
    `work.log`/`script-execution.log`, and neither a raw Bash call nor a `decision.log`
    self-report reaches those.
  - The plan's retrospective was dispatched with `orchestrated: false` without running the
    required resolution, so its **12 lessons went to the global corpus instead of this
    epic's inbox**. Corroborated: the inbox holds exactly one PLAN-170 message (the
    landing) and no candidate-lessons, while the global corpus carries a
    `2026-09-03-02-00X` batch of nine whose `component` and `category` are **empty** —
    the same producer gap the plan's own residue reports for `2026-09-02-15-001`.

## Routing and Merge Behavior

- Review: CodeRabbit produced **both** actionable findings and is OPTIONAL by project
  default; pr-agent, the sole default-required bot, participated twice and found nothing.
  This run overrode the bot lists plan-locally. Sourcery refused structurally on a stated
  cap of 150,000 diff *characters* measured against 4,906 changed *lines* — units that do
  not compare, a refusal firing two orders of magnitude early.
- CI/merge: merged as `6884e932902aabb8827b0f90b9932981faada61e`, base `main`, head
  `feature/plan-170-make-the-attribution-usable`. Verified via the CI abstraction
  (`ci pr view --pr-number 1385` → `state: merged`). No rebase conflicts, no re-verify
  signal. The CodeRabbit quota path resolved by releasing an hour-long cross-plan claim
  rather than holding it: the awaitable window would have bought nothing, since the real
  blocker was pr-agent going stale, which carries no rate limit.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-170 --status shipped`
- [x] row `pr` stamped `#1385`
- [x] row `landing` stamped `landings/PLAN-170.md`
- [x] row `plan_marshall_plan_id` stamped `plan-170-make-the-attribution-usable`
- [x] epic.md queue reconciled from status.json
- [x] inbox message `plan-170-make-the-attribution-usable-001.md` drained and archived
- [x] Watch opened — finalize-cost ratio (59% of run in `6-finalize`, all four thresholds tripped, zero retryable)
- [x] Open Defect opened — `direct-gh-glab-usage` cannot observe a raw Bash bypass or a `decision.log` self-report
- [x] Open Defect opened — retrospective dispatched `orchestrated: false`, routing 12 lessons past this epic's inbox
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **The derivation now reads plan lifecycle from this epic's `status.json`.** That is the
  first partition input that is not the spec corpus, and it makes the ledger's per-plan
  `status` field a machine consumer's contract: a new status value beyond
  landed/shipped/staged/running/parked raises `unknown_plan_status` rather than being
  absorbed. Recorded as an epic-level Watch, not a defect.
- ⛔ **The "12 contested modules" figure is NOT a standing property, and this reconciliation
  refuted it within one landing — its own.** Measured against the live
  `partition --epic test-quality` at three points:
  - With PLAN-150 and PLAN-170 at `running`, contested was **12**, exactly matching the
    landing's claim and its three named patterns (PLAN-155+PLAN-165 on 10 modules under
    `test/plan-marshall/manage-providers/`; PLAN-150+PLAN-160 on `test_dynamic_mypypath.py`;
    PLAN-155+PLAN-160 on `test_conftest_loader_contract.py`).
  - After this reconciliation transitioned both rows to `shipped`, contested became **186**.
  - The pair tally says why: **175 of the 186 are `PLAN-070,PLAN-150`** — and both are
    `terminal` (`landed` and `shipped` respectively, per the derivation's own
    `lifecycle_plans` mapping). Only **11** involve two active plans:
    PLAN-155+PLAN-165 (10) and PLAN-155+PLAN-160 (1). One more, PLAN-060+PLAN-090, is
    likewise terminal-vs-terminal.

  So the landing's own stated invariant — "the contested set is exactly the class the
  derivation refuses to adjudicate, modules claimed by two or more ACTIVE plans" — does not
  hold. The retirement rule resolves **active-vs-terminal** and has no rule for
  **terminal-vs-terminal**: when both claimants are terminal, neither retires the other and
  every shared module falls into contested. That is the normal case for a follow-up plan
  completing its predecessor's slice, which is precisely what PLAN-150 did to PLAN-070's
  unfinished **B6** deliverable. Recorded as an Open Defect against the shipped derivation;
  the genuinely live contested set is **11**, and that is the number `next` must sequence on.
- **Any epic reasoning that assumed exactly two sweeps is stale** — the sweep set is
  PLAN-110, PLAN-130, PLAN-135.
- **Lesson `2026-08-25-09-016` stands unfixed and was deliberately retained.** Its
  evidence cites the multiply-claimed figure this plan changed, but the plan touched
  `plan-orchestrator/templates/plan-spec.md` only — not the queue renderer or the
  disjointness gate it guards. The guarded fail-open (absence from `file_overlap_matches[]`
  read as disjointness) is still live, which is why this epic's `next` verb keeps checking
  containment by direct claimed-set read rather than trusting the matcher's silence.
