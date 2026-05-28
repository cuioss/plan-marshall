---
name: ref-narrative-styles
description: Reference library of narrative styles for technical documentation — tone, voice, structure, and pain-point/response/limit arcs per surface (concept pages, user guides, spec references)
user-invocable: false
---

# Narrative Styles Skill

A reference library of writing styles for the project's documentation tree. Each style document captures the narrative shape, voice, and tone rules for one documentation surface — concept page, user guide, spec reference, etc. The SKILL.md is the index; the actual style guidance lives under `styles/`.

## Enforcement

**Execution mode**: read-only. Load the style document that matches the surface you are authoring or revising. Apply the rules in the document to the prose you write. Do not transform existing prose without an explicit task to do so.

**Prohibited actions:**

- Do not invent new styles inline. If the surface you are authoring does not match an existing style document, surface the gap to the user before authoring a new style here.
- Do not blend styles. A page is written in one voice; the style document for its surface is the authoritative source for that voice.
- Do not export style rules to other surfaces by analogy. Concept-page tone is concept-page tone; spec-reference tone is its own register.

**Constraints:**

- Style documents under `styles/` are markdown reference docs, not executable workflows. They name patterns and anchor them to worked examples in the live documentation tree.
- Every style document carries an explicit "When to use this style" section so a writer can pick the right one without guessing.
- Worked examples are linked to the live merged files on `main` — when those files change shape, the style document's worked-example reference may need to be re-anchored.

## When to use this skill

Load this skill when:

- Authoring a new page in the documentation tree (`doc/concepts/`, `doc/user/`, `doc/developer/`).
- Rewriting an existing documentation page in a target voice (e.g., bringing a concept page up to the established narrative bar).
- Reviewing documentation prose against a style for consistency.

Do not load this skill when:

- Writing code, code comments, or test artefacts. The styles here are for prose-heavy documentation surfaces.
- Authoring `SKILL.md` files or `standards/` documents inside marketplace bundles. Those have their own enforcement-block conventions per `pm-plugin-development:plugin-architecture`.
- Writing commit messages, PR descriptions, or chat replies. The styles here are too long-form for those surfaces.

## Styles

| Style document | Surface | What it sounds like | Reference page on `main` |
|----------------|---------|----------------------|---------------------------|
| [`styles/concept-page.md`](styles/concept-page.md) | `doc/concepts/*.adoc` | Matter-of-fact, slightly self-ironic about LLM behaviour, third-person present tense. Opens with a pain point from stock Claude Code, describes the structural response Plan Marshall makes, names the honest limit. Bounded length (`==` sections only; no `====`). | `doc/concepts/process-enforcement.adoc`, `doc/concepts/security.adoc` |

## Future styles

The library is intentionally small at first. Add a new style only when an actual documentation surface needs one — premature style codification produces dead documents.

Slots that are likely worth filling later:

- `styles/user-guide.md` — second-person ("you"), task-shaped, walks the reader through a concrete operational sequence. Surface: `doc/user/*.adoc` (e.g. `getting-started.adoc`, `installation.adoc`).
- `styles/spec-reference.md` — third-person, dense, contract-precise, no narrative arc — the prose equivalent of an API spec. Surface: `marketplace/bundles/.../standards/*.md`.
- `styles/recipe-runbook.md` — imperative, numbered, deterministic — for procedural runbooks. Surface: `doc/developer/manual-sync-recovery.adoc` and similar.

When the time comes to add one, anchor it to a worked example on `main` first; then write the style document from the worked example, not from theory.

## Related

| Resource | Purpose |
|----------|---------|
| [`pm-documents:ref-asciidoc`](../ref-asciidoc/SKILL.md) | AsciiDoc syntax + formatting standards — the *how* of writing AsciiDoc; this skill is the *voice* of what you write in it. |
| [`pm-documents:ref-documentation`](../ref-documentation/SKILL.md) | Content quality, tone analysis, organization standards — the broader review surface this skill plugs into. |
| [`pm-documents:ref-svg-diagrams`](../ref-svg-diagrams/SKILL.md) | The sibling reference library for visual narrative — every concept-page style that asks for a diagram should reach for the matching diagram type in this skill. |
