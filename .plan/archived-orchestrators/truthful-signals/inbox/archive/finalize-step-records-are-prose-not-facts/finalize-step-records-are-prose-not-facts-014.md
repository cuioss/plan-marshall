envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:18:50Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=compile_report
observed_after_report_write=true

# compile-report classifies Phase Dispatch Boundaries as a benign omission while its payload exists

## Context

`compile-report run` for this plan returned:

```
status: success
sections_omitted[2]:
  - Phase Dispatch Boundaries
  - Permission Prompt Analysis
sections_dropped[0]:
```

`Permission Prompt Analysis` is a correct omission — no fragment was registered.

`Phase Dispatch Boundaries` is not. `report-structure.md` item 5 says: "Emit only when the `dispatch_boundaries` fragment carries at least one phase entry reporting `present: true`." That data exists and is renderable — it sits inside the registered `log-analysis` fragment, whose `dispatch_boundaries` block carries three phase entries (`4-plan`, `5-execute`, `6-finalize`), all `present: true`, holding 16 rows in total. The compiler looked for a separately-registered `dispatch_boundaries` aspect key, found none, and reported a benign omission.

`dispatch_boundaries` IS in the `collect-fragments` valid-aspect registry, so a standalone fragment is the shape the consumer expects. But no aspect in `plan-retrospective/SKILL.md`'s Step 3 table produces one — `analyze-logs` emits the block nested inside `log-analysis` instead. The key has a consumer and a registry entry but no producer.

## Root cause

Producer/consumer mismatch on the `dispatch_boundaries` key, plus the omitted-vs-dropped partition keying purely on "is a fragment registered under this key" rather than on "did the data that would populate this section exist anywhere in the bundle".

The consequence is the specific failure the omitted/dropped split was introduced to prevent: `sections_omitted` is documented as "Benign: nothing was lost", and here something was. The run reports `status: success` with an empty `sections_dropped`, so a caller cannot tell a genuinely-empty section from a section whose data the compiler did not know where to find.

## Proposed action

Pick one:

1. Give the key a producer: have the retrospective register the `dispatch_boundaries` block as its own fragment (it is already deterministic output of `analyze-logs`), and add it to the SKILL.md Step 3 aspect table so it is not an undocumented side-registration.
2. Or make the section read the block from where it actually lives (`log-analysis.dispatch_boundaries`) and drop `dispatch_boundaries` from the aspect registry, so a key with no producer cannot exist.

Either way, add a check that every key in the `collect-fragments` valid-aspect registry has a producer named in the SKILL.md aspect table — a registry entry with no producer is an omission the compiler will always report as benign.

## Evidence

- `compile-report run` output for this plan: `sections_omitted` contains `Phase Dispatch Boundaries`, `sections_dropped[0]`, `status: success`
- `work/fragment-log-analysis.toon` — `dispatch_boundaries` with `4-plan.present: true` (1 row), `5-execute.present: true` (5 rows), `6-finalize.present: true` (10 rows)
- `references/report-structure.md` item 5 (the trigger condition) and § "Compiler Boundaries" ("`sections_omitted` — ... Benign: nothing was lost")
- `collect-fragments add` `valid_aspects[17]` — includes `dispatch_boundaries`
- `plan-retrospective/SKILL.md` Step 3 aspect table — no row produces it

## Note

Observed at compile time, after `quality-verification-report.md` had been written. The report's own Proposed Lessons section therefore lists seven proposals, not eight; this is the eighth.
