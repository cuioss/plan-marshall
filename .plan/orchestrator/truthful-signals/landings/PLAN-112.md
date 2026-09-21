# Landing Analysis: PLAN-112 — Ceremony pre-filter dropped the security audit

epic: truthful-signals
workstream: WS-01
pr: [#1055](https://github.com/cuioss/plan-marshall/pull/1055) — merged as `ad683c574`

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 — trace the `change_type` path, adjudicate the omission signal | shipped-modified | Found a **sharper mechanism than hypothesised** — not a stale metadata read; `change_type` is taken from the **first deliverable**, so a discovery-first plan reports `verification` regardless of later mutation |
| D2 — fail the security gate toward inclusion, name every drop | shipped-as-specified | `security_audit_inactive` → `security_class_inactive`; **no `change_type` leg at all**; drops only when declared affected files AND live footprint are both empty; `security_class_omitted[{step, reason}]` + `[STATUS]` line |
| D3 — four pre-fix-failing regression tests | shipped-as-specified | 24/24 finalize steps green |

⭐ **Protected population is DERIVED, not enumerated** — membership comes from existing
`persona: persona-security-expert` frontmatter, so a future security-class step is protected the day
it is added, with no edit to the gate. This is the correct answer to the archetype this epic has now
recorded six times.

⭐ **The plan reproduced its own target defect, then caught it.** Its phase-4 manifest carried
`security_audit_omitted: true` and dropped the security audit from its own finalize despite an
operator-chosen full posture. Re-composing against the fixed composer restored it (23 → 24 steps) —
**the fix validated on itself.**

## Metrics and Anomalies

- Tokens: **4.7M, 63% of it in finalize** — six review-bot barrier rounds, three self-review passes,
  four quality-gate re-stamps, two loop-backs. ⛔ **Almost none in the fix itself.** CodeRabbit rate
  limits drove much of that wall-clock. This is the strongest cost datum the epic has for the
  barrier-deadlock work (**PLAN-119**).
- `sync-baseline` rebased 3×; `pre-push-quality-gate` re-fired 4× as HEAD advanced.
- Retrospective found **five further instances of the epic's own theme inside the plan's own
  instrumentation**: `check-artifact-consistency` reporting a hard `Recall 0% FAIL` that is really
  92% (worktree deleted before it ran), `metrics.md` understating tokens **2.7×**, `execution_log`
  silently stopping at the 13:21 loop-back, `extract-chat-signal` returning fully green after
  discarding **1128 of 1131 turns**.

## Routing and Merge Behavior

- Review: `automatic-review` 6 iterations, quorum proven; `sonar-roundtrip` 0 new-code issues
  (confirmed); 2 reviewers compared.
- Merge: squash-merged; worktree removed; tree clean.

⭐ **Two self-corrections the plan volunteered, both worth keeping:**

1. **It reported the merge blocked and needing operator intervention. It was not.** `pr auto-merge`
   worked; `autoMergeRequest: null` was a **stale read of async remote state treated as definitive**.
   Two findings were filed off it — one now **rejected-as-contradicted**, the other narrowed to an
   open question. ⭐ **This INVERTS the epic's theme**: the plan had learned to distrust green and
   trusted **red** instead. A false negative from a stale read is the same defect wearing the
   opposite sign.
2. **It recommended `safe-merge` as "the documented remedy"** without checking — `safe-merge` is not
   available on a required queue. Corroborates **PLAN-117**'s scoping.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1055; `landing` = landings/PLAN-112.md;
      `plan_marshall_plan_id` = ceremony-prefilter-dropped-the-security-audit
- [x] The premature-landing-message defect entry CORRECTED (see epic.md Open Defects)
- [x] 15 inbox messages received (8 drained earlier, 8 later batch)

## Follow-Ups

1. **`change_type` from the first deliverable** — Open Defect; lesson `2026-07-29-18-002`. Still live
   at every other consumer, explicitly `finalize-step-simplify`'s `simplify_inactive`.
2. **Lesson `2026-07-16-20-001` was TRIMMED, not closed** — its root cause stays live for
   `finalize-step-simplify`. Ready-made follow-up.
3. **The third `_resolve_footprint` call site is still deferred** (CodeRabbit named two; real count
   three) — Open Defect, and another instance of *a reviewer's list is a SAMPLE*.
4. **The five instrumentation defects** — forwarded to `code-intelligence-substrate` (measurement is
   their column).
