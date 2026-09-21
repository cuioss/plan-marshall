# Landing Analysis: PLAN-22 — the permission-grammar residue and the direct-route false zero

epic: multiplattform
workstream: WS-03
pr: #1452 (https://github.com/cuioss/plan-marshall/pull/1452)

> Landing record for one shipped plan. Lives at `landings/PLAN-22.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

Drained from `inbox/permission-grammar-residue-001.md`, corroborated against the merged diff
(`a88976a`), the CI abstraction, and the change ledger. **This closes coupling-inventory §B rows 5
and 6 — the last two unowned rows in §B.**

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| **D1** — `permission_fix.py`'s permission-DSL residue | **shipped-as-specified** | `_decline_non_claude(operation)` gated on `is_claude_target()` across **eight** DSL-emitting subcommands; `remove-redundant` propagates the `skipped` third state. |
| **D2** — `permission_doctor`'s direct-route false zero | **shipped-as-specified** | All three `detect-*` subcommands return `status: 'skipped'` on a non-Claude target instead of walking empty allow lists to a zero. |
| *(shared seam)* | **emergent, undeclared** | `permission_common.is_claude_target()` — one predicate both deliverables needed. |

## ⭐ D1 re-derived its symbol set, and in a better unit than the spec asked for

The spec's verify-first clause was explicit that the inventory's **seven symbols** were a *lead, not
a measurement*, and named PLAN-10's own refuted count (2 claimed → 7 actual) as the reason to
distrust it. The plan did not transcribe the list. It re-derived the residue in a different **unit**
— **eight subcommands**, the behavioural surface where the DSL actually escapes to a caller, rather
than seven constants and helpers scattered inside the module. Both the unit and the count differ
from the inventory's, which is what distinguishes a genuine re-derivation from a restatement.

⭐ The tests carry that through: each names **what would otherwise have been emitted** — *"not
timestamp wildcards"*, *"not `Skill(...)` rules"*, *"not the executor permission"*, *"not a
normalized render"*. These are behavioural assertions about the declined output, not structural
assertions that a guard exists.

## ⭐ D2 shipped the matched positive control — which is what makes the whole deliverable falsifiable

Three tests assert `status == 'skipped'` on a non-Claude target. On their own they would prove only
half of ADR-019: that the non-Claude route no longer returns a zero. The deliverable is the
*distinction*, and the test that establishes it is the fourth one:

> `"""On a Claude target with empty allow list: 'success' with zero (genuine zero)."""`

⭐ **This is the matched positive control the landing checks asked for.** Without it, a change that
simply made `detect-*` always return `skipped` would pass every other test in the class while
destroying the ability to report a real clean result. With it, "checked, found nothing" and "could
not check" are pinned apart in both directions — which is precisely the `could-not-evaluate reported
as a clean zero` class this epic has recorded eight times, now closed at one of its sites with an
instrument that can detect its own regression.

## Under-declaration: 2 of 6 — and it is NOT the in-flight-widening mechanism

Realized **6** paths against **4** declared entries; **2 undeclared**:

- `tools-permission-doctor/scripts/permission_common.py` — the shared `is_claude_target()` seam
- `tools-permission-fix/SKILL.md` — documenting the new decline behaviour

Against the series (PLAN-11: 15, PLAN-10: 19, PLAN-21: 0) this is a small, ordinary emergence: two
deliverables needed one predicate, so a helper appeared beside them **inside the same two skill
trees the spec already declared**. No change of kind, no operator authorisation, no seam-wide blast
radius.

⚠️ **But the spec's own same-act instruction did not bind, and that is worth recording.** PLAN-22
was the first spec staged carrying the obligation explicitly — and it was worded as *"if D1's remedy
turns out to need a platform-runtime op … it updates this section in the same act"*. D1's remedy
needed a **shared helper**, not a platform-runtime op, so the instruction's antecedent was never
satisfied and the surface was not updated. ⛔ **The instruction was too narrowly worded**: it named
the *specific* widening shape that had just burned PLAN-10 rather than the general one (any new file
this plan creates or touches). The general form is what the next spec should carry.

⭐ **No scope creep.** The three permission standards documents — `permission-architecture.md`,
`permission-validation-standards.md`, `permission-anti-patterns.md` — are absent from the diff, as
the spec's Out of Scope required. The settled PLAN-14 provenance declaration was not reopened.

## ✅ The §B-versus-§C question is settled — PLAN-22 was scoped correctly

PLAN-10's hand-off described the split as leaving "§C 5/6" open; I scoped PLAN-22 to **§B** rows 5
and 6 on the evidence of `a7ca9e491`'s diff and flagged the discrepancy rather than resolving it
silently. This landing's own report states it "closes multiplattform **§B** rows 5 and 6". The
flag resolves in favour of the diff-based reading; **PLAN-10's landing follow-up F2 is closed**, and
no re-staging is needed.

## Metrics and Anomalies

- **Tokens: not reported.** `landing-check` → `complete: false`, `missing_keys: [total_tokens]`.
  **9-for-9 on the OpenCode lane** — folds into the standing entry.
- ⭐ **Test count STABLE — the fourth reading closes the instability question.** 24773 → 20736 →
  25254 → **25270** (+16). After a dip and a full recovery, the count has now held across two
  consecutive gates. A structural instability is not supported by four readings; the remaining
  point is unchanged and unglamorous — nothing in the pipeline compares one gate's count to the
  last, which is why establishing this took four landings and manual arithmetic.
- **Build gate green — FOURTH consecutive substantively-clean post-merge case.** Ledger row
  `2026-09-08T15:17:23Z`, `exit_code: 0`, `tests_run: 25270`; merge at `16:18:39Z`; parent
  `fa5a7cdce` (#1451) landed `14:22:26Z`, ~55 minutes before the verify, and **nothing landed in the
  61-minute window**. Verified tree equals merged tree. ⭐ Note also that this run's ledger
  `--project-dir` is **absolute** — see the environment note below.

## Routing and Merge Behavior

- **Review:** CodeRabbit obtained; **both** findings fixed. Pre-PR verifier cleared after 2 rounds.
- **CI/merge:** merged via the merge queue as `a88976a`, confirmed an ancestor of `origin/main`.
  Branch prefix `fix/` — canonical. Worktree removed, branch deleted, main pulled.

## Environment notes carried from the run

- ⭐ **The relative `--project-dir` form double-nests under the build daemon** (it re-invokes the
  worktree executor from the worktree cwd); the absolute path works. **This is a live confirmation
  of exactly what PR #1445 documents** (`docs(developer): document the --project-dir and basetemp
  gate footguns`), which has now been open across three landings. The footgun is not theoretical —
  it was hit in this run. ⛔ This raises #1445 from housekeeping to the fix for a reproduced defect.
- ⚠️ **The general sub-agent endpoint returned a model error in this environment**, so the
  verification rounds used `explore` instead. Recorded in the run report. Not a plan defect; an
  environment fact that changed how verification was performed, and therefore something a reader
  comparing this run's verification depth against others needs to know.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` `#1452`; `landing` `landings/PLAN-22.md`; `plan_marshall_plan_id` `n/a`
- [x] epic.md narrative reconciled from status.json
- [x] Open Defect — landing incomplete (`total_tokens`), folded as the 9th instance
- [x] Watch CLOSED — test-count instability, on the fourth stable reading
- [x] Watch updated — the same-act obligation's wording is too narrow (added to the in-flight-widening defect)
- [x] PLAN-10 follow-up F2 (§B vs §C) — CLOSED, scoping confirmed
- [x] resume_anchor updated; START-HERE and Ordered Queue regenerated

## Follow-Ups

- **F1** ⛔ **PR #1445 should merge.** It documents the exact `--project-dir` footgun this run hit,
  and it is the last piece of PLAN-21's work not on main.
- **F2** The `is_claude_target()` seam now exists in `tools-permission-doctor/scripts/permission_common.py`.
  ⚠️ It is a natural attractor for other target-conditional logic; if a later plan needs the same
  predicate from outside these two skills, that is a relocation question, not a copy.
