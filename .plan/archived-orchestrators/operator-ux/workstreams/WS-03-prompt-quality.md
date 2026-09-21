# WS-03: Prompt-quality standard and enforcement

epic: operator-ux

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-prompt-quality.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Establish what a good `AskUserQuestion` looks like and make it checkable, so the prompts that
legitimately survive are answerable by someone who has not read the codebase. An authoring
reference already exists (`askuserquestion-patterns.md`) and is not being met, so this is a
*conformance* problem: strengthen the standard into testable rules, then give `plugin-doctor`
a rule that flags a violating prompt at authoring time. The workstream closes when a new
prompt that omits decision context, offers an option only describable in internal mechanics,
or fails to state the consequence of each choice is caught before it ships.

## Scope

- In scope: `plugin-architecture/references/askuserquestion-patterns.md` (the standard);
  the `plugin-doctor` rule catalog and the rule implementation; the definition of what an
  option must carry (consequence, default, recommendation, and a reason expressed in the
  user's terms rather than the system's).
- Out of scope: **remediating existing prompt sites** — that is WS-05, deliberately split so
  the standard can land and be enforced before a large mechanical sweep begins; the decision
  of whether a given prompt should exist at all (WS-01, WS-02); vocabulary and language rules
  (WS-04), which this standard references rather than restates.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-05-prompt-standard-and-doctor-rule | staged | Strengthen the AskUserQuestion standard into testable rules; add the plugin-doctor rule |

## Sequencing and Surface Notes

- **PLAN-05 must land before PLAN-08 (WS-05).** Remediating ~90 prompt sites against a
  standard that is still moving would mean doing the sweep twice.
- Surface is entirely inside `pm-plugin-development` — **disjoint from WS-01, WS-02 and
  WS-04**, which makes this the most parallelizable plan in the epic and a good partner for
  the second concurrency slot.
- The standard must cite WS-04's vocabulary and language rules rather than duplicating them,
  so PLAN-05 is authored to reference `persona-plan-marshall-agent` by anchor. If PLAN-06 has
  not landed, the anchor is authored as a forward reference and verified at outline.
