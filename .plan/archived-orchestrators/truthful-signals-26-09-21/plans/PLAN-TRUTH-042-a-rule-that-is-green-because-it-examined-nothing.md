# PLAN-TRUTH-042: an arch rule that is green because it examined nothing — second vacuity mode

epic: truthful-signals
workstream: WS-01

## Objective

⭐ **This is our flagship archetype arriving in a consuming project's gate**, and it is the **second**
vacuity mode recorded against the same skill.

Under ArchUnit's `no…` form (`noCodeUnits().should(cond)`), ArchUnit **inverts the polarity of the
condition's events**: `satisfied()` becomes a violation and `violated()` becomes a pass. A hand-written
`ArchCondition` whose `check()` reports offenders via `events.add(SimpleConditionEvent.violated(...))`
— **the natural way to write one** — therefore reports **nothing**.

⇒ **Every offender is silently reclassified as compliance and the rule stays green over an arbitrarily
dirty codebase.** Rephrasing positively (`codeUnits().should(notDeclare…)`) made it fire immediately on
a real violation the `no…` form hid.

| Mode | Mechanism | Recorded |
|---|---|---|
| 1 | `allowEmptyShould(true)` — rule matches zero classes | round-6 addendum item E |
| 2 | `no…` + `violated()` — polarity inversion | **this item** |

**Same failure, different mechanism: a rule that is green because it examined nothing.** ⚠ Our own
vacuous-guard counter stands at **n≥5**, and one prior instance was **introduced by a fix for it**.

## The generalisable remedy — this is the deliverable that matters

> ⭐⭐ **Every arch rule ships a negative control: a deliberately non-compliant fixture it must reject.
> A rule never observed to fail is not known to work.**

⇒ This closes **both** vacuity modes and every future one, because it does not depend on knowing the
mechanism. ⛔ **A fix that only documents the `no…`/`violated()` polarity closes mode 2 and leaves mode
3 open.** The polarity note is worth writing; it is not the fix.

## Second item, paired deliberately — item 14

`cui-rewrite:disable` **does not stop the upstream `AutoFormat` recipe** — the marker governs CUI
recipes only. Two OpenRewrite recipes fought over record-component indentation, producing churn no
local suppression can silence.

⚠ **Why it is paired with a vacuous arch rule rather than filed alone**: both are *a tool reporting a
state it cannot actually establish* — the arch rule reports "compliant" having examined nothing; the
rewrite set reports "formatted" while **its own output is an input to the next run**, so there is no
fixed point to report. ⭐ **Related to this repo's own lesson `2026-08-02-17-001`** (~170-file
non-idempotent import-group churn) — **same root shape, different repo**, which is why it is worth
stating as a property rather than patching a marker.

## Deliverables

1. **D0 — GATE: derive the arch-rule population and classify each by form.** Every rule in
   `arch-gate-java`, split by `no…` vs positive form and by hand-written vs built-in condition. ⛔ **Any
   `no…` rule paired with a hand-written `violated()` condition is presumed vacuous until a negative
   control proves otherwise** — do not sample.
2. **D1 — the negative-control obligation**, stated in the skill and enforced: every rule ships a
   fixture it must reject. ⛔ **Load-bearing.**
3. **D2 — document the polarity trap**: a hand-written `ArchCondition` must be paired with the positive
   rule form. **Secondary to D1, not a substitute.**
4. **D3 — retrofit negative controls to the existing population** from D0, and ⭐ **report how many
   rules were vacuous** — that count is the evidence the obligation was needed, and it is the number
   that will be asked for.
5. **D4 — the rewrite fixed-point item.** Document that `cui-rewrite:disable` governs CUI recipes only
   and does not defeat upstream `AutoFormat`; state the working remedy. ⚠ **If no local remedy exists,
   say so explicitly** — an honest "this cannot be suppressed locally, here is the upstream lever" beats
   a marker that silently does not apply.

## Claim Labels

- **REPORTED, checked first-party by the filer** at bundle 0.1.1276: the polarity inversion, that the
  positive rephrasing fired immediately on a real violation, and the `AutoFormat` marker scope.
  ⚠ **NOT re-derived by this orchestrator** — ArchUnit's `no…` event-polarity semantics are the load-
  bearing premise. ⛔ **D0 must confirm it against ArchUnit itself, not against the report**; if the
  semantics differ by ArchUnit version, the population in D0 splits by version.
- **OBSERVED (our own ledger)**: the round-6 `allowEmptyShould(true)` mode, and the vacuous-guard
  archetype at n≥5 including one instance introduced by a fix for it.
- **HYPOTHESIS**: `arch-gate-java` is the only skill shipping hand-written `ArchCondition`s. **DERIVE**
  — a second one inherits the same trap silently.
- **Verify-first clause**: D3 assumes every existing rule *can* be given a negative control. ⚠ A rule
  whose non-compliant fixture cannot be constructed is itself a finding — **record it, do not skip it**.

## Expected Surface

- **OBSERVED (per the report)**: `pm-dev-java:arch-gate-java` — rules, conditions, the skill text
- **OBSERVED**: `pm-dev-java-cui:parse-rewrite-log` — D4 only
- **HYPOTHESIS**: the arch-gate test fixtures directory — D1/D3's home

## Dependencies and Sequencing

- ✅ **DISJOINT FROM THE ENTIRE `plan-marshall` QUEUE** — `pm-dev-java*` bundle content only.
- ⚠ Adjacent to `PLAN-TRUTH-041` (same bundle). **Sequence, do not pair.**
- ⚠ **Not this epic's theme by surface, but squarely its theme by archetype.** Kept here on the
  vacuous-guard lineage rather than routed as generic Java work.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-042-a-rule-that-is-green-because-it-examined-nothing.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
