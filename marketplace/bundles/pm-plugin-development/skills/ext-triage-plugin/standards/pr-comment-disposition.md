# Marketplace Plugin PR Comment Disposition

Decision criteria for disposing of automated PR review comments (gemini-code-assist, Copilot, plugin-doctor, markdownlint, ruff/mypy, Sonar, etc.) on marketplace plugin artifacts (skills, agents, commands, scripts, plugin.json, marketplace.json). Comments reach this disposition step **after** the validity check from `dev-general-practices` (PR review hard rule): if a suggestion contradicts the plan's stated intent or driving lesson, reply-and-resolve immediately. Use this document when the suggestion is plan-compatible and you must decide between FIX, REPLY-AND-RESOLVE, or ESCALATE.

## Disposition Outcomes

| Outcome | Meaning | Required Output |
|---------|---------|-----------------|
| **FIX** | Apply the suggested change in a follow-up commit | Plugin change + thread reply linking commit |
| **REPLY-AND-RESOLVE** | Decline the suggestion; explain rationale; mark thread resolved | Reply with template; resolve thread |
| **ESCALATE** | Ambiguous; ask the user via AskUserQuestion before acting | AskUserQuestion call; record decision in lessons |

## FIX-Eligible Categories

Concrete violations of marketplace plugin standards (see `pm-plugin-development:plugin-architecture`, `pm-plugin-development:plugin-script-architecture`, `pm-plugin-development:plugin-doctor`). Always FIX when the comment identifies one of these.

| Category | Example Findings | Authoritative Standard |
|----------|------------------|------------------------|
| Missing frontmatter field | SKILL.md / agent.md / command.md missing `name` or `description` | `plugin-architecture` (Frontmatter) |
| Invalid frontmatter type | `user-invocable: "true"` (string) instead of boolean, `tools:` as YAML array instead of comma-separated string | `plugin-architecture` |
| plugin.json registration drift | Skill is `user-invocable: true` or context-loaded via `Skill:` directive but absent from plugin.json | `plugin-architecture` (plugin.json Registration Convention) |
| plugin.json over-registration | Script-only skill (`user-invocable: false`, only 3-part script notation) listed in plugin.json | `plugin-architecture` |
| Script notation mismatch | Script invoked as `{bundle}:{skill}:{script}` but file path doesn't follow `marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}` | `plugin-script-architecture` |
| Direct `.plan/` access in script | Script reads/writes `.plan/` directly instead of through `manage-*` API | `plugin-script-architecture`, `dev-general-practices` Hard Rules |
| Missing Enforcement block | Script-bearing skill lacks `## Enforcement` block | `plugin-architecture` (Enforcement Block Pattern) |
| Plugin-doctor `error` finding | Rule 8 (absolute paths in non-bootstrap), Rule 9 (script invocation discipline), Rule 10a (Enforcement block existence) | `plugin-doctor` |
| Skill output not TOON | New script prints `json.dumps(...)` instead of `serialize_toon(...)` per project migration | `plugin-script-architecture`, `ref-toon-format` |
| Tool-name casing wrong in adapter target | Frontmatter declares `read`/`write` (OpenCode form) instead of `Read`/`Write` (Claude form) for source files | `plugin-architecture` (Multi-Assistant Support) |
| Hard-coded build command in script | Script invokes `./pw`, `mvn`, `npm`, `gradle` directly instead of resolving via `manage-architecture:architecture resolve` | `dev-general-practices` Hard Rules |
| Direct `gh` / `glab` call in script | Script uses CLI directly instead of `tools-integration-ci:ci` abstraction | `dev-general-practices` Hard Rules |
| Test missing for new script | New script under `marketplace/bundles/*/skills/*/scripts/` has no corresponding test in `test/` | `plugin-script-architecture` (Testing) |
| Script test bypasses executor | Test calls script via `PYTHONPATH=... python3 path/to/script.py` instead of via `execute-script.py` | `dev-general-practices` (no smoke-tests via PYTHONPATH) |
| Component name not kebab-case | File or skill name uses `camelCase` or `snake_case` instead of project's kebab-case | `plugin-architecture` (Naming) |
| Missing standards/ subdir for declarative content | Skill bundles standards inline in SKILL.md instead of under `standards/` | `plugin-architecture` |
| Adapter compatibility break | Skill uses Claude-only tool (`Task`) without exclusion in adapter for OpenCode export | `plugin-architecture` (Multi-Assistant Support) |

## REPLY-AND-RESOLVE Categories

Decline the suggestion with the corresponding template. Always reply before resolving — never resolve silently.

### False Positive

| Trigger | Reply Template |
|---------|----------------|
| markdownlint MD041 on SKILL.md / agent.md / command.md (YAML frontmatter precedes first heading) | `False positive: YAML frontmatter precedes the heading by spec; documented in ext-triage-plugin standards as a known false-positive class.` |
| MD013 (line length) on a wide standards table | `False positive: tables in `standards/*.md` cannot wrap without losing column alignment; documented exception in suppression.md.` |
| F401 (unused import) on `__init__.py` re-export | `False positive: import is a public-API re-export; required for downstream consumers.` |
| Plugin-doctor flags a bootstrap script for absolute paths | `False positive: bootstrap scripts (`generate_executor.py`, init scripts) intentionally use absolute paths during initial setup; documented exception in plugin-script-architecture.` |
| Bot flags `tools:` as comma-separated string and suggests YAML array | `False positive: Claude Code frontmatter requires `tools:` as comma-separated string, not YAML array (see plugin-architecture Frontmatter section).` |
| Bot flags `description:` containing a colon as malformed | `False positive: description is properly quoted (`"Analyze: find issues"`). Bot regex misclassifies the inner colon.` |

### Plan-Intent Contradiction

| Trigger | Reply Template |
|---------|----------------|
| Suggestion reverts a notation rename done by the plan | `Suggestion contradicts plan intent: this PR migrates `{old_notation}` → `{new_notation}` per `{plan_id}/{lesson_id}`. Reverting reintroduces the deprecated notation.` |
| Suggestion adds a script-only skill back to plugin.json after the plan removed it | `Plan removes script-only skills from plugin.json per the registration convention (see plugin-architecture). Re-adding violates the convention this PR enforces.` |
| Suggestion reintroduces JSON output where the plan migrated to TOON | `Plan migrates script output JSON → TOON per `{plan_id}` (see ref-toon-format). Reverting to `json.dumps` contradicts the migration intent.` |
| Suggestion adds direct `.plan/` Read/Write where plan moved access through `manage-*` | `Plan enforces `.plan/` access via manage-* scripts only (dev-general-practices Hard Rule). Direct access is the explicit anti-pattern this PR removes.` |
| Suggestion reintroduces a hard-coded `./pw`/`mvn`/`npm` after migration to architecture-resolved commands | `Plan migrates to architecture-resolved commands per `{plan_id}/{lesson_id}`. Hard-coded build invocations are the anti-pattern this PR eliminates.` |
| Suggestion reintroduces direct `gh`/`glab` after migration to `tools-integration-ci` | `Plan migrates CI calls through `tools-integration-ci:ci` abstraction. Direct `gh`/`glab` is the anti-pattern this PR removes (see feedback_ci_abstraction_over_gh).` |

### Scope Out of Bounds

| Trigger | Reply Template |
|---------|----------------|
| Suggestion proposes refactoring a skill untouched by this PR | `Out of scope: `{skill}` is not modified in this PR. Refactor request belongs in a dedicated `plugin-maintain` plan.` |
| Bot proposes adding new bundles or skills not in the plan | `Out of scope: new component creation goes through `plugin-create` workflow, not inline in PR review.` |
| Bot proposes restructuring the marketplace directory layout | `Out of scope: directory layout is fixed by `plugin-architecture`; structural changes require an ADR and migration plan.` |
| Bot proposes adopting a new adapter (Cursor, Cody) | `Out of scope: adapter additions follow the `Adding New Adapters` workflow with a maintainer-approved spec; not in this PR's scope.` |
| Bot suggests reorganizing the executor mapping format | `Out of scope: executor format is generated; changes go through `marshall-steward` + `generate_executor.py`, not editing executor output (see feedback_never_edit_generated_executor).` |

### Out of Domain

| Trigger | Reply Template |
|---------|----------------|
| Bot suggests Java/JS pattern in a Python script | `Out of domain: script is Python; suggestion is `{lang}` syntax. Python equivalent is already in use at line {N}.` |
| Bot flags a generated file (e.g., `.plan/execute-script.py`) | `Out of domain: file is generated by `generate_executor.py`. Edits must go through the generator, not this file (see feedback_never_edit_generated_executor).` |
| Bot proposes runtime-environment changes (Python venv, package manager) inside a plugin code review thread | `Out of domain for this thread (plugin code review). Toolchain findings belong on infra PR.` |
| Bot suggests OpenCode-specific syntax in source file | `Out of domain: source files use Claude Code format; OpenCode form is generated by the adapter (see plugin-architecture Multi-Assistant Support).` |
| Bot complains about marketplace.json schema drift on a bundle plugin.json edit | `Out of domain for this thread (bundle plugin.json review). marketplace.json findings belong on a dedicated marketplace-config PR.` |

## Escalation Triggers

Use `AskUserQuestion` when the comment falls into any row below. Do NOT silently FIX or RESOLVE.

| Ambiguity | Why It Needs Escalation |
|-----------|------------------------|
| Suggestion changes a public skill notation (e.g., `bundle:skill:script`) used by other components | Notation changes propagate; verify all callers and lessons before accepting |
| Suggestion proposes splitting / merging bundles | Bundle topology change affects every component manifest and the marketplace.json; needs maintainer call |
| Suggestion proposes promoting a skill from `user-invocable: false` to `true` (or vice versa) | Visibility change affects user discoverability; needs maintainer + UX consideration |
| Bot proposes deprecating or removing a skill referenced by other plans | Removal impact spans plans; verify no in-flight plan depends on it |
| Suggestion proposes a new architectural rule (new plugin-doctor rule, new enforcement block requirement) | Rule additions affect every existing skill; needs ADR-level decision |
| Bot proposes a new build command, executor subcommand, or `manage-*` API verb | API surface additions affect downstream callers; needs maintainer review |
| Suggestion conflicts between two automated reviewers (plugin-doctor says A, mypy says B) | Cannot satisfy both; user must pick the authoritative tool |
| Bot suggests removing a hard rule from `dev-general-practices` | Hard rules are intentional (per `feedback_dev_general_hard_rules`); never remove without explicit user direction |
| Bot proposes a new adapter target without a spec | Adapter additions affect long-term maintenance; needs maintainer decision |
| Suggestion proposes reordering or skipping execute-task profile steps | Workflow shape is contractual; profile changes affect every plan execution path |

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
| Always cite the plugin-doctor rule number, frontmatter field, or `plugin-architecture` section that justifies the disposition | Reviewers can verify rationale without context-switching |
| Never reply "won't fix" without a category from this document | Untraceable rejections invite repeated bot suggestions on future PRs |
| Use the closing token expected by the CI provider (GitHub `Resolve conversation`; GitLab `Resolve thread`) only after the reply is posted | Resolving without a reply leaves no audit trail |
| Keep replies under 4 lines unless citing multiple standards | Long replies are skipped by reviewers; structured one-liners scale |

## Related Standards

- [severity.md](severity.md) — Severity-to-action mapping for plugin findings
- [suppression.md](suppression.md) — Suppression syntax (Python, markdown, plugin-doctor)
- `pm-plugin-development:plugin-architecture` — Architecture, frontmatter, registration conventions
- `pm-plugin-development:plugin-script-architecture` — Script implementation and testing standards
- `pm-plugin-development:plugin-doctor` — Quality gate rules
- `plan-marshall:dev-general-practices` — PR review hard rule (validate bot suggestions against plan intent)
- `plan-marshall:ref-toon-format` — TOON output format for scripts
