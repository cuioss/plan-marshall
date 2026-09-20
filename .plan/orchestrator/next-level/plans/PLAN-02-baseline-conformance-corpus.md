# PLAN-02: Baseline conformance corpus

epic: next-level
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

## Objective

Author the first real scenario set against the hard rules whose violation costs the most, run it, and
publish the baseline. The deliverable is the **number**, not a green result: a baseline that shows
several rules failing under pressure is more valuable than one that shows everything passing, because
the second is indistinguishable from a harness that cannot detect anything.

Rule selection is by recorded cost, not by intuition. The candidates are the rules whose violations
appear in this repository's own defect record: the `.plan/`-access rule, the build-command resolution
rule, the CI-abstraction rule, and the Bash-composition rules.

## Deliverables

1. A **derived** candidate list: every rule stated in `CLAUDE.md` § "Workflow Discipline (Hard Rules)"
   enumerated, with the selection criterion applied to the whole enumeration rather than to a sample.
   ⛔ The list's completeness is itself a claim and must be derived, not asserted.
2. Scenarios for the selected rules, in PLAN-01's fixture format.
3. A baseline run and its published result, with each verdict carrying its population.
4. A negative control: at least one scenario whose rule the harness is **expected** to score
   `violated`, so a run that reports everything `held` is distinguishable from a harness that scores
   nothing. Without it the baseline cannot be read.
5. ⭐ **A baseline refresh policy.** Folded from inbox `next-level-007`. An eval is baseline-relative:
   it asks whether behaviour regressed against a recorded baseline, not whether it cleared a fixed bar.
   That makes the baseline an owned artifact with a lifecycle — when it is re-recorded, on what trigger,
   and what happens to a stored verdict when the rule under it changes. ⛔ Nobody had named this
   deliverable before the drain; a baseline with no refresh policy decays into a comparison against a
   corpus state nobody remembers, which is the stale-cache-as-evidence archetype with extra steps.

## Claim Labels

- OBSERVED: `CLAUDE.md` § "Workflow Discipline (Hard Rules)" states the rules "apply to ALL work in
  this repository" and names a single bounded exception (the standalone plan lane under `doc/plans/`)
  — read at `CLAUDE.md`. The exception is part of the population and a scenario must not test a rule
  inside a context where that rule does not bind.
- OBSERVED: A PreToolUse hook enforces part of one rule family mechanically (the "R1" family), and its
  context gate fires only inside a plan context — read at `CLAUDE.md` § "Standalone Plan Lane". ⭐ A
  rule with a mechanical enforcer and a rule with only prose behind it are **different propositions**,
  and the baseline must report which is which or its numbers are not comparable across rules.
- HYPOTHESIS: The hard-rule population in `CLAUDE.md` is the complete set of rules worth a baseline,
  and no equivalent always-binding rule set lives only in `persona-plan-marshall-agent` — confirm/
  refute at
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md`
  (verify-at-outline). ⛔ If refuted, the enumeration deliverable's population is wrong and must be
  widened before any scenario is authored.
- Verify-first clause: PLAN-01's fixture format must be read at HEAD, not recalled from this spec.
  This spec deliberately does not restate the format — it points at it, because a restatement here
  would be a second copy that drifts.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/instruction-conformance/` — the
  component PLAN-01 creates; this plan adds scenarios to it
- OBSERVED: `test/pm-plugin-development/instruction-conformance/` — the mirror test directory

⚠ **Read-only, deliberately NOT declared above**: `CLAUDE.md` is the source of the rule population and
is **read, never modified** — a scenario tests a rule, it does not rewrite one. Declaring it would
serialize every sibling behind a file this plan does not touch.

## Dependencies and Sequencing

- Depends on: PLAN-01. This plan cannot be authored against a fixture format that does not exist.
- Overlaps with: PLAN-01, by construction — both declare the same new component. Never paired.
- Adjacent to: `.claude/settings.local.json`, which carries the machine-local PreToolUse hook a
  scenario may need to reason about. It is machine-local and not in a fresh clone, so no scenario may
  depend on its presence.

## Non-Goals

⛔ No rule is edited, softened, or removed on the strength of this baseline, however it comes out. The
baseline is evidence for a decision this epic has deliberately gated behind WS-02's cross-model
signal. A `violated` verdict here means "this rule did not hold under this pressure, on this model,
on this runtime" and nothing wider.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/next-level/plans/PLAN-02-baseline-conformance-corpus.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
