# Landing Analysis: PLAN-11 — audit-report-path-ignores-plan-dir

epic: code-intelligence-substrate
workstream: WS-05
pr: 1063 — https://github.com/cuioss/plan-marshall/pull/1063

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims
> against ground truth — a pasted claim is a lead, never a fact.

## Ground-Truth Corroboration

The landing was claimed three times before it was true. This record separates what was
verified from what was reported.

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1063 merged | **corroborated** | `ci pr view --head feature/audit-report-path-ignores-plan-dir` → `state: merged`; `git log origin/main` → `d0da6742d` at HEAD |
| D1 — cwd walk-up replaces `Path.cwd()` at `main()` | **corroborated** | `_resolve_repo_root()` defined at `audit.py:667`, consumed at `audit.py:7259` in `d0da6742d` |
| D2 — derived shipping predicate, `DELIVERY_COST_CHECKS` sole literal | **corroborated** | `audit.py:244` (`DELIVERY_COST_CHECKS`), `audit.py:256` (`FULL_CORPUS_CHECKS = frozenset(CHECK_NAMES) - DELIVERY_COST_CHECKS`), selector at `audit.py:1084` |
| D3 — doc port to SKILL.md + 8 `checks/*.md` | **corroborated** | `git show --stat d0da6742d` → SKILL.md + exactly 8 `checks/*.md` files changed |
| Spec HYPOTHESIS refuted (`write_persisted_report` calls `Path.cwd()`) | **corroborated** | The merge commit body states the refutation; `_resolve_repo_root` is called from `main()`, not from `write_persisted_report` |
| Mutation verification ("reverting fails exactly two tests") | **reported, not independently re-run** | Plan's own claim; the resolver regression tests exist at `test_audit_checks.py:815-876` |
| 4 branch commits | **superseded by squash** | The branch's 4 commits landed as the single squash commit `d0da6742d`; the branch SHAs (`225f3be9`, `2a471ae2`, `de6eb8be`, `2475cd17`) never reached main — see the `main_sha` defect below, which is the same fact from the other side |

⛔ **The premature-landing claim is the headline finding of this landing, not a footnote.**
Message `-001` was written at 08:05:20Z asserting "What landed — PR #1063". The PR merged at
approximately 08:31 CEST (commit `d0da6742d`, authored 10:30:57 +0200 — see the timestamp
caveat below). The message therefore preceded the merge, and the orchestrator refused it
twice on standing rule 1 before the third check corroborated it. **Emission of a
`kind=landing` message is not merge-gated.** This is the third such false-at-write-time
landing claim across the three epics. Routed to `truthful-signals` as
`code-intelligence-substrate-009.md` (their inbox's sequence, not ours).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — fix repo-root resolution at `main()` with an ADR-002 cwd walk-up | shipped-as-specified | `audit.py:667`, `audit.py:7259`; 3-branch resolver tests at `test_audit_checks.py:815-876` |
| D2 — filter delivery-cost checks on a derived shipping predicate | shipped-modified (scope widened) | `audit.py:244/256/1084/4458/6846`; the resolved `repo_root` threads into **six** consumers, not the one the spec named |
| D3 — port the changed contract surface into the auditor's documentation | shipped-as-specified | SKILL.md +52 lines and 8 `checks/*.md` in `d0da6742d` |
| (unplanned) loop-back fix — lock-step test guards the SKILL.md table | added-unplanned | Branch commit `2475cd17`, from a CodeRabbit finding |

**Scope fidelity: 3/3 shipped, one widened by verification rather than by drift.** The
widening is the plan's own correction of the spec's premise and is the epic's standing rule 4
("a reported instance is a SAMPLE") firing correctly — the named site was one of six.

## Metrics and Anomalies

- **Tokens: 3,980,943 total** for a 3-deliverable single-module bug fix.
- **Duration: 16h6m wall, 4h27m worked** — a 3.6× wall-to-worked ratio.
- **Anomalies:**
  - ⚠ **`6-finalize` alone cost 1,897,706 tokens — 48% of the plan's entire spend**, at 3h58m
    wall for 2h8m worked. This is the *second* consecutive landing in this epic where finalize
    dominates (PLAN-01 recorded finalize at 42%). Two points is a trend line worth naming, not
    yet a population.
  - ⚠ **`5-execute` wall time was 10h30m against 1h20m worked** — an 8× ratio, the largest gap
    in the table. Idle-vs-worked, not compute.
  - ⚠ The plan exceeds the `single_module bug_fix` anchor by roughly the same multiple PLAN-01
    did. Feeds the existing token-cost watch; owners remain PLAN-CIS-008 and PLAN-CIS-014.
  - ⚠ **Timestamp zones are mixed across the evidence**: inbox envelopes are UTC-stamped
    (`08:05:20Z`), the merge commit is `+0200`. Quoted times here are labelled; do not compare
    them unlabelled.

## Routing and Merge Behavior

- **Review: the shipped tree was reviewed by nobody, and every check said otherwise.**
  - pr-agent — the *required* bot — never saw `2475cd17`. Trigger B re-triggers only the
    most-recently-reviewed bot.
  - CodeRabbit declined to re-review an already-reviewed commit.
  - Sourcery was hard-quota refusing and produced no artifact — **while its check reported
    `SUCCESS`/pass throughout**, which this orchestrator independently observed in the
    pre-merge check read (10/10 SUCCESS).
  - `review_completeness check` was argparse-rejected (`exit_code=2`) at 07:48:27Z and the
    `automatic-review` step nonetheless recorded `outcome: done` at 07:49:50Z.
  - The operator merged with knowledge of the gap.
- **CI/merge:** all 10 checks SUCCESS; `mergeable`, `merge_state: clean`, not enqueued in the
  merge queue; squash-merged to `d0da6742d`. No rebase conflicts, no re-verify signals.
- **Surface collisions: none.** PLAN-11 (project auditor `audit.py`) and PLAN-02
  (`extension-api` / `manage-architecture`) ran concurrently under `parallelization_scope = 2`
  with no observed overlap. **The disjointness call was correct** — record it as a good pairing
  for future reference.
- **Operator deviations, recorded:** the trigger-A re-review gate was deliberately not re-fired
  (logged WARNING; it would have re-asked an already-answered question), and worktree removal
  timed out mid-deletion, resolved by restore-then-remove rather than `--force`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-11 --status shipped`
- [x] row `pr` stamped — `1063`
- [x] row `landing` stamped — `landings/PLAN-11.md`
- [x] row `plan_marshall_plan_id` stamped — `audit-report-path-ignores-plan-dir`
- [x] epic.md queue reconciled from status.json
- [x] Open Defect retired — `audit.py`'s `write_persisted_report` cwd derivation (the entry was
      itself based on the refuted premise; the real site was `main()` and it is fixed)
- [x] Watch updated — token-cost-above-anchor now carries a second data point
- [x] Defects/watches added from the drain (see below)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

Seven inbox messages drained with this landing (`-001` landing, `-006`…`-011` candidate-lessons):

| Message | Signal | Disposition |
|---|---|---|
| `-001` | the landing itself | reconciled (this record) |
| `-006` | unmeasurable footprint resolves to `[]` instead of UNKNOWN; pre-push-quality-gate was silently pruned and rescued only by an unrelated `qgate=always` | **folded** into PLAN-CIS-012 (footprint-read-outside-its-window) |
| `-007` | `inbox list` cannot express "consumed"; two readers erred in opposite directions | **discarded** — already in flight as sibling PR #1064 (`feature/plan-203-inbox-consumed-vs-missing`) |
| `-008` | `main_sha` captures the pinned cwd, so every worktree plan emits a false drift warning at 4-plan→5-execute | **staged** as PLAN-CIS-018 |
| `-009` | a crashed `review_completeness` does not block `mark-step-done`; check conclusions cannot express non-participation | **discarded here, delegated** to `review-apparatus` (`code-intelligence-substrate-003.md` in their inbox) — routing test 1 |
| `-010` | `check-manifest-consistency` filters `.claude/` as bookkeeping, discarding 10 of 11 files while reporting `findings: 0` | **staged** as PLAN-CIS-019, absorbing the standing M3 vacuous-guard defect |
| `-011` | Executive Summary is unrenderable yet counted as written; `dispatch_boundaries` collected then dropped | **staged** as PLAN-CIS-020 |

Plus, from the paste rather than the inbox:

- The premature-landing-claim archetype → delegated to `truthful-signals`
  (`code-intelligence-substrate-009.md` in their inbox).
- `marshal.json` provisioning stamp stale (0.1.1240 → 0.1.1270) and session restart advisable
  → Operator-Owed, already tracked.
