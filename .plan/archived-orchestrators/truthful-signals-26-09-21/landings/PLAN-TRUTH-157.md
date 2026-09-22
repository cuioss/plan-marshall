# Landing Analysis: PLAN-TRUTH-157 — Dispatch is assumed to protect judgement quality, but the write-bound half of landing analysis never leaves the calling session

epic: truthful-signals
workstream: WS-01
pr: #1494 (https://github.com/cuioss/plan-marshall/pull/1494)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth — a pasted or inbox claim is a lead, never a fact.

## Verification performed

- PR #1494 corroborated first-party via `ci pr view`: `state=merged`, `merge_commit_sha=ab86d7cbfeb7f9…`.
- Inbox landing message `plan-truth-157-032.md` cross-checked: `landing-check` reports `complete: true`.

## Deliverable Fidelity vs Spec

6/6 deliverables landed per the landing-facts block, matching the spec's D0–D5. `[LOOP_BACK]` headline:
`pre-submission-self-review` consumed all 5 admitted loop-back iterations (firing_count 6) before landing
clean, reaching the merge gate with zero remaining budget — held only because the final CodeRabbit triage
resolved its 2 findings (`00d610`, `9a819a`) as `taken_into_account` rather than requiring another fix
round. Two live, confirmed defects in `test_orchestrator_dispatch_workflow_pin.py` were deferred at the
ceiling and are owed a follow-up — **staged as PLAN-TRUTH-163.**

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D0 — re-derive population, re-confirm effort readings | shipped-as-specified | Phase Breakdown + candidate-lessons corroborate |
| D1 — refine write-freedom into draft-vs-apply | shipped-as-specified | Landed per steps |
| D2 — extend analyze.md's dispatchable envelope | shipped-as-specified | Landed per steps |
| D3 — extend decompose.md under the same boundary | shipped-as-specified | Landed per steps |
| D4 — pin orchestrator effort surfaces explicitly | shipped-as-specified | Confirmed live via `manage-config effort read` at this epic's own prior cleanup pass |
| D5 — matched controls (containment + effort-pin independence) | shipped-as-specified, with 2 deferred findings | `00d610`/`9a819a` deferred to PLAN-TRUTH-163 |

## Metrics and Anomalies (Phase Breakdown, from the operator's paste)

- Tokens: 6,778,337 total (spans populations); Billing (cost) column read is caveated by
  `adhoc-token-economy-analysis-001`'s finding that this column undercounts output 5× — **staged as
  PLAN-TRUTH-160**, which bears directly on how this very table should be read.
- Wall: 25h29m reported / 7h13m worked (n=5/6 phases) / 18h16m idle.
- `6-finalize` alone: 3h56m worked / 11h51m reported / 124,962,745 in the Billing column (see caveat
  above) — 724 tool uses, the single largest phase by every measure.
- `plan-retrospective` measured only 1 of 3 reviewers (`coderabbitai`); `cuioss-review-bot` and
  `sourcery-ai` participation was unmeasurable from the persisted store at order 990 — same
  measurement-population gap already tracked.
- Toolchain defects the retrospective surfaced in its own pipeline: `extract-chat-signal` emits a
  TOON-hostile multi-line `reduced_transcript` field; `analyze-logs` publishes only a `top_tags` sample
  with no total count for the aspect it grades. Both folded — see below.

## Routing and Merge Behavior

- Merge: squash-merged via the merge queue at `ab86d7cbf`, after contending with 3 other open PRs in the
  same queue (#1488, #1489, and this repo's own ad-hoc config PR #1495) for roughly 30 minutes.
- No rebase conflicts.

## Candidate-Lesson Dispositions (Step 5b) — 32 messages (31 candidate-lesson + 1 landing), summary

| Cluster | Messages | Disposition |
|---|---|---|
| Plan-retrospective's own measurement-pipeline bugs (TOON-hostile field, unmeasured top-tags, VERIFY tag count) | 001, 003 | Fold → PLAN-TRUTH-152 |
| Self-review loop-back budget reporting (same day as PLAN-TRUTH-148's own finding) | 002 | Fold → PLAN-TRUTH-147 |
| Terminal-step token record gap / dispatch attribution | 004, 007 | Fold → PLAN-TRUTH-149 |
| `architecture search --category` vs `--module` doc-usability nit | 005 | Discarded — minor, no defect |
| Verb-paraphrase recurrence (5 documented signatures, still recurring) | 006, 028–031 | **Staged → PLAN-TRUTH-162** (evidence) |
| Outline/refine self-review cluster (confidence-score corroboration, design-model classification, exclusion-rationale re-test, guard-criterion propagation) | 008–012 | Fold → PLAN-TRUTH-151 |
| Self-review guard/control-authoring pitfalls (sentence-vs-clause negation scope, positional indexing, matched-control-from-vocabulary-under-test, subset-transcription disagreement, per-member vacuity) | 013, 016, 017, 021, 022, 024, 026 | **Promoted** — new lesson `2026-09-15-06-002`, others folded into it as evidence |
| Deletion-over-restatement / correlation-key / cardinality-derivation process notes | 014, 015, 018, 019, 020, 023, 025 | Discarded — recurrences of already-tracked `plan-orchestrator`/self-review process lessons |
| Hardcoded surface list stays unpinned when a new surface registers | 027 | **Promoted** — new lesson `2026-09-15-06-003` (combined with `plan-truth-148-048`) |

## Reconciliation Actions

- [x] row `status` → `shipped`, `pr` → `1494`, `landing` → `landings/PLAN-TRUTH-157.md`
- [x] `plan_marshall_plan_id` already `plan-truth-157`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated; both derivable blocks regenerated via `compact`

## Follow-Ups

- PLAN-TRUTH-163 (new, staged): fix `00d610` and `9a819a` — the two dispatch-index/write-grant-detector
  defects this plan's own loop-back ceiling deferred.
- PLAN-TRUTH-160 (new, staged): the Billing (cost) 5× undercount bears on reading THIS landing's own
  Phase Breakdown table honestly.
