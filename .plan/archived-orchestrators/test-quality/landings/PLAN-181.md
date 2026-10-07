# Landing Analysis: PLAN-181 — Run 3 Carve 2 — tools-permission-fix Source

epic: test-quality
workstream: WS-04
pr: https://github.com/cuioss/plan-marshall/pull/1582

> Landing record for one shipped plan. Lives at `landings/PLAN-181.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Corroborated against the real diff (merge commit `1a9a672`, squash of PR #1582), the
`origin/main` tree, and read-only CI state. The working tree predates the merge
(local HEAD `faec2caa`, uncommitted-scope pending operator decision), so all file
evidence comes from the git objects, not the checkout.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — Re-derive source scope at dispatch | shipped-as-specified | PR body records the re-derivation: 2 files over budget at dispatch HEAD (1618, 1587 lines), 65 `monkeypatch` + 287 `tmp_path` hits — matches the nomination shape (small source, setup-dense). Consistent with the pre-landing measurements already stamped on the spec's claims. |
| D2 — Fixture hoist + splits, no behavior change | shipped-as-specified | Merge commit stat: `_permission_fix_fixtures.py` +198, 10 `test_*` splits (max 382 = `test_consolidate_apply.py`), 2 originals deleted (−1587 `test_permission_fix_behavior.py`, −1618 `test_permission_fix.py`); 13 files, +3279/−3205. `origin/main` tree confirms exactly these 11 files in the source, both originals absent. A Sourcery-driven follow-up commit (dead local helpers, 5 files, 145 deletions) rode the same PR — within the carve, no new surface. |
| D3 — Fidelity proof | shipped-modified | pytest 141 passed both orders (preserved); AST test functions 124 preserved. `_fidelity_diff` reports lost=124/gained=124 on path-qualified identities — this is the file-move axis, `Class::test` names unchanged. `_definition_duplication` introduced=0; `_banner_attribution` introduced=0 (2 pre-existing fixed). ⚠️ The spec's done-when "lost=0/gained=0" is unmet **in letter**: the instrument is path-sensitive, so splits can never report 0/0 on path-qualified identities. Known instrument limitation, disclosed by the plan and filed to `.plan/orchestrator/process-compliance/inbox`. Fidelity in substance is preserved (assertion count + identity name-match). |
| D4 — Green both orders + doctor clean | shipped-as-specified | pytest default + reverse green (141 passed), no new skips; doctor `test-conventions` error-0 (budget 0, down from 2 at merge HEAD); quality-gate green. CI corroborated at the drain: 10/10 checks success (Python Verify + gate ×2 runs, dependency-review, Sourcery review). |
| D5 — Per-PR review logging | shipped-as-specified | `skip-bot-review` label y; CodeRabbit skipped y (label-intended, informational notice only): the CodeRabbit check row reads SUCCESS/no-op. Sourcery present y — 1 nitpick triaged FIX, re-review Approved, thread cleared. Corroborated via `ci pr reviews`: sourcery-ai DISMISSED (2026-09-22T11:44:28Z) → APPROVED (13:37:48Z). No human reviews outstanding. |

## Metrics and Anomalies

- Tokens: `total_tokens=0` in the landing-facts block — read as **unmeasured**, not a
  measured zero (same convention as PLAN-180's "no figure reported — not zero").
  No per-phase figures surfaced; none recorded here.
- Duration: not reported in the landing payload.
- Anomalies:
  - 3-line ruff-format churn (commit `ade0e8ee2`) never pushed: the merge queue froze
    the head (GH006) and CI stayed green without it, so format is **unenforced** on
    merged triage PRs. The churn was discarded with the local branches post-merge —
    nothing wrong shipped. Watch added (WS-03 candidate).
  - PR body text stale by the time of landing (single-commit/13-files prose vs the 2
    PR-branch commits), because the Sourcery cleanup commit was appended after the body
    was authored. Disclosed in the landing message; per-spec D5 log lines live there.
  - Fidelity instrument path-sensitivity (filed to process-compliance): a `Class::test`
    split can never report lost=0/gained=0 under path-qualified identities.
  - Fresh verification worktree retired post-verification; branch deleted post-merge.

## Routing and Merge Behavior

- Review: `skip-bot-review` label skipped CodeRabbit (quota saved, informational only);
  Sourcery 1 nitpick → triaged FIX → re-review APPROVED → inline thread cleared. No
  human review required; no human feedback outstanding.
- CI/merge: 10/10 checks green at merge; merge via the merge queue (squash), landed as
  `1a9a67229` — identical to `origin/main`'s tip at the drain. No rebase conflicts, no
  re-verify signal, no collision with any sibling or live plan.
- ✅ **The emit gate override is vindicated in practice.** The 47 `file_overlap_matches`
  rows disposed inert at the A4 pass stayed inert: the carve touched exactly
  `test/plan-marshall/tools-permission-fix/` and zero live sibling claims moved against
  it. Same shape as the PLAN-165 override vindication — and, like that one, the safety
  came from a *machine-checkable* disposition (the live corpus read at emit), not from
  a judgement that the overlap "looked unlikely".

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-181 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-181 --field pr --value #1582`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-181 --field landing --value landings/PLAN-181.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-181 --field plan_marshall_plan_id --value run-3-carve-2-tools-permission-fix`
- [x] epic.md queue reconciled from status.json — PLAN-181 landing section added; emit annotation stands as history
- [x] Watch added — ruff-format unenforced under merge-queue freeze (GH006), WS-03 candidate
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary` (one invocation emits both)

## Follow-Ups

- **Carve 3 (tools-permission-doctor) not staged** — standing just-in-time discipline:
  one carve per emission, staged on operator order. The next emission's natural
  candidate when ordered.
- **PLAN-140 parked** — claims 1/2 re-scope owed (attribution vs archived sibling
  specs structurally vacuous); row waits on the operator's disposition. Pre-existing,
  carried in the anchor.
- **Note surfaced, WS-03 candidate:** ruff-format is not enforced by CI on merge-queue
  triage heads (the dropped `ade0e8ee2` churn proves it). Watch added; stage on demand.
- Pre-existing (carried): 7 dangling `landings/PLAN-NNN.md` refs in `settled.md`; the
  operator's commit-scope decision on 103 uncommitted paths (5 epic-own).