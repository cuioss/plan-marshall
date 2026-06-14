---
name: ref-narrative-styles
description: Reference library of narrative styles for technical documentation — tone, voice, and structural arcs per genre (engineering-narrative, future user-guide / spec-reference / runbook)
user-invocable: false
mode: knowledge
---

# Narrative Styles Skill

A reference library of writing styles for prose-heavy documentation. Each style document captures the narrative shape, voice, and tone rules for one documentation genre. The SKILL.md is the index; the actual style guidance lives under `styles/`.

## Enforcement

**Execution mode**: read-only. Load the style document that matches the genre you are authoring or revising, and apply its rules to the prose you write. Do not transform existing prose without an explicit task to do so.

**Prohibited actions:**

- Do not invent new styles inline. If the document genre does not match an existing style document, surface the gap to the user before adding one here.
- Do not blend styles. A document is written in one voice; the style document for its genre is the authoritative source for that voice.

**Constraints:**

- Style documents under `styles/` are markdown reference docs, not executable workflows.
- Every style document carries an explicit "When to use this style" section so a writer can pick the right one without guessing.
- New styles are anchored to a worked example before they are codified; theory-only style documents do not earn a slot.

## When to use this skill

Load this skill when:

- Authoring a new prose-heavy document and looking for the right voice.
- Rewriting an existing document to bring it up to an established narrative bar.
- Reviewing documentation prose against a style for consistency.

Do not load this skill when:

- Writing code, code comments, or test artefacts.
- Authoring `SKILL.md` files or `standards/` documents inside marketplace bundles — those follow plugin-architecture conventions, not narrative styles.
- Writing commit messages, PR descriptions, or chat replies — the styles here are too long-form for those surfaces.

## Styles

| Style document | Genre | What it sounds like |
|----------------|-------|----------------------|
| [`styles/engineering-narrative.md`](styles/engineering-narrative.md) | Documents that motivate a piece of engineering — design RFCs, concept pages, the narrative section of an ADR. | Matter-of-fact, slightly self-ironic, third-person present tense. Opens with the problem, describes the structural response, names the honest limit. |

## Adding a new style

Add a new style only when a real documentation genre needs one — premature style codification produces dead documents. When the time comes, find a worked example in the repository first, then write the style document from the example rather than from theory.

## Related

| Resource | Purpose |
|----------|---------|
| [`pm-documents:ref-asciidoc`](../ref-asciidoc/SKILL.md) | AsciiDoc syntax and formatting — the *how* of writing AsciiDoc; this skill is the *voice* of what you write in it. |
| [`pm-documents:ref-documentation`](../ref-documentation/SKILL.md) | Content quality, tone analysis, organization — the broader review surface this skill plugs into. |
| [`pm-documents:ref-svg-diagrams`](../ref-svg-diagrams/SKILL.md) | The sibling reference library for visual narrative — when a narrative document reaches for a diagram, that skill carries the per-type standards. |
