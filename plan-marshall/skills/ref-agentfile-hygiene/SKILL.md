---
name: ref-agentfile-hygiene
description: Agentfile context-hygiene rubric — objective criteria classifying every CLAUDE.md/AGENTS.md section as always-on-justified, demotable-to-skill, or inert/deletable, plus the always-on line budget and directory-tree anti-pattern; the shared source of truth for the recipe and the plugin-doctor backstop rules
user-invocable: false
mode: knowledge
implements: ref
---

# Agentfile Hygiene Rubric

**REFERENCE MODE**: This skill provides reference material. Load the rubric on-demand when auditing, trimming, or gating an agentfile.

An **agentfile** is an always-on instruction file an AI coding assistant loads into context every session — `CLAUDE.md` (Claude Code) and `AGENTS.md` (OpenAI / OpenCode spec). Because the file is always-on, every line carries a fixed per-session token cost and competes for the context window; agentfiles drift upward over time as rules accrue. This skill carries the objective, domain-invariant rubric for deciding which sections earn that always-on cost.

The rubric is the single normative source of truth consumed by BOTH halves of the agentfile-hygiene capability:

- the cognitive sweep `plan-marshall:recipe-agentfile-hygiene`, which classifies each section and emits one remediation deliverable per offending section; and
- the deterministic `pm-plugin-development:plugin-doctor` backstop rules `agentfile-line-count-over-budget` and `agentfile-directory-tree-present`.

Consumers reference the rubric — they MUST NOT restate its content — so the LLM recipe and the deterministic rules stay in sync by construction.

## Enforcement

**Execution mode**: Reference library; load the rubric standard on-demand.

**Prohibited actions:**
- Do not restate or duplicate the rubric in a consuming skill, rule, or doc — reference `standards/rubric.md` instead.
- Do not add project-specific examples, path literals, or agentfile content to the rubric — it is domain-invariant and ships to consumer repos verbatim.

**Constraints:**
- `standards/rubric.md` is the single normative source for every enforcement-critical hygiene criterion.
- The rubric is agentfile-type-agnostic: it applies to `CLAUDE.md` (every nesting level) and `AGENTS.md` alike.

## Rubric

```text
Read: standards/rubric.md
```

The rubric covers: the empirical grounding for agentfile hygiene; the three section classifications (`always-on-justified` | `demotable-to-skill` | `inert/deletable`) with concrete criteria; the always-on line budget (default 200 lines, with the per-consumer budget note); and the directory-tree anti-pattern.

## Related Skills

- `plan-marshall:recipe-agentfile-hygiene` — cognitive sweep that consumes this rubric and emits remediation deliverables
- `pm-plugin-development:plugin-doctor` — deterministic backstop rules that embody the rubric's line-budget and directory-tree criteria
- `plan-marshall:tools-sync-agents-file` — distinct concern: creates/updates `AGENTS.md` per the OpenAI spec (this skill audits and trims existing agentfiles)
