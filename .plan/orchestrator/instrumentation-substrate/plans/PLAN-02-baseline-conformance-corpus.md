# PLAN-02: Baseline conformance corpus

epic: instrumentation-substrate
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
   **AND** every always-binding rule in `persona-plan-marshall-agent/SKILL.md` § "Hard Rules (never
   override)" and `standards/tool-usage-patterns.md`, enumerated, with the selection criterion applied
   to the whole enumeration rather than to a sample. ⛔ **Population widened at cleanup 2026-09-22** —
   see Claim Labels: `CLAUDE.md` alone is refuted as the complete population. The list's completeness
   is itself a claim and must be derived, not asserted.
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
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: CLAUDE.md verbatim at HEAD: applies to ALL work, one bounded exception (doc/plans/)
- OBSERVED: A PreToolUse hook enforces part of one rule family mechanically (the "R1" family), and its
  context gate fires only inside a plan context — read at `CLAUDE.md` § "Standalone Plan Lane". ⭐ A
  rule with a mechanical enforcer and a rule with only prose behind it are **different propositions**,
  and the baseline must report which is which or its numbers are not comparable across rules.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: CLAUDE.md Standalone Plan Lane table + .claude/settings.local.json PreToolUse matcher-less group confirm the R1 enforcer
- ⛔ **REFUTED at cleanup 2026-09-22 (was HYPOTHESIS).** The hard-rule population in `CLAUDE.md` is NOT
  the complete set of rules worth a baseline. `persona-plan-marshall-agent/SKILL.md` § "Hard Rules
  (never override)" carries 5 always-binding rules absent from `CLAUDE.md` (e.g. "Bash: Timeout from
  architecture-resolved canonical command", "Subagents are leaves — no further dispatch", "Git
  targeting: … never `cd {path} && git`"), and `standards/tool-usage-patterns.md` carries 5 more
  (env-var dispatch in Bash, no heredocs with `#` lines, no sleep for external waits, the
  `TERM_PROGRAM`-only env-var read allow-list, authoring file contents via Bash forbidden in every
  shape). **Consequence, absorbed into this spec's scope**: deliverable 1's enumeration is widened to
  span all three sources (see Deliverables). Shared refutation with PLAN-08 idx 3 (same population,
  same artifacts) — reconcile the two enumerations rather than deriving the population twice.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: persona-plan-marshall-agent/SKILL.md Hard Rules (5 extra) + tool-usage-patterns.md (5 extra) absent from CLAUDE.md; deliverable 1 widened; shared with PLAN-08 idx3
- Verify-first clause: PLAN-01's fixture format must be read at HEAD, not recalled from this spec.
  This spec deliberately does not restate the format — it points at it, because a restatement here
  would be a second copy that drifts.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/instruction-conformance/` — the
  component PLAN-01 creates; this plan adds scenarios to it
- OBSERVED: `test/pm-plugin-development/instruction-conformance/` — the mirror test directory

⚠ **Read-only, deliberately NOT declared above**: `CLAUDE.md`, `persona-plan-marshall-agent/SKILL.md`
and `standards/tool-usage-patterns.md` (the widened population, per Claim Labels) are all **read, never
modified** — a scenario tests a rule, it does not rewrite one. Declaring them would serialize every
sibling behind files this plan does not touch.

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
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-02-baseline-conformance-corpus.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
