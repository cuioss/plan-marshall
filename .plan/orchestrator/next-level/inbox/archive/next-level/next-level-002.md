envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:24:29Z

## Chronically-violated prose rules are the population for a hook-demotion survey

Source: same Day 1 whitepaper (see message 001 for provenance and the outside-document caveat).

### The observation

The paper singles out lifecycle hooks with a one-line justification that names our situation exactly:

> "Guardrails or Hooks: Deterministic code that runs at specific lifecycle points... Hooks are the place
> for things the agent should never forget but often does."

`CLAUDE.md` § Workflow Discipline opens by stating its own rules exist "because Claude regularly violates
them despite softer guidance." That is a written admission that a body of prose is carrying load prose
cannot carry. Against that population, plan-marshall runs **one** hook family — the PreToolUse R1 group,
installed machine-locally in `.claude/settings.local.json` and context-gated to plan contexts, so a fresh
clone and every cloud session carry none of it. Every other hard rule is exhortation.

### The candidate work

A survey over the hard-rule set partitioned on two independent axes:

1. **Mechanically checkable** — can a deterministic PreToolUse/PostToolUse check decide compliance without
   model judgement? (`.plan/` direct access, `gh`/`glab` direct invocation, hard-coded `./pw`/`mvn`/`npm`,
   shell file operations, temp files outside `.plan/temp/` — plausibly yes. "No improvisation in workflow
   steps" — plausibly no.)
2. **Chronically violated** — is there a violation record, or is the rule prose nobody has ever breached?

Only the intersection is hook material. The other three cells matter too: a rule that is checkable but
never violated is a candidate for **deletion** from the static tier rather than promotion, and a rule
violated but not checkable is exactly what WS-01's harness exists to put under pressure.

### Why it belongs to this epic rather than to a general cleanup

Demotion is measurable in both currencies this epic cares about. A hooked rule produces a violation count
instead of an assertion, and every rule that leaves the prose block shortens a static payload that is
present in every model call on every runtime. That is the third done-condition — the price of carrying an
instruction becoming a number — reached from the enforcement side.

⛔ This is **not** a de-escalation sweep on instruction wording, and must not be allowed to grow into one.
Demotion moves a rule from prose to code; it does not soften the rule, and it does not touch the wording
of any rule that stays.

### Status

A directional proposal grounded in our own violation record. The paper corroborates the shape and supplies
no data for it.
