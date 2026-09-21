# Landing Analysis: PLAN-TRUTH-139 — `build.queue.max_slots` is dead on one path and unreconciled on the other

epic: truthful-signals
workstream: WS-01
pr: #1479 (https://github.com/cuioss/plan-marshall/pull/1479)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth — a pasted or inbox claim is a lead, never a fact.

## Verification performed

- PR #1479 corroborated first-party via `ci pr view`: `state=merged`, `merge_commit_sha=d931d8baa9477…`
  (matches both the operator paste's `d931d8baa` and the inbox landing's `pr=#1479`/`merge_state=merged`).
- Inbox landing message `plan-truth-139-007.md` cross-checked against the operator paste: `landing-check`
  reports `complete: true` (all 9 required `landing-facts` keys present with real values) — this is a
  landing that arrived complete, not the completeness gap PLAN-TRUTH-149 exists to close.
- The `plan-truth-139-001.md` filename the paste's residue section names for review-apparatus was
  confirmed to be a **different file** than this epic's own `plan-truth-139-001.md` (a candidate-lesson
  about the security-audit sweep) — each epic's inbox sequence is independent, and `review-apparatus`'s
  own tree carries its own `plan-truth-139-001.md` (a `finding`, created 13:26:27Z, earlier than this
  epic's 001 at 14:20:09Z). Not a defect — a naming coincidence across independent per-epic sequences,
  worth remembering when cross-referencing inbox filenames between epics.

## Deliverable Fidelity vs Spec

The staged spec (`plans/PLAN-TRUTH-139-…md`) named 4 deliverables (D0 gate + D1–D3). The landing reports
8. This is **shipped-expanded, not a discrepancy**: D0 is a population-derivation gate by the spec's own
design ("D0 may legitimately find it is the only member; that is a result, and it must be published as
one") — the adaptive-reap-threshold move and the config-scope population audit are exactly the kind of
additional population members D0 was scoped to surface, and the docs/skill-doc-contract deliverables are
the spec's own "say so when it does not take effect" obligation made concrete at two more sites.

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D0 — derive the population of same-shape knobs | shipped-as-specified, expanded | Landing D5 "config-scope population audit" — `machine-global-config-scope-audit.md` publishes the population and overlap |
| D1 — daemon must not silently accept an unreachable resolution | shipped-as-specified | Landing D3 "daemon re-resolves and reports its cap per submit" |
| D2 — give the cap a machine-global home | shipped-as-specified | Landing D1 "machine-global cap home + both consumers rewired", D2 "per-repo key demoted…+ migrate" |
| D3 — fallback path reports cap disagreement | shipped-as-specified | Landing D4 "fallback queue reports cap disagreement, never reconciles it" |
| (surfaced by D0) adaptive reap threshold | added, in-scope | Landing D5 (numbered "5" in the paste) |
| (obligation made concrete) skill-doc + operator/dev guides | added, in-scope | Landing D7/D8 |

## Metrics and Anomalies

- Tokens: 11,600,752 (landing-facts `total_tokens`, matches paste's "11.6M tokens")
- Wall time: paste states "9h16m worked"; `landing-facts.total_wall_seconds=450494` (~125h elapsed). These
  are two different metrics (active work vs. calendar-elapsed since the plan entered `3-outline` around
  2026-09-08) — not corroborated as a discrepancy, noted so a future reader doesn't conflate them.
- Loop-back: `loop_back_iterations=4` of `loop_back_ceiling=5` — close to the ceiling but did not exhaust it.
- Anomaly, self-reported and logged at WARNING by the plan itself: `mark-step-done` was once stamped with
  a **fabricated** `head_at_completion` (`1e2fddb7b` padded to a 40-char string instead of resolved via
  `git rev-parse HEAD`); self-caught and corrected before it shipped. Root cause and remedy captured as a
  candidate-lesson (see below) — staged as **PLAN-TRUTH-156**.
- Anomaly: two of the run's own fixes introduced the inverse of the defect they closed (`574fd5`, `9c441d`
  below) — both caught by CodeRabbit, not by any in-house gate. Captured as a candidate-lesson (Promoted).

## Routing and Merge Behavior

- Review: CodeRabbit reviewed the final head, clean after 4 firings. 17 substantive findings total this
  run (15 counted `actionable`, 2 hidden by a review-body classifier gap — see residue). Notable: `266f33`
  (Major, CWE-116) — the fifth of five unsanitised report boundaries, missed by this plan's own security
  audit, which had closed the other four.
- CI/merge: all checks green (4 firings); merged via merge queue at `d931d8baa`. No rebase conflicts or
  re-verify signals reported — no parallelization-consequence correction needed at this landing.
- Sonar: `sonar-roundtrip` reported `0 filed` with `count_status: confirmed` — but no Sonar analysis has
  ever run for this PR (gate 404, provider not activated). A `confirmed` zero here is an **empty-surface
  zero**, structurally indistinguishable from a clean scan. Filed as `367874`; recurs on every plan in
  this repo until Sonar is wired into PR CI. **Recorded as a standing epic Watch below**, not re-litigated
  per landing.

## Residue — findings routed elsewhere

Seven findings were filed rather than fixed in this landing, each already routed by the plan itself:

- **review-apparatus** (5): the participation-detector ruling (`review-apparatus/plan-truth-139-001.md`),
  `af8660` (currency test credits a bot from a comment predating the reviewed range), `867ba4` (no
  `escalate_ask` reason for "window claimed, wait delegated to orchestrator"), `5c3027` (CodeRabbit
  `rate_limit_eta_patterns` miss its own reset phrasing), `154f51` (producer-noise filter admits our own
  trigger comments as findings). Two more candidate-lessons (005, 006 below) also route there.
- **truthful-signals** (3, already in this epic's own residue): `367874` (Sonar confirmed-zero on an
  unrun analysis, Watch below), `409263` (`triage.md` prescribes `deliverable: 0` for a FIX task, which
  the validator rejects), `805bc7` (in-process build env inheritance, declined as out-of-footprint).

## Candidate-Lesson Dispositions (Step 5b)

Six `candidate-lesson` messages were filed to this epic's inbox. Each received exactly one disposition:

| Message | Title | Disposition |
|---|---|---|
| `plan-truth-139-001.md` | Derive the boundary population in a security sweep instead of enumerating it | **Promote** — new corpus lesson, component `plan-marshall:recipe-security-audit`. Recurrence of the corpus's established "derive completeness, never assert it" archetype (already tracked component-by-component, e.g. `2026-09-03-00-001`), with new concrete evidence; not a duplicate of any single existing entry. |
| `plan-truth-139-002.md` | A fix that flips a claim's truth conditions must assert both directions | **Promote** — new corpus lesson, component `plan-marshall:plan-marshall`. Distinct from the existing matched-control lessons for test batteries (`2026-09-04-08-012`, `2026-09-07-21-001`, `2026-09-11-15-001`) — this one targets the triage FIX-task specification obligation, not test authoring. |
| `plan-truth-139-003.md` | `mark-step-done` must derive `head_at_completion`, never accept it from the caller | **Stage** — new spec `PLAN-TRUTH-156`, queue row appended. No existing staged spec's Expected Surface covers `manage-status`'s `mark-step-done`; PLAN-TRUTH-154 (confident-wrong authority surfaces) and PLAN-TRUTH-144 (unreadable-write producers) were checked and neither is a clean fit. |
| `plan-truth-139-004.md` | Temp residue poisons learned build durations and silently re-tiers canonicals | **Fold** — into PLAN-TRUTH-150 ("build and CI verdicts that mislead specifically on the healthy path"), whose Objective and Expected Surface (`script-shared/scripts/build/`, `manage-architecture/`) already cover this exact mechanism class. Surface verified via `corpus surfaces` after the fold — see decision log. |
| `plan-truth-139-005.md` | A `review_body` carrying content beneath a status line must not be classified meta | **Discard** here (out of epic) — forwarded to `review-apparatus`'s own inbox as `truthful-signals-{NN}.md`. |
| `plan-truth-139-006.md` | Re-fire the pre-push quality gate after the `mutates_source` steps that follow it | **Discard** here (out of epic) — forwarded to `review-apparatus`'s own inbox alongside 005. |

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-139 --status shipped`
- [x] row `pr` stamped `1479`
- [x] row `landing` stamped `landings/PLAN-TRUTH-139.md`
- [x] row `plan_marshall_plan_id` already `plan-truth-139` (stamped in an earlier session)
- [x] epic.md queue reconciled from status.json (this landing folds no other queue row)
- [x] Watch added: Sonar `confirmed`-zero is an empty-surface zero, recurs on every plan until Sonar is
      wired into PR CI (see `367874`)
- [x] 2 corpus lessons promoted, 1 new spec staged (PLAN-TRUTH-156), 1 fold into PLAN-TRUTH-150, 2 findings
      forwarded to `review-apparatus`
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- PLAN-TRUTH-156 (new, staged): `mark-step-done` derives `head_at_completion` itself; stop accepting it
  from the caller.
- PLAN-TRUTH-150: gains a narrative note on the adaptive-timeout/temp-residue mechanism (no Expected
  Surface change — already covered).
- 2 corpus lessons promoted (security-audit population derivation; matched-controls obligation for
  truth-condition-flipping triage fixes).
- Sonar-confirmed-zero Watch stands epic-wide until PLAN-TRUTH-150-or-successor wires Sonar into PR CI, or
  a dedicated spec is staged for it.
