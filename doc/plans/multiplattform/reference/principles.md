# Cross-Cutting Principles — Multi-Target Architecture

The non-negotiable constraints governing every plan in the `multiplattform` epic. They bind the
runtime abstraction (`marketplace/bundles/plan-marshall/skills/platform-runtime/`), the build
generator (`marketplace/targets/`), and every general skill body and shared script.

---

## 1. Goal-Based API — semantic in, normalized out

Platform-runtime operations express **intent**, and they carry **normalized data in both
directions**. The target's wire/API format — settings-file shape, permission-string grammar,
transcript JSON, token-usage fields, hook-event names — never crosses the boundary, as an
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

- Good: the metrics ops return normalized token categories
  (`{input, output, cache_read, cache_creation, total}`). The transcript layout, the
  `message.usage` four-field shape, and the cache-pricing weights live inside `claude_runtime`;
  `manage-metrics` only ever sees normalized numbers.
- Bad: returning — or having the caller parse — a transcript path or raw transcript JSONL.
  "The runtime returns the path, core parses it" is a relocated coupling, not an abstraction.

The test: if you switched targets, would the data crossing this boundary change shape? If yes,
the format is leaking — push it inside the implementation and normalize the contract.

---

## 2. Boundary Rules

Use `platform-runtime` when:

- The operation's behavior differs between targets
- The operation touches platform settings, plugin paths, or hook mechanisms

Do NOT use `platform-runtime` for:

- CI/PR operations → `tools-integration-ci`
- Plan state → `manage-status`, `manage-tasks`
- Architecture data → `manage-architecture`
- Metrics storage/analysis → `manage-metrics` (runtime only captures; storage is internal)
- Executor regeneration → `tools-script-executor`

When in doubt, ask: "Would this work identically if I switched targets?" If yes, it belongs in
plan-marshall internal code.

---

## 3. No-Op Policy

If a target cannot implement an operation, it returns:

```toon
status: no-op
operation: <name>
reason: <why it cannot be done>
alternative: <what the user can do instead>
```

The caller MUST handle `no-op` gracefully and continue. Never fail a workflow because a display
hook is unsupported, and never fake success — a fabricated effect counter misleads callers.

See `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/no-op-policy.md` for
the full caller obligations, worked examples, and the `no-op` vs `error` distinction.

---

## 4. Single Source of Truth

- Claude Code format in `marketplace/bundles/` is the only editable source.
- Target outputs (`target/opencode/`, `target/pr-agent/`, …) are **generated artifacts**.
- Body text is emitted **verbatim except for bounded mechanical line-level transforms**. Each
  target declares its transform rules as **data** (its `mapping.json`); the shared engine
  (`marketplace/targets/body_transform_engine.py`) applies them. The Claude target declares no
  body transforms, so its output is verbatim and equality-validated
  (`marketplace/targets/claude/equality_check.py`).
- The set of Claude source idioms a target may rewrite is a **registered vocabulary**
  (`mapping.json::body_idiom_rewrites`). A target maps the subset it renames; the build **fails
  closed** (`UnmappedIdiomError`) on any registered source idiom a non-verbatim target leaves
  unmapped, and on any unknown disposition.
- Frontmatter, manifests, and those data-driven body transforms are the only build-time rewrites.
- Adding a transform rule is a data change in a target's config, not new emitter code.

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

The design is built for *N* targets, and the registry already holds three (`claude`, `opencode`,
`pr-agent` — re-derive from `TARGET_REGISTRY` in `marketplace/targets/__init__.py`; the registry
is the source of truth, never a prose enumeration). The governing test:

> **Adding a target costs: implement two contracts + a data file, register once, and edit
> zero general skill bodies, shared runtime scripts, or other targets.**

The two contracts are `Runtime` (runtime behaviour + layout resolution,
`platform-runtime/scripts/runtime_base.py`) and `TargetBase` (build emission,
`marketplace/targets/base.py`). Both are registry-dispatched; the data file is the target's
`mapping.json`.

Concretely, adding target `X` is exactly:

1. `platform-runtime/scripts/x_runtime.py` — subclass `Runtime`, implement each operation or
   decline via `no-op`; declare X's layout roots inside it.
2. `marketplace/targets/x/` — subclass `TargetBase`, plus a single `mapping.json` declaring X's
   `tool_permissions`, `model_map`, and body-transform rules (`directive_rewrites`,
   `slash_rewrites`, `body_idiom_rewrites`); the shared `body_transform_engine` applies that
   data, so X writes no transform code.
3. Register X once on each side (the runtime registry in `platform_runtime.py`, the build
   `TARGET_REGISTRY`).

Nothing else: no general skill body, no shared script, and no other target may need editing.

Anti-patterns (a new target must never require these):

- **Target enumeration in core or contracts** — no `if target == "claude"/"opencode"` in a
  general skill, shared script, or an ABC docstring. The ABC states *intent* + the no-op
  fallback; per-target behaviour lives in the concrete `*_runtime` / `*Target` class.
- **Target-shaped interfaces** — an operation's signature must not encode one target's model
  (e.g. an install op naming another platform's hook events). Operations are target-opaque;
  specifics live behind the implementation.
- **Per-target code where data suffices** — tool/model/directive mappings and layout roots are
  declared as data, applied by shared engines.
- **Core-owned target tables** — a target declares its own roots/mappings inside its
  implementation; the core does not maintain a growing per-target table.

A target declines any capability it lacks via the [No-Op Policy](#3-no-op-policy) — it never
fakes success and never blocks a workflow.

**Differs-per-target vs. exists-only-on-some-targets.** A capability that exists everywhere but
behaves differently belongs behind a `Runtime` op (uniform contract, per-target impl). A
capability that exists only on some targets — no analog elsewhere — belongs in a
**target-specific component**, shipped via a `targets:` frontmatter filter and simply *absent*
on other targets (cleaner than a runtime no-op for a capability the other target does not have
at all). This gated fourth home is admitted only when all three conditions hold:

1. It is a whole workflow/knowledge body, not reducible to a single `Runtime` op or a
   body/frontmatter transform.
2. It is genuinely N/A on other targets, not merely hard to abstract.
3. Normalizing it would force a no-op op onto every other target or distort the shared ABC.

It must never be used to dodge normalization — format-coupling (metrics shape, permission DSL,
tool-name vocab) still normalizes into the runtime/build-target homes; the target-specific
component is for target-bound *capabilities*, not the per-target *rendering* of a shared one.

The four placement homes, chosen by *what kind* of coupling an aspect is:

| Home | What lands here |
|---|---|
| `platform-runtime` | Everything target-specific at runtime: behaviour/side-effects (settings & permission I/O, transcript reading, hook installation, title rendering) and filesystem-layout resolution |
| Build target (`marketplace/targets/{name}/`) | Emitted-text vocabulary and emitted-frontmatter format, declared as `mapping.json` data and applied by the shared engine |
| Stays put (platform-agnostic) | Logic identical across targets; it only *sources* target-specific values from `platform-runtime` |
| Target-specific component (`targets:` filter) | Whole capabilities that exist only on some targets — absent elsewhere, no runtime no-op |

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
