# Documentation PR Comment Disposition

Decision criteria for disposing of automated PR review comments (gemini-code-assist, Copilot, AsciiDoc-lint, markdownlint, link-checker, Sonar, etc.) on documentation files (AsciiDoc, ADRs, interface specifications, markdown). Comments reach this disposition step **after** the validity check from `dev-general-practices` (PR review hard rule): if a suggestion contradicts the plan's stated intent or driving lesson, reply-and-resolve immediately. Use this document when the suggestion is plan-compatible and you must decide between FIX, REPLY-AND-RESOLVE, or ESCALATE.

## Disposition Outcomes

| Outcome | Meaning | Required Output |
|---------|---------|-----------------|
| **FIX** | Apply the suggested change in a follow-up commit | Documentation change + thread reply linking commit |
| **REPLY-AND-RESOLVE** | Decline the suggestion; explain rationale; mark thread resolved | Reply with template; resolve thread |
| **ESCALATE** | Ambiguous; ask the user via AskUserQuestion before acting | AskUserQuestion call; record decision in lessons |

## FIX-Eligible Categories

Concrete violations of documentation standards (see `pm-documents:ref-asciidoc`, `pm-documents:ref-documentation`, `pm-documents:manage-adr`, `pm-documents:manage-interface`). Always FIX when the comment identifies one of these.

| Category | Example Findings | Authoritative Standard |
|----------|------------------|------------------------|
| Broken cross-reference | `xref:missing-anchor[...]`, `<<missing-id>>`, dead `link:` URL | `ref-asciidoc` (Cross-References) |
| Broken external link | 404 on documented URL, redirect chain to unrelated content | `ref-asciidoc` (Link Verification) |
| Missing blank line before list | List item directly after paragraph without blank line (renders as paragraph) | `ref-asciidoc` (List Formatting) |
| Heading level skip | `==` directly after `=` then `====` (skips `===`) | `ref-asciidoc`, markdownlint MD001 |
| Missing required ADR section | New ADR lacks Context / Decision / Consequences | `manage-adr` |
| Outdated ADR status | ADR status remains `Proposed` after merge, or `Accepted` on superseded record | `manage-adr` |
| Interface spec missing required field | New interface lacks `version`, `producers`, `consumers` field | `manage-interface` |
| Duplicate definition across docs | Same concept defined in two places without cross-reference | `ref-documentation` (No Duplication rule) |
| Version history / changelog added | "Recent Changes", dated update sections, version numbers in body | `ref-documentation` (No Version History rule) |
| Timestamps in body | Dates added to document content (other than ADR/release metadata) | `ref-documentation` (No Timestamps rule) |
| Source-block language tag missing | `[source]` without language for syntax highlighting (`[source,java]`) | `ref-asciidoc` |
| Table column drift | Header column count differs from row column count | `ref-asciidoc` (Tables) |
| AsciiDoc admonition misuse | `NOTE:` followed by multi-paragraph block without `====` delimiters | `ref-asciidoc` |
| Markdown lint `error` level | MD040 fenced code without language, MD034 bare URL outside angle brackets | markdownlint config |
| Tone / voice violation | Marketing language ("blazingly fast", "revolutionary") in technical doc | `ref-documentation` (Tone Analysis) |
| Inconsistent terminology | Same concept named two ways within same document (e.g., "task" and "step" interchangeably) | `ref-documentation` |

## REPLY-AND-RESOLVE Categories

Decline the suggestion with the corresponding template. Always reply before resolving — never resolve silently.

### False Positive

| Trigger | Reply Template |
|---------|----------------|
| Link checker reports 403/429 on a rate-limited but valid URL | `False positive: `{url}` returns 403/429 due to rate-limiting, not a dead link. Verified manually; `// skip-link-check` annotation is the documented pattern (see suppression.md).` |
| Bot flags AsciiDoc passthrough block (`++...++`) as malformed markdown | `False positive: file is AsciiDoc, not markdown. Passthrough syntax is intentional and documented in ref-asciidoc.` |
| MD041 (first line heading) on a SKILL.md / agent.md with YAML frontmatter | `False positive: YAML frontmatter precedes the first heading by spec; markdownlint rule does not account for frontmatter (documented in ext-triage-plugin standards).` |
| Bot flags numeric anchor IDs (`[[REQ-001]]`) as "non-descriptive" | `False positive: requirements docs use stable numeric IDs for traceability (see `requirements-authoring`); descriptive anchors break cross-doc references.` |

### Plan-Intent Contradiction

| Trigger | Reply Template |
|---------|----------------|
| Suggestion adds version-history section on a plan removing version history per `ref-documentation` | `Suggestion contradicts plan intent: `ref-documentation` mandates "No version history". This PR removes the changelog per `{plan_id}/{lesson_id}`. Reverting reintroduces the anti-pattern.` |
| Suggestion proposes splitting a doc that the plan is consolidating | `Plan consolidates `{topic}` into a single canonical document per `{plan_id}`. Splitting reverses the consolidation goal.` |
| Bot suggests duplicating content for "discoverability" instead of cross-reference | ``ref-documentation` "No duplication" rule mandates cross-references. Duplication is the explicit anti-pattern this PR removes.` |
| Bot suggests adding dates / timestamps for "freshness" | `Project policy ("No timestamps") forbids dates in document body. Freshness is tracked via git history, not body content.` |

### Scope Out of Bounds

| Trigger | Reply Template |
|---------|----------------|
| Suggestion proposes rewrite of a section untouched by this PR | `Out of scope: `{section}` is not modified in this PR. Rewrite request belongs in a dedicated documentation maintenance plan.` |
| Bot proposes converting AsciiDoc to markdown (or vice versa) | `Out of scope: format conversion requires an ADR; not in this PR's stated scope. AsciiDoc is the documented project standard.` |
| Bot proposes adding diagrams (PlantUML, Mermaid) when the PR is a text edit | `Out of scope: diagram authoring is a separate task; not the focus of this PR.` |
| Bot proposes glossary / index for unchanged content | `Out of scope: glossary is tracked as a separate maintenance task, not a merge blocker for this content edit.` |

### Out of Domain

| Trigger | Reply Template |
|---------|----------------|
| Bot flags markdownlint rule on an `.adoc` file | `Out of domain: file is AsciiDoc, not markdown. markdownlint rules do not apply (see ref-asciidoc for AsciiDoc-specific lint).` |
| Bot suggests Sphinx / RST syntax in AsciiDoc | `Out of domain: project uses AsciiDoc, not RST. Sphinx-only directives have no AsciiDoc equivalent in this stack.` |
| Bot flags code-quality issue inside a documentation code block | `Out of domain for this thread (documentation review). Code blocks in docs are illustrative; code quality findings belong on the source PR, not the doc PR.` |
| Bot complains about i18n / translation strategy | `Out of domain: project documentation is single-language by policy; i18n is not in this PR's scope.` |

## Escalation Triggers

Use `AskUserQuestion` when the comment falls into any row below. Do NOT silently FIX or RESOLVE.

| Ambiguity | Why It Needs Escalation |
|-----------|------------------------|
| Suggestion changes the documented behavior of a public API in a doc-only PR | Doc PRs are not the place to ratify API changes; verify the source-of-truth code matches |
| Suggestion proposes superseding an existing ADR with a new one | ADR supersession is a maintainer decision; never accept inline |
| Suggestion proposes adding or removing an Interface specification record | Interface contract changes require explicit user confirmation per traceability rules |
| Bot proposes a tone shift across documents (e.g., from formal to conversational) | Tone is a project-wide editorial decision; needs maintainer sign-off |
| Bot proposes restructuring document organization (TOC, top-level headings) | Structural reorganization affects all consumers of the doc; needs maintainer call |
| Bot suggests deleting a doc as "obsolete" | Deletion requires confirming no consumers (cross-refs, links, code citations) — escalate |
| Bot proposes converting between content formats (AsciiDoc ↔ markdown ↔ HTML) | Format change is an ADR-level decision |
| Suggestion conflicts between two automated reviewers (markdownlint says A, Vale says B) | Cannot satisfy both; user must pick the authoritative linter |

## Disposition Flow

```
Bot comment received
  ↓
Plan-intent check (dev-general-practices PR review rule)
  Contradicts plan? → REPLY-AND-RESOLVE (Plan-Intent Contradiction)
  ↓
Match FIX category from table above?
  Yes → FIX (apply change, reply with commit link)
  ↓
Match REPLY-AND-RESOLVE category?
  Yes → reply with template, mark resolved
  ↓
Match Escalation Trigger?
  Yes → AskUserQuestion, record decision in lessons
  ↓
Default → ESCALATE (do not silently fix or resolve unknown categories)
```

## Reply Quality Rules

| Rule | Rationale |
|------|-----------|
| Always cite the AsciiDoc / markdownlint rule id or `ref-documentation` section that justifies the disposition | Reviewers can verify rationale without context-switching |
| Never reply "won't fix" without a category from this document | Untraceable rejections invite repeated bot suggestions on future PRs |
| Use the closing token expected by the CI provider (GitHub `Resolve conversation`; GitLab `Resolve thread`) only after the reply is posted | Resolving without a reply leaves no audit trail |
| Keep replies under 4 lines unless citing multiple standards | Long replies are skipped by reviewers; structured one-liners scale |

## Related Standards

- [severity.md](severity.md) — Severity-to-action mapping for documentation findings
- [suppression.md](suppression.md) — AsciiDoc / markdown comment-suppression syntax
- `pm-documents:ref-asciidoc` — AsciiDoc formatting and validation
- `pm-documents:ref-documentation` — Content quality, tone, and review standards
- `pm-documents:manage-adr` — ADR format and lifecycle
- `pm-documents:manage-interface` — Interface specification format
- `plan-marshall:dev-general-practices` — PR review hard rule (validate bot suggestions against plan intent)
