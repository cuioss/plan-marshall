# PLAN-PR-033: The foreign gate's blocking population, and Branch F's unreachable recovery

epic: review-apparatus
workstream: WS-04

> Staged plan spec, created 2026-08-23 by the cloud-wave ingestion. Carries the two gaps PLAN-PR-028
> deliberately left as recorded proposals because each needs an **operator decision** before any code
> may change. See `../cloud-wave-audit.md` § 8.

## Objective

Two defects in the finalize gates were analysed to a conclusion and then stopped, correctly, because
each has two defensible dispositions and choosing one silently would be worse than leaving it open.
This plan carries both to a decision and implements the chosen one. **It is operator-gated by design:
its first deliverable is an `AskUserQuestion`, not an edit.**

## Problem

**1. `020 G4` — read-intent and survey-scope foreign paths enter the blocking population.**
The foreign-PR gate selects its population by bare truthiness on the `foreign` annotation
(`foreign_pr_gate.py:207`), with no consideration of what the deliverable declared it would *do* with
the path. Two landed decisions point in opposite directions and neither is wrong:

- `deliverable_write_set` (#1283) exists precisely to say that a **read-intent** path is not part of
  what a deliverable writes; blocking a landing on a foreign repo the plan only *read* is a false
  refusal.
- `survey_scope` was added to the gate's field list **deliberately** (#1295), with a test pinning
  "the whole declared surface" — because a survey that touched a foreign repo is exactly the case where
  an unnoticed foreign commit hides.

The gap's *Done when* asks for one helper owning the rule and a gate test asserting the chosen
disposition. Neither can be written until the rule is chosen.

**2. `080 G5` — Branch F names a recovery its own `done` record suppresses.**
`branch-cleanup.md`'s Branch F closing text describes a re-entry that performs deferred cleanup. At
HEAD the F1/F2/F3 split has partly repaired this — F1 records `--outcome loop_back` and genuinely
re-enters — but F2 and F3 still record terminal `done`, and the dispatcher's only per-outcome branch is
`IF outcome == "done": SKIP this step`. So for F2/F3 the described recovery still cannot fire.

The mechanism choice alters dispatcher control flow on **every finalize run**, which is why
PLAN-PR-028 recorded it rather than taking it. Three dispositions, each with a real cost:

- record `loop_back` for F2/F3 as well — makes the recovery real, and makes two more branches re-enter;
- declare `head_dependent: true` on the step — narrower, but changes re-fire semantics globally;
- accept operator-deferred cleanup — cheapest, and requires the prose to stop promising a recovery.

## Deliverables

**D0 — GATE, mutates nothing. Put both decisions to the operator.** Present each with its options, the
landed decision that supports each side, and the consequence of each choice, via `AskUserQuestion`.
Record the outcomes. **Nothing downstream may be scoped before this returns.** If the operator defers
either question, that half of the plan stops and is reported as deferred — it is not decided by
default.

**D1 — Implement the `020 G4` disposition.** One helper owns the rule ("which foreign paths enter the
blocking population"), called from both selectors, with the chosen disposition stated in its docstring
and the reason. A gate test asserts the chosen behaviour for all three intent classes — write, read,
survey — and the pinning test's fixtures gain an `intent` key, which they lack today.

**D2 — Implement the `080 G5` disposition.** Whichever branch is chosen, the outcome is the same
invariant: **`branch-cleanup.md` promises no recovery that the recorded outcome suppresses.** If the
mechanism changes, the prose follows it; if operator-deferred cleanup is accepted, the prose says so
plainly and names who performs it.

**D3 — Pin both.** A test for each, failing against the pre-change tree, asserting the chosen
behaviour rather than the analysis.

## Claim Labels

- OBSERVED: `foreign_pr_gate.py:207` selects on `not entry.get('foreign')` — bare truthiness, no
  `intent` term. Neither foreign selector reads `intent`; `deliverable_write_set` is at
  `_plan_parsing.py:456`.
  - verdict: corroborated | checked_at: 19453cb | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 19453cb (was 7845a4b9a). METHOD CHANGED THIS PASS: intersection of the spec's DECLARED Expected Surface (via corpus surfaces, the single shared reader) against git diff --name-only 7845a4b9a..HEAD (204 paths). The former whole-spec-file method is RETIRED as non-discriminating - it scored hits on prose mentions of CLAUDE.md and .plan/marshal.json. ZERO declared paths moved in this window, so no premise of this spec was disturbed. NOT a line-by-line re-audit: this establishes the surface is UNDISTURBED, not that the premise was re-read.
- OBSERVED: the survey-scope pinning test's fixtures carry only `path`/`foreign`, no `intent`. It lives
  in `test_foreign_pr_gate.py` (`:214-243`), **not** in `test_survey_scope_declaration.py`.
- OBSERVED: `phase-6-finalize/SKILL.md:724` — `IF outcome == "done": SKIP this step` is the dispatcher's
  only per-outcome branch; `:37` bars every other skip.
- OBSERVED: `branch-cleanup.md:1707` states eight terminal `mark-step-done` sites — Branches A-E plus
  F1/F2/F3 — of which **seven record `--outcome done` and F1 records `--outcome loop_back`**.
  `:1846-1861` explains why F1 loops back and F2/F3 do not.
- HYPOTHESIS: F2 and F3 are the only remaining branches whose prose promises a recovery their outcome
  suppresses — confirm/refute by reading all eight branch bodies at outline (verify-at-outline).
- Verify-first clause: **re-derive the terminal branch set before scoping.** PLAN-PR-028's spec was
  written against a six-branch model that the F1/F2/F3 split invalidated; any count taken from that
  spec is stale.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — only if the
  `080 G5` disposition changes dispatcher semantics (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py`
  — only if the chosen rule needs a new intent accessor (verify-at-outline)

## Dependencies and Sequencing

- **Depends on: PLAN-PR-028's D4/D5** — that plan fixes the gate's *evidence* defects (the empty-`foreign`
  clear, `unpushed`, the missing `--branch`); this plan changes its *population*. Landing them in the
  other order would make this plan's tests assert against a gate still clearing on no evidence.
- **MUST NOT run concurrently with PLAN-PR-028** — same file, same test module.
- Overlaps with: PLAN-PR-027 (`phase-6-finalize/SKILL.md`, only on the `080 G5` mechanism branch).
- Adjacent to: `020 G6` — that an executing agent can ignore correct prose is the house convention for
  all eight `phase-6-finalize` scripts, not a defect of this gate. It stays an epic-level open item.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-033-the-foreign-gate-population-and-branch-f-recovery.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
