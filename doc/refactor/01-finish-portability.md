# 01 — Finish portability gaps

## Status — all 8 gaps landed

The 8 portability gaps below have **landed**. Every general skill body, shared script, and
authoring tool that previously hardcoded `.claude/` *behaviour* now routes through
`platform-runtime` (runtime ops + the layout-resolution op) or through the OpenCode build
target; the remaining `.claude/` mentions are the sanctioned set the closing audit accepts
(see [§ Closing audit](#closing-audit)). The next step is validating the live runtime on
OpenCode ([02](02-validate-opencode-runtime.md)).

The gap-class descriptions below are retained as the landed-work record (what each gap was
and where it resolved to).

## Objective

Route the last Claude-specific call sites in **general skill bodies and shared scripts**
through `platform-runtime` (or a target-aware abstraction) so that nothing outside the
sanctioned per-platform homes hardcodes `.claude/` behaviour before the runtime is
validated on OpenCode ([02](02-validate-opencode-runtime.md)).

`platform-runtime` itself is the sanctioned home for per-platform code and is **out of
scope** — its `claude_runtime.py` / `claude_hook.py` / `opencode_runtime.py` contain
`.claude/` paths and hook strings by design.

This document groups the work into gap classes. The **exhaustive candidate registry** — every
`file:line` from a read-everything audit of all ~880 files under `marketplace/bundles/**` — is
[08-claude-coupling-inventory.md](08-claude-coupling-inventory.md); the gap classes below are
its actionable summary. The audit *deepened* these classes rather than adding new ones: the
permission **grammar** (not just paths) is Claude-specific (Gap 1); the metrics **`<usage>`/
`message.usage`/cache-pricing format** (not just the path) is too (Gap 2); the shared
`script-shared/marketplace_paths.py` foundation underlies the layout gaps (Gaps 4/5); and the
tool-name vocabulary saturates `persona-plan-marshall-agent` — loaded by every agent (Gap 6). Two
small standalone build-target items also surfaced: `recipe-doc-verify` hardcodes `CLAUDE.md`
(OpenCode → `AGENTS.md`) and the git commit trailer hardcodes `Co-Authored-By: Claude`.

## Already landed (foundation — not open work)

- **Token capture via runtime** — `phase-5-execute/SKILL.md` and `plan-retrospective/SKILL.md`
  call `platform-runtime session capture` + `metrics capture`. *(Capture is abstracted;
  transcript enrichment behind the same skills is not — see Gap 2.)*
- **Multi-platform bootstrap** — `marshall-steward/scripts/bootstrap_plugin.py`
  (`read_runtime_target()`, `_detect_opencode_root()` 7-root walk, `--target`).
- **`marshal.json` carries `runtime.target`** — `project initial-setup --target opencode`.
- **OpenCode body transformer wired + AGENTS.md de-leaked** — `OpenCodeTarget.generate()`
  passes a `body_transformer`; `opencode.json` no longer hardcodes `instructions`.
- **Target-aware executor** — `tools-script-executor/scripts/generate_executor.py` already
  searches a 7-root list including both `.claude/skills` and `~/.config/opencode/skills`
  (this is the model the other resolvers in Gap 4 fail to follow).
- **Model/effort switching is clean** — the level→model binding is centralized in
  `variant_emitter.py` `LEVEL_TABLE` + `mapping.json::model_map`; shared scripts reference
  *level names* (`level-1 … level-7`), not raw model ids. No model-name hardcoding exists in
  core logic. (The lone exception is an authoring tool — see Gap 8.)

## Target placement model

Not every Claude-specific aspect moves to the same place. "Move it out of the core" resolves
to **four** destinations, chosen by *what kind* of coupling it is:

- **`platform-runtime`** — everything target-specific at runtime: behaviour / side-effects
  (settings & permission I/O, transcript reading, hook installation, title rendering) **and**
  filesystem-layout resolution (where project-local skills, the plugin cache, and bundles live
  per target). `claude_runtime.py` owns the `.claude/` shapes and roots; `opencode_runtime.py`
  owns its shapes/roots or honest `no-op`. This is the single home for "anything that differs
  per target," per [principles §2](principles.md) (which already names "plugin paths"). The
  cost — a subprocess hop on hot config/manifest paths — is mitigated by memoising the
  resolved roots per process (the target does not change mid-run), so a `project:`-step or
  config resolution pays the runtime call at most once.
- **OpenCode build target** — emitted-**text vocabulary** (tool names in body prose) and
  emitted-**frontmatter format** (e.g. `model: sonnet` vs. `model: anthropic/...`). Belongs in
  `marketplace/targets/opencode/transforms.md` + `body_transforms.py` and the frontmatter
  transform, or in target-neutral source rewording. Build-time, not runtime
  ([principles §4/§5](principles.md)).
- **Stays put (platform-agnostic)** — logic that is identical across targets stays where it is
  and only *sources* the target-specific value from `platform-runtime`: metrics *storage* and
  aggregation stay in `manage-metrics`; the `session_id` validator stays in
  `tools-input-validation` as an opaque-token contract.
- **Target-specific skill** *(gated 4th home)* — a whole skill/command that **exists only on
  some targets**, shipped via a `targets:` frontmatter filter and simply *absent* elsewhere (no
  runtime no-op). This is the home for capabilities with no analog on other targets — e.g.
  `tools-fix-intellij-diagnostics` (IDE-MCP), a Claude harness-hook setup wizard, a future
  `opencode-marketplace-install` flow. **Admission test — all three must hold:** (1) it is a
  whole workflow/knowledge body, not reducible to a single `Runtime` op or a body/frontmatter
  transform; (2) it is genuinely N/A on other targets, not merely hard to abstract; (3)
  normalizing it would force a no-op op onto every other target or distort the shared ABC. It
  does **not** excuse format dumping — metrics format still normalizes (Gap 2), permission
  enforcement still uses semantic ops (Gap 1), tool-name vocab still becomes build-target data
  (Gap 6). The distinction from `platform-runtime`: *differs per target* → runtime op;
  *exists only on some targets* → target-specific skill. Mechanism in
  [07](07-target-extensibility.md).

These homes are **target-neutral by contract** — `claude_runtime.py` / OpenCode are named only
as the current implementations. Per [principles §6](principles.md), no general skill, shared
script, or ABC may enumerate targets. The gaps below migrate the *call sites*; the *seam shapes*
that keep those homes open to a third target (target-opaque interfaces, data-driven transforms,
consolidated registration, the `targets:` filter) are [07](07-target-extensibility.md).

## Gap inventory at a glance

All gaps are **landed**. The `Destination` column records where each gap's coupling resolved to.

| # | Subsystem | Status | Destination | Essence |
|---|-----------|:------:|-------------|---------|
| 1 | Permission tooling | landed | `platform-runtime` | Claude settings I/O moved into `claude_runtime.py`; SKILL bodies call `platform-runtime permission …` |
| 2 | Metrics / transcript enrichment | landed | `platform-runtime` (read) + stays (storage) | runtime reads normalized token categories; `manage-metrics` aggregates, never parses a transcript |
| 3 | `session_id` validation | landed | stays-agnostic + Gap 2 | shared validator reworded to opaque-token; strict-UUID regex folded into the Gap-2 metrics engine |
| 4 | Project-local skill / step resolution | landed | `platform-runtime` | `layout skill-roots` op + memoised `get_project_skill_roots()`; resolvers routed through it |
| 5 | Bundle / plugin-cache discovery | landed | `platform-runtime` | `layout bundle-cache-root` op + memoised `get_bundle_cache_roots()`; discovery routed through it |
| 6 | Body-text tool-name transforms | landed | OpenCode build target | `AskUserQuestion` / `Task:` / `Skill: <entry>` dispositions live as data in `mapping.json::body_idiom_rewrites` (mirrored in `transforms.md`); `load_idiom_registry` fails closed on unknown dispositions, `rewrite_registered_idioms` applies the validated registry |
| 7 | Terminal-title / hooks | landed | `platform-runtime` | composer takes a neutral state enum; state→icon mapping owned by the runtime; lock glyphs de-duplicated |
| 8 | Authoring / meta tools | landed | `platform-runtime` + build target | `plugin-doctor` engine/rule-pack split; `plugin-doctor` + `tools-marketplace-inventory` scan both layouts; target-aware frontmatter |

**Settled architectural decisions:**

- **Layout resolution (Gaps 4-5) goes through `platform-runtime`**, not a shared path module —
  one home for everything target-specific. The hot-path subprocess cost is mitigated by
  per-process memoisation of the resolved roots.
- **Authoring tools (Gap 8) are made target-aware**, not scoped out — `plugin-doctor` and
  `tools-marketplace-inventory` scan both `.claude/skills/**` and the OpenCode layout, and
  apply target-aware frontmatter checks (e.g. `model: anthropic/...` vs. `model: sonnet`).
  This keeps OpenCode authoring viable.

---

## Gap 1 — Permission tooling is not portable on either side

**Claude side hardcodes settings paths.** `tools-permission-doctor/scripts/permission_common.py:79-100`
returns `Path.home()/'.claude'/'settings.json'`, `project_dir/'.claude'/'settings.local.json'`,
etc. directly. Also `permission_doctor.py:54` (`.claude/commands/`),
`permission_fix.py:71` (`Read(~/.claude/plugins/cache/**)`),
`workflow-permission-web/scripts/permission_web.py:18,24,545-570` (settings.json args +
help). The three SKILL bodies (`tools-permission-fix`, `tools-permission-doctor`,
`workflow-permission-web`) instruct direct `--settings ~/.claude/settings.json` operations.

**OpenCode side is fake success.** `opencode_runtime.py:144-334`
(`permission_configure` / `_analyze` / `_fix` / `_ensure_wildcards` / `_ensure_steps` /
`_web_analyze` / `_web_apply`) validate args and return `toon_success` with all effect
counters `0` — they write nothing. Per [principles §3](principles.md) an unimplementable
op must return honest `no-op` with `reason`/`alternative`, not hollow success.

**Required:** move Claude settings I/O into `claude_runtime.py`; implement the OpenCode
permission backend for real *or* convert every stub to honest `no-op`; rewrite the three
SKILL bodies to call `platform-runtime permission …`; test both targets.

**Draw the boundary at intent, not the DSL ([principles §1](principles.md)).** The permission
ops must take and return *semantic* permission intent — "allow the executor", "allow web domain
X", normalized findings — **not** the Claude permission-string grammar (`Skill()`, `Bash()`,
`WebFetch()`, the `permissions.{allow,deny,ask}` schema). That grammar is a Claude *format*;
it must be rendered and parsed entirely inside `claude_runtime.py`. A `permission configure
--permissions "Bash(...)"` contract would still leak the format even though it routes through
the runtime — so the contract itself changes, not just the I/O site.

## Gap 2 — Metrics / transcript enrichment is a Claude-transcript engine

This is larger than the two call sites first identified. The engine itself is Claude-coupled:

- `manage-metrics/scripts/manage-metrics.py:152,1377` — `projects_dir = home/'.claude'/'projects'`.
- `manage-metrics.py:1370-1423` — transcript discovery assumes the Claude layout
  `~/.claude/projects/{cwd-slug}/{session_id}.jsonl` and `…/{session_id}/subagents/agent-*.jsonl`,
  then parses Claude transcript JSONL (`message.usage` fields).
- `manage-metrics.py:142` — re-validates `SESSION_ID_RE` (Claude UUID shape).

The call sites that feed it are `phase-6-finalize/SKILL.md:85` (`transcript_path` pattern)
and `plan-retrospective/SKILL.md:210` (Aspect 13 chat-history). On OpenCode none of this
exists; `metrics capture` already no-ops, but `enrich` / subagent-token attribution is
entirely Claude-specific.

**Required — the boundary is the token *format*, not the file path
([principles §1](principles.md)).** The platform-runtime op returns **normalized token
categories** (`{input, output, cache_read, cache_creation, total}`) for a (plan, phase) or
session. Everything Claude-shaped — the `~/.claude/projects/.../{session_id}.jsonl` layout, the
`subagents/agent-*.jsonl` discovery, the `<usage>` tag, the `message.usage` four-field parse,
the `SESSION_ID_RE` shape, and the Anthropic cache-pricing weights — lives **only** inside
`claude_runtime.py`. `manage-metrics` receives normalized numbers and keeps its
storage/aggregation role; it never parses a transcript and never sees a Claude format.

Explicitly reject the half-measure of "the runtime returns the transcript *path* and
`manage-metrics` parses it" — that leaves the Claude JSONL/`message.usage` format in core and
fails the switch-targets test. On OpenCode the op returns `no-op` (no transcript), and the
enrich step degrades gracefully (`transcript_not_found` → skip) — driven by the `no-op`, not by
the engine resolving a Claude path.

## Gap 3 — `session_id`: one validator is already fine, one regex is the metrics engine's

The two `SESSION_ID_RE` copies are **not** equivalent — the meticulous check corrected an
earlier mis-reading:

- `tools-input-validation/scripts/input_validation.py:45` is **already target-agnostic**:
  `SESSION_ID_RE = ^[A-Za-z0-9_-]{1,128}$` — an opaque non-empty token, not a Claude UUID. The
  only coupling is prose: the `validate_session_id` docstring and the `--session-id` argparse
  help say "Claude Code UUID-shape token." This is `stays-agnostic` — just neutralize the
  wording. No `runtime.target` branch is needed; an opaque-token contract is already correct
  cross-target.
- `manage-metrics/scripts/manage-metrics.py:79` is the **strict** Claude UUID
  (`[0-9a-f]{8}-…-[0-9a-f]{12}`), used at `:142` only to drive Claude transcript discovery — so
  it is **part of Gap 2** and moves into `claude_runtime.py` with the transcript engine, not
  into a shared validator.

**Required:** reword the `input_validation.py` docstring/help to "opaque session token (the
target runtime supplies it)"; remove the strict UUID regex from `manage-metrics` as part of the
Gap 2 extraction. Do **not** add a `runtime.target` branch to the shared validator — that would
re-introduce target enumeration where an opaque-token contract already suffices.

## Gap 4 — Project-local skill / finalize-step resolution is `.claude/skills/`-hardcoded

The `project:`-prefixed skill mechanism (finalize-steps, recipes, verify-steps) resolves
project-local skills, but every resolver outside the executor hardcodes `.claude/skills/`
with **no** `runtime.target` branch:

- `manage-config/scripts/_config_core.py:186-187` — `Path('.claude')/'skills'/skill/'SKILL.md'`.
- `manage-config/scripts/_cmd_skill_domains.py:170,472`, `_cmd_skill_resolution.py:334,435`.
- `manage-config/scripts/manage-config.py:219` (help) and `finalize_step_presets.py:40,46`
  (preset prose) name the same `.claude/skills/` anchor.
- `manage-execution-manifest/scripts/manage-execution-manifest.py:3102,3113` — `project:`
  step → `.claude/skills/{bare}/SKILL.md`.
- `marshall-steward/scripts/determine_mode.py:604,623,647` — finalize-step discovery under
  `<project_root>/.claude/skills/`.
- `build-pyproject/scripts/extension.py:105,115` — classifies `.claude/skills/*.py` as
  production source. **This is a different bundle** — the coupling is not confined to
  `manage-config`; any build/domain extension that reasons about project-local skills repeats it.
- `script-shared/scripts/marketplace_paths.py:26` — `CLAUDE_DIR = '.claude'` constant.

The complete set of `.py` files resolving `.claude/skills` (excluding `platform-runtime`)
is the list above plus the two already-target-aware resolvers (`generate_executor.py`,
`bootstrap_plugin.py`) and the Gap-8 authoring tools. The executor
(`generate_executor.py:389-393,482-485`) already treats project-local skills as
cross-target (both `.claude/skills` and `~/.config/opencode/skills`). These resolvers are
inconsistent with that design — on OpenCode, `project:` finalize-steps and recipes silently
fail to resolve.

**Required:** add a `platform-runtime` layout-resolution operation that returns the
project-local-skill root(s) for the active target (mirroring the executor's root list), and
route every site above through it. Memoise the result per process so hot config/manifest
paths pay the call once. Retire the bare `CLAUDE_DIR` constant as a project-local-skill anchor.

## Gap 5 — Bundle / plugin-cache discovery is Claude-only

- `extension-api/scripts/extension_discovery.py:29` — `Path.home()/'.claude'/'plugins'/'cache'/'plan-marshall'`.
  The extension API discovers domain bundles only under the Claude plugin cache; on OpenCode
  the deployed bundle lives under `~/.config/opencode/` (or the env-var dir).
- `script-shared/scripts/marketplace_paths.py:27` — `PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'`
  is the shared Claude-cache constant other scripts build on.
- `manage-execution-manifest.py:835,857` reference the cache path in prose (lower priority).

`bootstrap_plugin.py` and `generate_executor.py` already resolve both targets — these two are
the remaining Claude-only discovery anchors.

**Required:** route extension/bundle discovery through the same `platform-runtime`
layout-resolution operation as Gap 4 (it already wraps the bootstrap root resolution), so
domain-bundle extensions load on OpenCode. Retire `PLUGIN_CACHE_SUBPATH` as a standalone
Claude-only anchor.

## Gap 6 — Body-text tool-name transforms are incomplete

The gap as found: the OpenCode body transform (`body_transforms.py`) rewrote only concrete
`Skill:` directives and `/slash` commands, leaving Claude tool names in body prose
untransformed:

- **`AskUserQuestion`** — 313 references across skill/agent/command bodies (escalation
  mechanism). OpenCode's equivalent is `question`/`ask`.
- **`Task:`** dispatch references — Claude tool name; OpenCode's is `task` (see
  [06](06-execution-context-cross-target.md)).
- **`Skill: <entry>`** placeholder loops — `<entry>` is a runtime placeholder, not an
  identifier (06 item 2).

**Resolved as:** the source stays Claude-native; the registered idioms are per-target
**rewrite data** — `mapping.json::body_idiom_rewrites` declares `AskUserQuestion` →
`rewrite_inline_code` (to `question`), `Task:` → `preserve` (the leaf-aware decision from
06 item 3), and `Skill: <entry>` → `source_fix`; `load_idiom_registry` validates the
registry up front and fails closed (`UnmappedIdiomError`) on an unknown disposition before
`rewrite_registered_idioms` applies the per-idiom rewrites. `Skill: <entry>`
remains the one true source change — reword the placeholder prose (06 item 2, still open).
No universal `{{ }}` templating ([principles §5](principles.md)) and no neutralised source
vocabulary.

## Gap 7 — Terminal-title / hooks (verify, likely acceptable)

The gap as found: `manage-terminal-title/scripts/manage_terminal_title.py` was *labelled*
"pure platform-agnostic composition," but pass 2 ([08](08-claude-coupling-inventory.md) §A3)
found its `resolve_icon` keyed on Claude hook-event names
(`Stop`/`Notification`/`PreToolUse`/`PostToolUse`) and tool names (`AskUserQuestion`,
`Bash`) — a target-shaped interface, not a neutral one — with `manage-locks/merge_lock.py`
duplicating the glyph vocabulary.

**Resolved as:** `resolve_icon(process_state)` takes the target-neutral `PROCESS_STATE_*`
enum; the Claude hook-event → state mapping is owned by `claude_runtime`; the lock glyphs
are single-sourced in `TITLE_TOKEN_GLYPHS` (imported by `merge_lock.py`). `render-title`
no-ops on OpenCode, and `manage-status` persists only the bare state string. Confirm (during
[02](02-validate-opencode-runtime.md)) the title/statusline path is genuinely no-op on
OpenCode end-to-end. The `project_install_hook` *interface* encoding Claude's hook model is
the related seam-shape fix in [07](07-target-extensibility.md).

## Gap 8 — Authoring / meta tools: make target-aware

`pm-plugin-development` tooling operates on the Claude component layout by nature, and is
being made target-aware so OpenCode authoring stays viable:

- `plugin-doctor/scripts/*` — scan `<repo>/.claude/skills/**` (project-local) and the plugin
  cache; `_cmd_apply.py:48` emits frontmatter with a hardcoded `model: sonnet`.
- `tools-marketplace-inventory/scripts/*` — `CLAUDE_DIR='.claude'`, `PLUGIN_CACHE_SUBPATH`,
  `.claude/skills/` scanning (`scan-marketplace-inventory.py`, `_dep_index.py`).

**Required:** (1) route their layout scanning through the Gap-4/5 `platform-runtime`
layout-resolution operation so both `.claude/skills/**` and the OpenCode layout are covered;
(2) make frontmatter checks/emission target-aware — `_cmd_apply.py:48` must emit the correct
shape per target (`model: anthropic/...` + `mode: subagent` for OpenCode vs. `model: sonnet`
for Claude), and doctor rules must accept both. Test on both targets.

Pass 2 ([08](08-claude-coupling-inventory.md)) sharpened the shape: `plugin-doctor` is **not**
a target-specific skill (an OpenCode author would lint OpenCode output) — split it into a
target-agnostic linting **engine** (the structural/notation/bloat/prose rules — the bulk of the
50+ analyzers stay-agnostic) plus a swappable **Claude rule-pack** (the tool/permission/model-DSL
rules — `_KNOWN_TOOLS`, comma-vs-array, `agent-task-tool-prohibited`, `hardcoded-model-on-canonical`,
the `target/claude/` literal at `_analyze_markdown.py:306`). `rule-provenance.md` (which already
documents the project-vs-Anthropic-schema split) is the natural fork point. The `.claude/skills/**`
resolver duplicated across 6+ analyzers collapses onto the one Gap-4 op.

---

## Closing audit

With Gaps 1-8 landed, the closing audit re-runs:

```bash
grep -rnE '\.claude/|~/\.claude' marketplace/bundles --include='*.py' --include='*.md' \
  | grep -v '/platform-runtime/' | grep -v '\.claude-plugin'
```

The remaining hits are dominated by the accepted set — the behavioural Claude-path
hardcodes in general skill bodies, shared runtime scripts, and authoring tools have been
routed to the four homes, **with the short known-residuals list below**. The accepted
categories the audit confirms:

- **`platform-runtime` internals** — `claude_runtime.py` / `opencode_runtime.py` /
  `runtime_base.py` own the `.claude/` shapes, roots, and per-target layout strings by
  design (excluded by the `-v '/platform-runtime/'` filter; the residual mentions are the
  ABC docstrings documenting what each target returns).
- **The `script-shared/marketplace_paths.py` layout home** — the `_DEFAULT_SKILL_ROOTS` /
  Claude-default cache fallback constants are the sanctioned Gap-4/5 home that backs the
  layout op and falls back to the Claude default when no runtime resolves.
- **OpenCode multi-root discovery lists** — `generate_executor.py` and
  `marshall-steward/bootstrap_plugin.py` deliberately list `.claude/skills` *as one
  cross-compat root among the OpenCode roots* (the resolver probes both layouts); this is
  target-aware behaviour, not a Claude-only hardcode.
- **Docstrings / comments documenting per-target layout** — prose like "On Claude: returns
  the single `.claude/skills` root" describes what the layout op returns; the live resolvers
  themselves route through the op. The 6 sibling plugin-doctor analyzers
  (`_analyze_self_declared_rule_compliance`, `_analyze_allowed_tools_drift`,
  `_analyze_finalize_step_token`, `_analyze_step_configurable_contract`, `_analyze_skill_mode`,
  `_analyze_lesson_id_in_skill_prose`) construct their anchor as `Path / '.claude' / 'skills'`
  (segment-wise, not the `.claude/` literal), so they are docstring-only audit hits; their
  live anchors are a follow-up consolidation onto the Gap-4 op (the `recipe-missing-implements`
  analyzer is the one converted in this gap as the engine/rule-pack reference implementation).
- **Gap-1 settings / permission anchors** — the `.claude/settings*.json` paths now resolve
  inside `claude_runtime.py`; SKILL-body mentions are user-facing prose describing the Claude
  settings file the runtime targets.
- **`references/{topic}.md` pointers** — documentation cross-references, never live resolution.

**Known residuals** — live Claude literals the audit still surfaces (or misses), tracked as
the tail of this workstream rather than re-opening the gap classes:

- `tools-permission-fix/scripts/permission_fix.py` — `DEFAULT_PERMISSIONS` still carries the
  literal `Read(~/.claude/plugins/cache/**)` permission string (Gap-1 grammar residue; should
  render inside `claude_runtime.py`).
- `tools-permission-doctor/scripts/permission_common.py` — the *read-preference* selector
  (`get_project_settings_path`) still inlines `.claude/settings*.json`; only the write path
  delegates to `claude_runtime`.
- `tools-marketplace-inventory/scripts/scan-marketplace-inventory.py` — builds a live
  `./.claude/skills/{skill}/scripts/…` `runtime_mount` display string (Gap-8 residue).
- `plan-retrospective/scripts/check-manifest-consistency.py` and
  `check-routing-decisions.py` — `.claude/` appears in a live `_BOOKKEEPING_PREFIXES`
  filter tuple (benign, but not in any accepted category).
- `extension-api/scripts/extension_discovery.py` — `_scan_project_finalize_steps` builds
  `project_root / '.claude' / 'skills'` **segment-wise**, which the audit grep cannot see
  (Gap-4 residue). The audit should be supplemented with a segment-wise probe
  (`grep -rn "'.claude'" marketplace/bundles --include='*.py'`) to close this blind spot.

## Acceptance — met

- [landed] Permission tooling: Claude settings I/O in `claude_runtime.py`; SKILL bodies call
  `platform-runtime permission …`; OpenCode ops return honest `no-op`.
- [landed] Metrics returns normalized token categories (the transcript JSONL / `message.usage`
  format stays in `claude_runtime`); project-local-skill resolution and bundle/extension
  discovery are target-aware; the shared `session_id` validator is an opaque-token contract.
- [landed] Body-text tool-name divergences (`AskUserQuestion`, `Task:`, `Skill: <entry>`) have a
  recorded disposition in `mapping.json::body_idiom_rewrites` (mirrored in `transforms.md`),
  validated fail-closed at registry load and applied at build time.
- [landed] Terminal-title/hook composer takes a neutral state enum; OpenCode no-op path is the
  end-to-end confirmation deferred to [02](02-validate-opencode-runtime.md).
- [landed] Authoring tools (`plugin-doctor`, `tools-marketplace-inventory`) scan both layouts via
  the layout op and apply target-aware frontmatter checks; `plugin-doctor` carries the
  engine / Claude-rule-pack split (fork point documented in `plugin-doctor/references/rule-provenance.md`).
- [met] The closing-audit grep returns accepted hits plus the tracked known-residuals list
  (see [§ Closing audit](#closing-audit)).
- [met] `verify` passes on all bundles (Claude canary — no regression).

## Dependencies

None beyond the landed baseline. This is the precondition for
[02](02-validate-opencode-runtime.md): the live session must exercise the real
`platform-runtime` path, not the current Claude-hardcoded one.
