# Cross-Cutting Principles

These rules apply to all clusters. They are non-negotiable constraints, not suggestions.

---

## 1. Goal-Based API — semantic in, normalized out

Platform-runtime operations express **intent**, and they carry **normalized data in both
directions**. The target's wire/API format — settings-file shape, permission-string grammar,
transcript JSON, token-usage fields, hook-event names — must never cross the boundary, as an
argument *or* as a return value. The format lives only inside the concrete `*_runtime`
implementation.

**The call says what, not how:**

- Good: `permission allow-web --domain docs.oracle.com` / `permission allow-scripts --executor`
- Bad: `patch-claude-settings --file .claude/settings.local.json`
- Also bad: `permission configure --permissions "Bash(python3 …)"` — `Bash(...)` is the Claude
  permission-DSL *format*; passing it through a "goal-based" call still leaks the format. The
  caller states intent (allow the executor, allow a web domain); the runtime renders the
  `Bash(...)` / `WebFetch(...)` string itself.

**The return carries normalized data, not the wire format:**

- Good: `metrics capture` returns normalized token categories
  (`{input, output, cache_read, cache_creation, total}`).
- Bad: returning — or having the caller parse — Claude's `<usage>` tag, the `message.usage`
  four-field shape, or the transcript JSONL. The Anthropic cache-pricing weights and the JSONL
  schema stay inside `claude_runtime`; `manage-metrics` only ever sees normalized numbers.

The test: if you switched targets, would the data crossing this boundary change shape? If yes,
the format is leaking — push it inside the implementation and normalize the contract.

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

See `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/no-op-policy.md` for the full caller obligations, worked examples, and the `no-op` vs `error` distinction.

---

## 4. Single Source of Truth

- Claude Code format in `marketplace/bundles/` is the only editable source
- Target outputs (`.opencode/`, `.cursor-plugin/`) are **generated artifacts**
- Body text is emitted **verbatim except for bounded mechanical line-level transforms**.
  Each target declares its transform rules as **data** (its `mapping.json` / `transforms`
  config); a **shared engine** applies them. The Claude target declares no body transforms,
  so its output is verbatim.
- The set of Claude source idioms a target may rewrite (tool names like `AskUserQuestion`,
  `Task:`; the `Skill:` directive; `/slash` commands) is a **registered vocabulary**. A
  target maps the subset it renames; the build **fails closed** on any source idiom in that
  vocabulary that a non-verbatim target leaves unmapped (cf. `UnmappedToolError`).
- Frontmatter, manifests, and those data-driven body transforms are the only build-time rewrites
- Adding a transform rule is a data change in a target's config, not new emitter code

---

## 5. No Universal Syntax

Do not invent `{{ }}` or similar templating for cross-platform body text.

If a skill needs platform-specific behavior, that behavior goes in:
- A script behind `platform-runtime`
- A conditional instruction ("If Claude Code, do X; if OpenCode, do Y")
- A no-op with alternative

Not in the body text itself.

---

## 6. Open to Further Targets

The design is built for *N* targets (Claude Code, OpenCode, and future adapters — Cursor,
Windsurf, …), not a Claude-vs-OpenCode binary. The governing test:

> **Adding a target costs: implement two contracts + a data file, register once, and edit
> zero general skill bodies, shared runtime scripts, or other targets.**

The two contracts are `Runtime` (runtime behaviour + layout resolution) and `TargetBase`
(build emission). Both are registry-dispatched; the data file is the target's
`mapping.json` / transform config.

Anti-patterns (a new target must never require these):

- **Target enumeration in core or contracts** — no `if target == "claude"/"opencode"` in a
  general skill, shared script, or an ABC docstring. The ABC states *intent* + the no-op
  fallback; per-target behaviour lives in the concrete `*_runtime` / `*Target` class.
- **Target-shaped interfaces** — an operation's signature must not encode one target's model
  (e.g. an "install hook" op naming another platform's hook events). Operations are
  target-opaque; specifics live behind the implementation.
- **Per-target code where data suffices** — tool/model/directive mappings and layout roots
  are declared as data, applied by shared engines.
- **Core-owned target tables** — a target declares its own roots/mappings inside its
  implementation; the core does not maintain a growing per-target table.

A target declines any capability it lacks via the [No-Op Policy](#3-no-op-policy) — it never
fakes success and never blocks a workflow.

See [07-target-extensibility.md](07-target-extensibility.md) for the seam audit and the
structural work to reach this bar.

---

## 7. Terminology

| Use | Do Not Use |
|-----|-----------|
| target | harness |
| platform-runtime | platform abstraction layer, harness API |
| Claude Code | Claude (when unambiguous) |
| OpenCode | opencode (in code), OpenCode (in prose) |
| drift | mismatch |
| no-op | unsupported, not implemented |

---

## 8. Document Hygiene

- No version numbers or changelogs in any document
- No "Status", "Created", "Last updated" metadata
- No duplication — cross-reference instead
- Current state only — do not describe transitional information
- AsciiDoc for long-form docs (`.adoc`), Markdown for plans and skills (`.md`)
