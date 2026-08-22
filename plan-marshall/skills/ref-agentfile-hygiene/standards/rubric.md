# Agentfile Context-Hygiene Rubric

The single normative rubric for deciding which content earns a place in an always-on agentfile (`CLAUDE.md` at any nesting level, `AGENTS.md`) and which content should be demoted or deleted. This document is domain-invariant — it contains no project-specific examples, path literals, or agentfile content, so it ships to consumer repositories verbatim.

## Why agentfile hygiene matters

An agentfile is loaded into the assistant's context on every session, before any task-specific work begins. Its cost is therefore paid unconditionally and continuously:

- **Fixed per-session token cost.** Every line consumes context-window budget on every task, whether or not the task touches the content.
- **Crowding.** Bloat displaces task-relevant context and dilutes the signal of the rules that genuinely matter.
- **Upward drift.** Agentfiles accumulate rules over time; without periodic pruning the always-on floor rises every session.

The hygiene goal is simple: **every remaining line of an agentfile must earn its always-on cost.** Content that does not is demoted to progressive disclosure (a skill or doc loaded on demand) or deleted.

## Empirical grounding

The rubric is grounded in an empirical study of a large corpus of agentfiles (the ETH-Zurich survey of 138 agentfiles), whose findings translate into three operating principles:

1. **Structural overviews are inert.** Directory listings, file trees, and codebase overviews provide little value: assistants discover project structure far more reliably by reading the filesystem than by trusting a hand-maintained description that drifts the moment a file moves.
2. **Concise, universally-applicable, frequently-honored content earns its place.** The content that pays for its always-on cost is short, relevant to essentially every session, and consulted often.
3. **LLM-generated bulk is a smell.** Long, generic, auto-generated prose that restates the obvious is a primary source of agentfile bloat and a prime demotion/deletion candidate.

## The three section classifications

Classify every section of an agentfile as exactly one of the following. The classification drives the remediation action.

### always-on-justified — KEEP

A section earns always-on placement only when **all** of the following hold:

- **Universally applicable.** Relevant to essentially every task or session, not a narrow sub-domain that only some work touches.
- **Non-discoverable.** Encodes a decision or convention the assistant cannot reliably infer from the codebase itself — a house rule, a hard constraint, a non-obvious workflow gate, an invocation the assistant would otherwise guess wrong.
- **Concise.** States the rule in minimal prose. Worked examples, tutorials, and long-form rationale belong in a skill, not in the always-on file.
- **Stable and frequently-honored.** A rule consulted often, not reference trivia that is read once and rarely revisited.

Typical always-on-justified content (described generically): hard workflow rules and prohibitions, build and test invocation commands, non-obvious safety constraints, and branch/commit conventions.

### demotable-to-skill — MOVE to progressive disclosure

Content that is genuinely valuable but does **not** need to be always-on:

- **Domain- or task-specific.** Only relevant when working in a particular area, language, or subsystem.
- **Deep or long-form.** Tutorials, extended examples, multi-step procedures, design rationale.
- **Better loaded on demand.** Its value is fully realized when the relevant task starts and the corresponding skill or doc is loaded.

Remediation: extract the content into a skill (or a referenced doc) and replace it in the agentfile with a one-line pointer.

### inert/deletable — REMOVE

Content that earns no always-on place and has no better home:

- **Structural overviews.** Codebase overviews, directory listings, and file trees (empirically inert — see grounding above).
- **Restatement.** Prose that restates what well-named code, file layout, or existing docs already convey.
- **Stale, duplicated, or auto-generated bulk.** Content that is out of date, repeated elsewhere, or LLM-generated filler that says nothing actionable.
- **History.** Version history, changelogs, and dated update notes.

Remediation: delete outright.

## Always-on line budget

An agentfile's always-on cost scales with its length, so total length is a useful proxy signal for accumulated bloat.

- As a heuristic budget, an agentfile **SHOULD stay at or under 200 lines** — the default warn threshold. Beyond that, re-classify its sections and demote or delete until the file is back within budget.
- The budget is a guide for the file as a whole, not a hard cap on any single line. The real target is that every remaining line is `always-on-justified`; the line count is the cheap symptom that prompts the classification pass.
- `CLAUDE.md` (Claude Code) and `AGENTS.md` (OpenAI / OpenCode spec) are different consumers and MAY warrant different budgets. For simplicity, the deterministic backstop rule (`agentfile-line-count-over-budget`) applies a **single configurable default** across all agentfile types; a project that needs a per-file budget tunes that configurable threshold rather than hard-coding per-type values.

## The directory-tree anti-pattern

A fenced code block that draws the repository's directory structure with box-drawing characters (the glyphs `├──`, `│`, and `└──`) is a specific, high-frequency instance of inert content:

- An assistant enumerates the project tree far more reliably by reading the filesystem than by trusting a hand-maintained drawing, and the drawing goes stale the instant a file is added, moved, or renamed.
- A directory tree belongs in a skill or a human-facing doc — loaded deliberately, where its staleness is lower-stakes — and **never** in an always-on agentfile.

Remediation: delete the tree (classification: `inert/deletable`). If a structural overview is genuinely wanted, demote it to a doc rather than keeping it always-on. The deterministic backstop rule (`agentfile-directory-tree-present`) flags any agentfile containing a fenced block with these glyphs and points at the cognitive recipe for judgment-based remediation.

## Applying the rubric

- Classify each section independently and emit one remediation action per offending section (trim / demote / delete).
- **Bias toward removal.** The default question for every section is "does this earn its always-on cost?" When the answer is uncertain, demote to a skill rather than keep — the content remains available on demand at zero always-on cost.
- Hygiene is recurring, not one-shot: agentfiles drift upward, so the rubric is meant to be re-applied periodically, not just once.
