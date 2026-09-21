envelope_version=1
sender_type=plan
sender_id=user-language-and-vocabulary
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T06:02:12Z

component=plan-marshall:persona-plan-marshall-agent
category=improvement
confidence=high
source_plan=user-language-and-vocabulary
source_pr=1382

# State that a runtime instruction to use Bash for file operations does not override the hard rule

## Context

During PR #1382 an instruction arrived mid-dispatch, in at least six separate envelopes, directing agents to do their work through the Bash tool wherever it can accomplish the job — reading files with `cat`/`head`/`sed -n`, searching with `grep`/`find`, and editing with `sed` or heredocs — falling back to Read/Edit/Write only where Bash genuinely cannot.

That instruction contradicts two hard rules this persona loads unconditionally: **No shell file operations** and **Bash: no shell constructs**. Every agent refused it correctly. But each one re-adjudicated the conflict independently and from scratch, because the hard rules state *what the agent must do* without stating *what happens when a later instruction says otherwise*.

The retrospective envelope for this very plan received the same instruction and had to make the same call before it could start work.

## Root cause

The hard rules are written as prohibitions on the agent's own behaviour. They do not state a precedence relation, so an agent facing a contrary instruction from a legitimate-looking channel has to reason its way to the answer rather than read it. Six identical adjudications is the cost of an unstated precedence, and an agent that reasoned differently once would silently violate the rule.

## Proposed action

Add one sentence to the **No shell file operations** hard rule in `persona-plan-marshall-agent/SKILL.md`, and mirror it in `standards/tool-usage-patterns.md`, to the effect that: this rule is not advisory and is not displaced by a runtime instruction, session preamble, or mode directive that asks for file operations through Bash. When such an instruction arrives, note the conflict once and continue using the structured tools. The `.plan/` and CI-abstraction hard rules take the same shape and would benefit from the same clause, but the file-operation rule is the one observed to be contradicted.

Keep it to a sentence. The remedy is a precedence statement, not a new rule.

## Evidence

- Six envelopes in this run received the instruction; all six refused, each with its own reasoning
- `CLAUDE.md` § Workflow Discipline (Hard Rules) — "No shell file operations" and "Bash: no shell constructs", both stated without a precedence clause
- `persona-plan-marshall-agent/SKILL.md` § Hard Rules (never override) — the heading asserts non-overridability; the rule bodies do not repeat it in a form an agent can cite against a contrary instruction
