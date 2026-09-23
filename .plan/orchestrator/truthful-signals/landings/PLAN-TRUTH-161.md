# Landing Analysis: PLAN-TRUTH-161 — ADR number allocation reads the local tree, so two open branches collide invisibly

epic: truthful-signals
workstream: WS-01
pr: #1586 (squash-merged as 1bd5c6a3)

> Landing record for one shipped plan. Lives at `landings/PLAN-TRUTH-161.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Corroborated against merge commit `1bd5c6a3` (`git show`: subject
`fix(adr): fail landing on duplicate ADR numbers (#1586)`, body enumerates
D0/D1/D2 file-for-file), the landed tree at HEAD, and the inbox
`landing-facts` block (`deliverables_total=3, deliverables_done=3`,
`complete: true`).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — landing-time uniqueness check | shipped-as-specified | `manage-adr.py` surfaces distinct `duplicate_numbers` named state + `error: duplicate_numbers` (lines 476–567); documented in `SKILL.md` + `phase-6-finalize/standards/adr-integration.md` § "Landing fails closed on duplicate ADR numbers" |
| D1 — matched stale-view control | shipped-as-specified | Commit stat: `test/plan-marshall/manage-adr/_manage_adr_fixtures.py` + `test_manage_adr_crud_and_numbering.py`; PR review summary confirms duplicate-detection + catch coverage |
| D2 — one header source of truth + round-trip control | shipped-as-specified | Commit stat: `adr-template.adoc` + `_cmd_validate.py` + `test/pm-documents/ref-asciidoc/test_asciidoc.py`; review summary notes template header support |
| Added-unplanned (review loop-back) | shipped-modified (scope grew, reviewed) | Malformed filenames excluded from duplicate grouping as advisory-only (`manage-adr.py:483`); scan gate wired into `branch-cleanup.md` § "ADR duplicate-number gate" (lines 1381–1414) before merge/queue dispatch |

No deliverable dropped. The loop-back additions were reviewed, not scope creep:
both close the class the spec names (a malformed name collapsing to
duplicate number 0 would have been a false positive of D0's own gate).

## Metrics and Anomalies

- Tokens: `total_tokens=0` in the landing-facts block — a zero/degraded value, not a measurement. Real spend lives in the archived plan's `metrics.md`; the zero is recorded here as a metrics-pipeline gap, not as a finding against the work.
- Duration: `total_wall_seconds=26855.0` (~7.5 h wall).
- Anomalies: `ci-verify` timed out twice against still-running remote CI, then recorded green — infra wait, no code defect (matches the folded candidate-lesson). Pre-push gate committed three one-line ruff-format blank lines in unrelated permission-fix split tests as a style commit on the branch — noted, no declaration impact (spec frozen at ship). `pre-submission-self-review` first fired against a stale local base and failed closed, then passed clean on retry (15 candidates, no findings) — the gate working as designed. `archive-plan:n/a` in steps while the plan IS archived at `.plan/local/archived-plans/2026-09-22-truth-161-adr-number-allocation/` (14 entries, full artifacts) — step-name/reporting nuance only.

## Routing and Merge Behavior

- Review: CodeRabbit summary corroborates D0/D1/D2 + loop-back items; all threads triaged per operator report; two loop-back fix tasks landed in the same PR.
- CI/merge: remote CI green on merged head per operator report; squash-merge `1bd5c6a3` on `main` corroborated locally; `landing-check` footprint base resolves to `origin/main @ 1bd5c6a3`, not stale. No rebase conflicts (squash path). `merge_state=merged`, `cleanup_owed=false` — no Watch opened.
- Pairing consequence: none. R was 1 with only 161 in flight; no supposedly-disjoint pair existed to collide, so no declared surface is implicated.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-161 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-TRUTH-161 --field pr --value 1586`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-TRUTH-161 --field landing --value landings/PLAN-TRUTH-161.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-TRUTH-161 --field plan_marshall_plan_id --value truth-161-adr-number-allocation` (sender id = archived dir slug; archived `status.json` carries no id key)
- [x] epic.md queue reconciled from status.json
- [x] no defect/watch opened or retired (no 161 narrative items outside generated blocks; residue is process noise)
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator compact` (same renderers as `resume-summary`, in-place between markers)

## Follow-Ups

- Candidate-lesson `truth-161-adr-number-allocation-001.md` (CI-wait timeout triage as infra noise): FOLDED into PLAN-TRUTH-169 narrative (adjacent D1/D4 subject; adds no file surface — decision line states so explicitly). Message archived on consume.
- Landing message `truth-161-adr-number-allocation-002.md`: reconciled here; archived on consume.
- Proactive `next` selection runs as analyze Step 4 item 7 after the ship (see session output).
