# multiplattform

The epic that finishes the multi-target architecture: target-opaque runtime seams, a
target-scoping mechanism for components that exist on only some targets, zero Claude literals
outside the sanctioned homes, and a one-command OpenCode developer loop.

This is a **standalone epic**: like `test-quality`, it has no counterpart ledger under
`.plan/local/orchestrator/`. Everything it needs is in git; nothing in it expects an orchestrator
record to exist.

Read [`../README.md`](../README.md) for the tree layout and the run contract, and
[`../cloud-bridge.md`](../cloud-bridge.md) for the `{NNN}-` prefix rule. This file adds only what
is specific to this epic: the architecture baseline the plans build on, the boundary between
plannable and validation-gated work, and the dependency/concurrency contract.

[`reference/`](reference/) holds the epic's evidence and constraints:

- [`reference/principles.md`](reference/principles.md) — the non-negotiable cross-cutting rules
  (goal-based API, no-op policy, single source of truth, no universal templating, the N-target
  cost bar, terminology, document hygiene). Every plan in this epic is authored and verified
  against them.
- [`reference/coupling-inventory.md`](reference/coupling-inventory.md) — the registry of open
  Claude couplings, by placement home. The plans' deliverables are drawn from it; it shrinks as
  they land.
- [`reference/opencode-validation-protocol.md`](reference/opencode-validation-protocol.md) — the
  live-runtime runbook (exact commands, expected observations, pass/fail criteria) for the first
  execution on a real OpenCode install, plus the post-validation work that becomes plannable once
  it has run.

## The baseline

What exists today, stated so the plans do not re-derive it from scratch. Every enumeration below
is a **lead** — re-derive from the named source before acting on it.

| Fact | Source of truth |
|---|---|
| Three build targets are registered: `claude` (verbatim mirror, equality-gated), `opencode` (frontmatter + body transforms from `mapping.json`), `pr-agent` | `TARGET_REGISTRY` in `marketplace/targets/__init__.py` |
| The `Runtime` ABC carries 24 operations, registry-dispatched (`claude`, `opencode`), including `wait_for` (ADR-011) | `platform-runtime/scripts/runtime_base.py`; count by `@abstractmethod` |
| Body rewrites are data + one shared engine, fail-closed: `directive_rewrites`, `slash_rewrites`, and four registered idioms in `body_idiom_rewrites` (`AskUserQuestion` → rewrite, `Task:` → preserve, `Skill: <entry>` → source_fix, `Monitor` → source_fix) | `marketplace/targets/opencode/mapping.json`; `marketplace/targets/body_transform_engine.py` |
| The level→model tables are single-sourced: the OpenCode variant emitter imports `LEVEL_TABLE`/`ALIAS_GATED_EFFORTS` from the Claude emitter and resolves aliases through `mapping.json::model_map`, with lockstep tests on both sides | `marketplace/targets/claude/variant_emitter.py`; `marketplace/targets/opencode/variant_emitter.py`; `test/marketplace/targets/*/test_level_table_lockstep.py` |
| Metrics are normalized at the runtime boundary: `claude_runtime` owns transcript layout, parsing, and cache weights; `manage-metrics` consumes `{input, output, cache_read, cache_creation, total}` and never parses a transcript | `platform-runtime/scripts/claude_runtime.py`; `manage-metrics/scripts/manage-metrics.py` |
| Layout resolution is a runtime op with memoised helpers (`get_project_skill_roots()`, `get_bundle_cache_roots()`); the config, manifest, steward, and inventory-discovery resolvers route through them. Extension discovery routes its cache roots through but not its implementor scan, and several plugin-doctor analyzers keep inline anchors — both open, registered in the [coupling inventory](reference/coupling-inventory.md) §B (the implementor scan is plan `030`'s D4) | `script-shared/scripts/marketplace_paths.py` and its consumers |
| OpenCode declines what it cannot do honestly: permission ops and automatic metrics capture return `no-op` with `reason` + `alternative`, never fabricated success | `platform-runtime/scripts/opencode_runtime.py`; `platform-runtime/standards/no-op-policy.md` |
| CI gates OpenCode generation on every relevant PR, and the distribution matrix publishes both `dist-claude` and `dist-opencode` (branches) plus `claude/`- and `opencode/`-prefixed dist tags from one source tag | `.github/workflows/opencode-generate-check.yml`; `.github/workflows/claude-distribute.yml` |
| The terminal-title composer is target-neutral (process-state enum in, glyphs single-sourced); the Claude event→state mapping lives in `claude_runtime` | `manage-terminal-title/scripts/manage_terminal_title.py`; `manage-locks/scripts/merge_lock.py` |
| `plugin-doctor` is a target-agnostic engine with a documented, swappable Claude rule-pack (the fork point is documentary) | `plugin-doctor/references/rule-provenance.md` |

## The boundary: plannable vs validation-gated

**OpenCode has never executed a plan-marshall workflow live.** The runtime answers every
operation and the emitter produces a complete tree, but the behaviours the design assumes —
subagent user-prompting, `task`-tool dispatch, `skill`-tool loading, parallel dispatch,
instruction retention — are unobserved on a real install. Confirming them needs an interactive
session with a human at a terminal, which the cloud plan lane cannot provide, so that work is
**not a plan in this epic**: it is the
[validation protocol](reference/opencode-validation-protocol.md), run by an operator when an
OpenCode install is available. The install-path pin and the OpenCode user/developer
documentation depend on its outcomes and are authored as new plans afterwards — the protocol's
"Post-validation work" section is their staging list.

Everything below that line is plannable now: none of the four plans requires an OpenCode
install, an operator decision, or an unvalidated behaviour.

## The plans, and what may run at the same time

```text
010 runtime seam neutrality ─┬─ sequential, either order ─┬─ 030 claude-literal residuals
                             └─ (shared: claude_runtime) ─┘
020 target-scoped components ── independent of everything
040 sync-opencode inner loop ── independent of everything
```

| Plan | Surface | May run concurrently with |
|---|---|---|
| `010` | `platform-runtime/scripts/**` (ABC, router, both runtimes), `script-shared/scripts/marketplace_paths.py`, `test/plan-marshall/platform-runtime/**`, `test/plan-marshall/script-shared/**`, conditionally `platform-runtime/standards/contract.md` and the `project install-hook` caller invocations its D1 parameter change reaches | `020`, `040` |
| `020` | `marketplace/targets/**`, `plan-marshall/commands/tools-fix-intellij-diagnostics.md`, `pm-plugin-development` (plugin-doctor + frontmatter standards), `test/marketplace/targets/**`, `test/pm-plugin-development/plugin-doctor/**` | `010`, `030`, `040` |
| `030` | permission/providers/extension/inventory/retrospective scripts named in its Expected surface, plus `platform-runtime/scripts/claude_runtime.py` + `_claude_runtime_impl.py` (and conditionally `platform-runtime/standards/contract.md`), and their `test/` subtrees | `020`, `040` |
| `040` | `.claude/skills/sync-opencode/**`, `test/sync-opencode/**`, `doc/developer/marketplace-build.adoc`, `doc/developer/distribution.adoc` | `010`, `020`, `030` |

**`010` and `030` must not run concurrently.** Both edit `claude_runtime.py` /
`_claude_runtime_impl.py` — `010` moves the install-op vocabulary in, `030` moves permission
rendering in. Run them in either order, not together; `010` first is preferable because `030`
then renders into the already-neutral contract shape.

⚠️ **The surface lists are hand-written, so every run re-derives its own before acting.** Each
plan's Expected surface names the files its deliverables touch; the run confirms the list against
the tree (files exist, symbols present) as its first action and reports — rather than silently
absorbs — any file the work turns out to need beyond it. Two plans discovering a shared file that
this table calls disjoint is a partition defect: halt and report it.

Three shared constraints bind every plan in this epic. They are stated once here — each plan
points back to this README through its epic header line rather than restating them:

- A plan **never edits another plan's surface**, even for an obvious adjacent fix — the neighbour
  may be running concurrently. Record the finding in the report instead.
- Counts and enumerations in the plans (operation counts, docstring hit counts, residual sets,
  registry membership) are **leads**: re-derive at the moment of the claim, act on what the tree
  says, and report divergence from the plan's figure.
- The [principles](reference/principles.md) bind every deliverable: no target enumeration in
  contracts, no wire format across the runtime boundary, no universal templating, honest no-ops.
