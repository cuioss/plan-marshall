# Requirements PR Comment Disposition

Decision criteria for disposing of automated PR review comments (gemini-code-assist, Copilot, AsciiDoc-lint, requirements-validator, traceability-checker, Sonar, etc.) on requirements documents, specifications, and acceptance-criteria artifacts. Comments reach this disposition step **after** the validity check from `dev-general-practices` (PR review hard rule): if a suggestion contradicts the plan's stated intent or driving lesson, reply-and-resolve immediately. Use this document when the suggestion is plan-compatible and you must decide between FIX, REPLY-AND-RESOLVE, or ESCALATE.

## Disposition Outcomes

| Outcome | Meaning | Required Output |
|---------|---------|-----------------|
| **FIX** | Apply the suggested change in a follow-up commit | Requirements change + thread reply linking commit |
| **REPLY-AND-RESOLVE** | Decline the suggestion; explain rationale; mark thread resolved | Reply with template; resolve thread |
| **ESCALATE** | Ambiguous; ask the user via AskUserQuestion before acting | AskUserQuestion call; record decision in lessons |

## FIX-Eligible Categories

Concrete violations of requirements-engineering standards (see `pm-requirements:requirements-authoring`, `pm-requirements:planning`, `pm-requirements:traceability`). Always FIX when the comment identifies one of these.

| Category | Example Findings | Authoritative Standard |
|----------|------------------|------------------------|
| Missing requirement ID | New requirement entry without stable `REQ-NNN` / `NFR-NNN` identifier | `requirements-authoring` (Identifier Convention) |
| Duplicate requirement ID | Two requirements with the same `REQ-NNN` (collision) | `requirements-authoring` |
| Non-SMART wording | "System should be fast" / "user-friendly" / "as needed" without measurable criterion | `requirements-authoring` (SMART) |
| Implementation leak | Requirement specifies HOW (technology, framework) instead of WHAT | `requirements-authoring` (What vs How) |
| Acceptance criteria missing | Requirement lacks Given/When/Then or testable criterion list | `requirements-authoring` (Acceptance Criteria) |
| Acceptance criteria non-testable | Criterion is opinion-based ("looks good", "feels responsive") | `requirements-authoring` |
| Traceability gap (req → impl) | Requirement has no implementation reference and is marked complete | `traceability` (Bidirectional Linking) |
| Traceability gap (impl → req) | Implementation marker (`// REQ-NNN`) without matching requirement entry | `traceability` |
| Orphaned requirement | Requirement references a removed feature; not marked superseded/deprecated | `requirements-authoring` (Lifecycle) |
| Conflicting requirements | Two requirements impose contradictory constraints on same component | `requirements-authoring` |
| Missing required metadata field | New entry lacks `priority`, `status`, `owner` per project schema | `requirements-authoring` |
| Status drift | Requirement marked `Implemented` but no impl reference exists | `traceability` |
| Plan task without requirement link | Plan task references a feature without `REQ-NNN` traceability | `planning` (Traceability) |
| Project setup gap | New requirements document missing standard top-level structure | `setup` |
| Cross-reference broken | `<<REQ-002>>` points to nonexistent or renamed requirement | `requirements-authoring` (see `ref-asciidoc` for syntax) |
| Modal verb misuse | "should" used where "shall" is required for normative requirements (per RFC 2119 / project glossary) | `requirements-authoring` (Modal Verbs) |

## REPLY-AND-RESOLVE Categories

Decline the suggestion with the corresponding template. Always reply before resolving — never resolve silently.

### False Positive

| Trigger | Reply Template |
|---------|----------------|
| Bot flags numeric `REQ-NNN` IDs as "non-descriptive" | `False positive: requirements use stable numeric IDs by policy (`requirements-authoring` Identifier Convention). Descriptive IDs break cross-doc traceability links and renaming history.` |
| Traceability bot flags missing impl link on a requirement marked `Proposed` | `False positive: status is `Proposed`; impl link is required only at `Implemented` per traceability lifecycle. No gap exists.` |
| Bot flags a requirement as "untestable" because the criterion involves business policy | `False positive: criterion is testable via `{evidence_type}` (audit log, business approval). Tooling-style "automated test" is not the only valid acceptance evidence.` |
| AsciiDoc-lint flags admonition block formatting in a requirement note | `False positive: admonition syntax is intentional per `ref-asciidoc`. Bot's "fix" would collapse multi-paragraph note into single line, losing context.` |

### Plan-Intent Contradiction

| Trigger | Reply Template |
|---------|----------------|
| Suggestion adds implementation detail to a requirement that the plan is making more abstract | `Suggestion contradicts plan intent: this PR removes implementation leakage per `{plan_id}/{lesson_id}`. Adding `{detail}` reintroduces the WHAT-vs-HOW violation.` |
| Suggestion reverts a requirement renumbering that the plan completed | `Plan renumbers requirements per `{plan_id}` (audit trail in `traceability`). Reverting breaks downstream references.` |
| Bot suggests "should" where the plan upgrades to "shall" for compliance | `Plan upgrades modal verbs to "shall" for normative compliance per `{plan_id}`. "Should" is intentionally removed.` |
| Bot proposes folding two requirements into one when the plan splits them for clarity | `Plan splits `{req}` into two requirements per `{plan_id}` for independent acceptance testing. Folding reverses the split.` |

### Scope Out of Bounds

| Trigger | Reply Template |
|---------|----------------|
| Suggestion proposes rewrite of a requirement untouched by this PR | `Out of scope: `{req_id}` is not modified in this PR. Rewrite request belongs in a dedicated requirements maintenance plan.` |
| Bot proposes adding new requirements not in the plan's scope statement | `Out of scope: this PR's scope statement does not include `{topic}`. Adding new requirements requires a separate planning iteration.` |
| Bot proposes restructuring the entire requirements directory | `Out of scope: directory reorganization affects all traceability links and requires an ADR; not in this PR's stated scope.` |
| Bot proposes adopting a new requirements management tool (Jira, ReqIF, DOORS) | `Out of scope: tooling change requires maintainer decision and migration plan; not in this PR's scope.` |

### Out of Domain

| Trigger | Reply Template |
|---------|----------------|
| Bot flags AsciiDoc-format issue inside a requirements thread | `Out of domain for this thread (requirements review). AsciiDoc formatting findings are triaged via `ext-triage-docs` and `ref-asciidoc`.` |
| Bot suggests source-code refactor based on an acceptance criterion | `Out of domain for this thread (requirements review). Implementation findings belong on the source PR; this PR is requirements-only.` |
| Bot suggests architectural diagrams (C4, UML) inside a requirement entry | `Out of domain: requirements describe WHAT, not architecture. Diagrams belong in ADRs (see `manage-adr`).` |
| Bot proposes test-case implementation inline with requirement | `Out of domain: test cases live alongside implementation, not requirements. Acceptance criteria here remain declarative per `requirements-authoring`.` |

## Escalation Triggers

Use `AskUserQuestion` when the comment falls into any row below. Do NOT silently FIX or RESOLVE.

| Ambiguity | Why It Needs Escalation |
|-----------|------------------------|
| Suggestion changes a normative ("shall") requirement that has downstream implementations | Normative changes ripple into compliance evidence; require maintainer + product owner sign-off |
| Suggestion proposes deleting a requirement marked `Implemented` | Deletion implies removed functionality; verify with maintainer that the feature is actually removed |
| Suggestion proposes splitting / merging requirements with established traceability | Trace integrity at risk; needs explicit user confirmation |
| Bot suggests changing requirement priority (e.g., MUST → SHOULD) | Priority shifts affect release planning; product-owner-level decision |
| Bot proposes adding NFRs (security, performance) on top of a functional-only PR | NFR introduction expands review scope; may need separate plan |
| Bot proposes superseding a stakeholder-approved requirement | Stakeholder reapproval required; escalate before changing |
| Suggestion conflicts between two automated reviewers (validator says A, Vale says B) | Cannot satisfy both; user must pick the authoritative linter |
| Bot suggests changing terminology in the project glossary | Glossary changes affect every requirement and downstream code; needs maintainer call |

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
| Always cite the requirement ID and the relevant `requirements-authoring` / `traceability` section that justifies the disposition | Reviewers and auditors can verify rationale without context-switching |
| Never reply "won't fix" without a category from this document | Untraceable rejections invite repeated bot suggestions on future PRs |
| Use the closing token expected by the CI provider (GitHub `Resolve conversation`; GitLab `Resolve thread`) only after the reply is posted | Resolving without a reply leaves no audit trail |
| Keep replies under 4 lines unless citing multiple standards | Long replies are skipped by reviewers; structured one-liners scale |

## Related Standards

- [severity.md](severity.md) — Severity-to-action mapping for requirements findings
- [suppression.md](suppression.md) — AsciiDoc comment-suppression syntax (delegates to `ref-asciidoc` for format-specific rules)
- `pm-requirements:requirements-authoring` — SMART, modal verbs, identifier conventions
- `pm-requirements:planning` — Plan ↔ requirement traceability
- `pm-requirements:traceability` — Bidirectional linking standards
- `pm-requirements:setup` — Project requirements directory structure
- `pm-documents:ref-asciidoc` — AsciiDoc formatting reference (cross-references, admonitions)
- `plan-marshall:dev-general-practices` — PR review hard rule (validate bot suggestions against plan intent)
