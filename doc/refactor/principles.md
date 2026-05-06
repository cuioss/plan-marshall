# Cross-Cutting Principles

These rules apply to all clusters. They are non-negotiable constraints, not suggestions.

---

## 1. Goal-Based API

Platform-runtime operations must express **intent**, not mechanism.

**Good:** `permission configure --scope project --permissions "Bash(...)"`
**Bad:** `patch-claude-settings --file .claude/settings.local.json`

The caller says what it wants (allow these scripts). The runtime decides how (patch settings file, update opencode.json, etc.).

---

## 2. Boundary Rules

Use `platform-runtime` when:
- The operation's behavior differs between Claude Code and OpenCode
- The operation touches platform settings, plugin paths, or hook mechanisms

Do NOT use `platform-runtime` for:
- CI/PR operations → `tools-integration-ci`
- Plan state → `manage-status`, `manage-tasks`
- Architecture data → `manage-architecture`
- Metrics storage/analysis → `manage-metrics` (runtime only captures; storage is internal)
- Executor regeneration → `tools-script-executor`

When in doubt, ask: "Would this work identically if I switched from Claude to OpenCode?" If yes, it belongs in plan-marshall internal.

---

## 3. No-Op Policy

If a target cannot implement an operation, it returns:

```toon
status: no-op
operation: <name>
reason: <why it cannot be done>
alternative: <what the user can do instead>
```

The caller MUST handle `no-op` gracefully and continue. Never fail a workflow because a display hook is unsupported.

---

## 4. Single Source of Truth

- Claude Code format in `marketplace/bundles/` is the only editable source
- Target outputs (`.opencode/`, `.cursor-plugin/`) are **generated artifacts**
- Body text is emitted **verbatim** — no transformation for target outputs
- Only frontmatter and manifests are transformed at build time

---

## 5. No Universal Syntax

Do not invent `{{ }}` or similar templating for cross-platform body text.

If a skill needs platform-specific behavior, that behavior goes in:
- A script behind `platform-runtime`
- A conditional instruction ("If Claude Code, do X; if OpenCode, do Y")
- A no-op with alternative

Not in the body text itself.

---

## 6. Terminology

| Use | Do Not Use |
|-----|-----------|
| target | harness |
| platform-runtime | platform abstraction layer, harness API |
| Claude Code | Claude (when unambiguous) |
| OpenCode | opencode (in code), OpenCode (in prose) |
| drift | mismatch |
| no-op | unsupported, not implemented |

---

## 7. Document Hygiene

- No version numbers or changelogs in any document
- No "Status", "Created", "Last updated" metadata
- No duplication — cross-reference instead
- Current state only — do not describe transitional information
- AsciiDoc for long-form docs (`.adoc`), Markdown for plans and skills (`.md`)
