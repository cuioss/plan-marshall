# Landing Analysis: PLAN-TRUTH-144 — the lessons corpus and producers that report success over a write nothing can read

epic: truthful-signals
workstream: WS-01
pr: #1560 (https://github.com/cuioss/plan-marshall/pull/1560)

> Landing record for one shipped plan. Written by the `analyze` verb after
> verifying the operator's paste against ground truth: `git log`/`merge-base`
> for the commit, and the archived plan's own `status.json`/`metrics.md` for
> the token/loop-back figures. No inbox landing message existed for this plan
> (paste mode, not inbox-scan) — the plan filed its lessons directly into the
> global corpus rather than through the orchestrator inbox this time.

## Deliverable Fidelity vs Spec

- **manage-lessons three-state resolution (found/absent/unreadable)** — shipped-as-specified. Confirmed by PR title: "fix(manage-lessons,manage-metrics): close write-success-over-unreadable-record gaps (#1560)".
- **CodeRabbit-caught crash fix (uncaught `UnicodeDecodeError` in `resolve_lesson`)** — shipped, applied inline after the self-review ceiling blocked the normal loop-back path (per operator's paste — not independently re-read against the diff, taken as a first-party operational note).

**Not independently re-derived**: the full deliverable list against `solution_outline.md` was not re-read line-by-line for this report.

## Metrics and Anomalies

- Tokens: 7,921,882 total (`status.json`), confirmed. `metrics.md` shows `6-finalize` as the dominant phase: ~5.05M dispatched tokens, 820 dispatch calls, ~16h elapsed. The operator's paste figure (63% / 4.8M tokens, 2h42m) is directionally consistent (finalize clearly dominant) but not an exact match to the raw table figures read here — treated as a corroborated-in-direction, not byte-exact, claim.
- `loop_back_iteration: 15` in `status.json` — consistent with the paste's "hit the 14-round loop-back ceiling" (14 loop-backs → iteration 15).
- **Anomaly — two independent loop-back ceilings hit in the same run.** Per the paste: `pre-submission-self-review` and the post-merge unified triage both hit the 14-round ceiling. The operator stopped the first and hand-fixed the second rather than continuing to loop. This is a first-party operator observation, not independently re-derived from logs for this report.
- **Anomaly — a merge-queue wait-loop hung once**, recovered by re-enqueuing directly and polling manually (operator's own account of this session; matches the general pattern this epic already tracks around merge-queue robustness, e.g. PLAN-TRUTH-063/PLAN-PR-009).
- Lessons corpus activity: 4 new lesson files (`2026-09-21-13-001` through `-004`, mtimes ~15:24–15:26) and apparent recurrence-append touches to two pre-existing lessons (`2026-09-21-10-001`, `-10-005`, both re-modified ~15:26) are visible on disk, roughly matching the paste's "4 new lessons plus 3 recurrence appends" (the third recurrence append was not independently located).

## Routing and Merge Behavior

- Review: CodeRabbit and `cuioss-review-bot` both needed explicit re-trigger comments — per the operator, neither auto-re-reviews on push under this repo's current bot config. Not independently re-verified against `.plan/marshal.json`'s `required_bots`/`optional_bots` for this report.
- CI/merge: `merge_state: merged`, `cleanup_owed: false` (`status.json`). Merge commit `05b5d1ac4` confirmed as an ancestor of `main` via `git merge-base --is-ancestor`, and local `main` was fast-forwarded to include it.
- The merge got stuck once on a hung `ci pr merge-queue` wait-loop; the operator recovered by re-enqueuing directly and polling themselves rather than relying on the original wait. Worth watching for recurrence (see Follow-Ups).

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `1560`
- [x] row `landing` stamped → `landings/PLAN-TRUTH-144.md`
- [x] row `plan_marshall_plan_id` stamped → `lessons-corpus-producers-report-success`
- [x] epic.md queue reconciled from status.json (Ordered Queue regenerated)
- [x] Watch added — a `ci pr merge-queue` wait-loop hung once this run; recovered by manual re-enqueue+poll. Not yet a confirmed pattern (n=1 first-party sighting), but matches this epic's standing merge-queue-robustness theme.
- [x] Watch added — plan-retrospective flagged 4 unreadable lessons in the corpus from an earlier plan's write pattern, and an `allowed-tools: Grep` declared-but-denied-at-runtime gap — both explicitly marked by the plan as needing operator judgment, not blocking.
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated (`orchestrator resume-summary`, hand-applied due to the worktree read/write resolution gotcha — not relevant here since this reconciliation ran directly in the main checkout)

## Follow-Ups

- **Two independent 14-round loop-back ceilings hit in one run** (`pre-submission-self-review`, post-merge unified triage), one hand-fixed rather than looped through — the plan's own retrospective already filed 4 new lessons + append recurrences about this, including one specifically about the pre-submission-self-review non-convergence witnessed here. No new epic-level action needed beyond what the plan's own lessons capture already recorded; flagged here so a future cleanup pass cross-checks those lessons for promotion/staging when the inbox next drains from a source that routes through it.
- **A hung `ci pr merge-queue` wait-loop, recovered manually** — one first-party sighting this session (independent of the two hangs/mid-worktree issues this orchestrator hit earlier on PLAN-TRUTH-143's own PRs #1564/#1567). Worth a dedicated finding if it recurs a third time; not staged as its own plan yet.
- **4 unreadable lessons + an `allowed-tools: Grep` gap** — explicitly flagged by the plan's retrospective as needing operator judgment, not blocking. Left as a Watch (see epic.md) rather than staged, since no concrete remedy was proposed in the paste.
