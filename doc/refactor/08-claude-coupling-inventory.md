# 08 — Claude-Coupling Candidate Inventory

## What this is

The exhaustive candidate registry from a read-everything audit of `marketplace/bundles/**`
(~880 files across all 10 bundles, read in full — not grepped). Every candidate is a place
where Claude-Code-specific behaviour, vocabulary, layout, or format is embedded in
general/core code and must move to one of the [placement-model](01-finish-portability.md)
homes before the system is genuinely N-target ([principles §6](principles.md)).

This is the evidence base behind the [01](01-finish-portability.md) gap classes and the
[07](07-target-extensibility.md) seam work. It cites representative `file:line` evidence per
cluster; where a cluster spans many sites the count is noted rather than every line.

`marketplace/targets/**` (the generator) was out of audit scope — it is reviewed separately
in [07](07-target-extensibility.md).

## Destination tallies

| Destination | What lands here | Weight |
|-------------|-----------------|:------:|
| `platform-runtime` (behaviour + layout) | settings/permission I/O, transcript read, hooks/title, project-local & cache layout resolution | Largest |
| OpenCode build target (transforms + data) | tool-name vocab, frontmatter shape, level→model table, permission DSL, `CLAUDE.md` filename, commit trailer | Large |
| stays-agnostic (source target value from runtime) | CI/git/build ops, metrics storage/aggregation, validators, `.plan/` executor, credentials | — |
| prose-neutralize | "Claude Code" naming, host-permission-UI rationale, per-target doc tables | Medium |
| sanctioned-ok (no action) | `.claude-plugin`/`marketplace.json` manifests, `platform-runtime` internals, IDE-MCP command | — |
| cleanup byproducts | stale `.pyc`, doc-drift bugs | Incidental |

---

## A. platform-runtime — runtime behaviour

### A1. Permission subsystem (paths **and** grammar)
The deepest un-abstracted cluster. Beyond the `.claude/settings*.json` paths, the entire
permission **DSL grammar** is Claude-specific and is treated as core code, not per-target data.

| Evidence | Coupling |
|----------|----------|
| `tools-permission-doctor/scripts/permission_common.py:79-100` | `.claude/settings.json` / `settings.local.json` path resolution |
| `permission_common.py:37-42,67-72` | `permissions.{allow,deny,ask}` settings schema |
| `tools-permission-doctor/scripts/permission_doctor.py:43-61,177-302` | `Skill()/SlashCommand()/Bash()/Write()` permission-string grammar + 24 anti-pattern regexes; `.claude/commands/` |
| `tools-permission-fix/scripts/permission_fix.py:64-72,489-491,775-793` | `EXECUTOR_PERMISSION` literal, `DEFAULT_PERMISSIONS` incl. `Read(~/.claude/plugins/cache/**)`, wildcard emit `Skill({name}:*)` |
| `workflow-permission-web/scripts/permission_web.py:18,24,104-108,438,457-486,545-547` | whole skill is Claude settings I/O: `WebFetch(domain)` grammar + `permissions.allow` schema + `~/.claude/settings.json` |
| `tools-permission-doctor/standards/permission-architecture.md`, `permission-validation-standards.md`, `permission-anti-patterns.md` | the three standards documents are entirely the Claude permission model |

Destination: paths → PR-layout; settings I/O → PR-behavior; the permission **grammar** →
build-target *data* (per-target permission emission), not core code.

### A2. Metrics / transcript engine (path, layout, **and** API format)
| Evidence | Coupling |
|----------|----------|
| `manage-metrics/scripts/manage-metrics.py:152,1377` | `~/.claude/projects` home |
| `manage-metrics.py:115-161,146,159` | `{proj}/{sid}/subagents/agent-*.jsonl` transcript layout |
| `manage-metrics.py:142` | `SESSION_ID_RE` Claude UUID shape |
| `manage-metrics.py:77,81-89,1429-1473` | `<usage>` tag (`USAGE_TAG_RE`), `message.usage` four-field shape (Claude API) |
| `manage-metrics.py:90-95` | `BILLING_WEIGHT_CACHE_*` Anthropic cache-pricing weights |
| `plan-retrospective/scripts/extract-chat-signal.py`, `references/chat-history-analysis.md`, `references/permission-prompt-analysis.md` | parse Claude session JSONL + settings/permission model |

Destination: transcript resolution + parse → PR-behavior; the metrics **storage/aggregation**
layer is identical across targets and stays-agnostic (`manage-metrics` keeps it).
**Boundary ([principles §1](principles.md)):** the op returns **normalized token categories**
(`{input, output, cache_read, cache_creation, total}`); the `<usage>`/`message.usage` format,
JSONL schema, and Anthropic cache weights never cross into core. "Return the transcript path,
core parses it" is a relocated coupling, not an abstraction.

### A3. Hooks, terminal-title, statusline (incl. a target-shaped interface)
| Evidence | Coupling |
|----------|----------|
| `manage-terminal-title/scripts/manage_terminal_title.py:71-101,95-98` | **mislabeled "platform-agnostic"**: `resolve_icon` keyed on Claude hook-event names (`Stop/Notification/PreToolUse/...`) + tool names (`AskUserQuestion`, `Bash`) — a §6 target-shaped interface |
| `marshall-steward/references/menu-terminal-title.md:58-115,280-368` | steward independently enumerates the full hook-event vocabulary, names `CLAUDE_CODE_DISABLE_TERMINAL_TITLE`, and composes+writes the `$CLAUDE_CODE_SESSION_ID/active-plan` cache path itself instead of via a runtime op |
| `marshall-steward/references/menu-healthcheck.md`, `menu-configuration.md` | literal `--settings ~/.claude/settings.json` paths supplied by the steward |
| `plan-marshall/references/hook-authoring-guide.md` (whole) | Claude-Code hook/statusline/envelope contract |
| `tools-script-executor/scripts/generate_executor.py:36-47` | writes `~/.cache/plan-marshall/sessions/{session_id}/active-plan` (session-keyed) |

Destination: PR-behavior. The icon→event mapping and the session-cache write belong behind a
runtime op; `manage-terminal-title` should compose from a target-neutral state, not Claude
event names.

### A4. Host-IDE launch (per-host, not per-target — but same relocation)
| Evidence | Coupling |
|----------|----------|
| `manage-files/scripts/manage-files.py:106-107,127-163,246-325` | `detect_ide` / `cmd_open_in_ide` launch VS Code/Cursor/JetBrains via `TERM_PROGRAM`/`__CFBundleIdentifier` inside core file CRUD |

Destination: PR-behavior (a runtime side-effect), though it keys on host editor, not the Claude target.

---

## B. platform-runtime — filesystem-layout resolution

### B1. Project-local skill / `project:` step resolution (`.claude/skills`, no target branch)
The highest-count cluster: every resolver outside the executor hardcodes `.claude/skills`.

| Evidence | Coupling |
|----------|----------|
| `manage-config/scripts/_config_core.py:186-187` | `Path('.claude')/'skills'/skill/'SKILL.md'` |
| `manage-config/scripts/_cmd_skill_resolution.py:334,435`; `_cmd_skill_domains.py:170,472` | recipe / finalize-step / verify-step / domain discovery roots |
| `manage-config/scripts/manage-config.py:219` | `discover-project` help string |
| `manage-execution-manifest/scripts/manage-execution-manifest.py:3102-3113` | `project:` step → `.claude/skills/{bare}/SKILL.md` |
| `marshall-steward/scripts/determine_mode.py:604-637` | finalize-step discovery |
| `build-pyproject/scripts/extension.py:105-116` | classifies `.claude/skills/*.py` as production (**cross-bundle**) |
| `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_*.py` (6+ analyzers) + `doctor-marketplace.py` | each re-derives `marketplace_root.parent.parent/.claude/skills` |
| `pm-plugin-development/skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py`, `_dep_index.py` | `.claude/skills` scan + `CLAUDE_DIR`/`PLUGIN_CACHE_SUBPATH` constants |
| `tools-script-executor/scripts/generate_executor.py:331-373` | `discover_local_scripts` hardcodes `.claude/skills` (asymmetry — the *embedded resolver* in the same file IS target-aware) |

### B2. Bundle / plugin-cache discovery (the shared foundation)
| Evidence | Coupling |
|----------|----------|
| `script-shared/scripts/marketplace_paths.py:26-27` | `CLAUDE_DIR='.claude'`, `PLUGIN_CACHE_SUBPATH='plugins/cache/plan-marshall'` constants |
| `marketplace_paths.py:245-352` | `get_plugin_cache_path()` + `get_base_path` scopes (`global`→`~/.claude`, `project`→`./.claude`, `plugin-cache`, `cache-first`) — the foundational leak imported across the tree |
| `script-shared/scripts/marketplace_bundles.py:17,114-177` | `.claude-plugin/plugin.json` + versioned plugin-cache layout discovery |
| `extension-api/scripts/extension_discovery.py:24-29` | `get_plugin_cache_path` defaults to `~/.claude/plugins/cache/plan-marshall` (env `PLUGIN_CACHE_PATH` is the only override — the right shape, wrong default) |

Destination: B1+B2 → one `platform-runtime` layout-resolution op (memoised per process), per the
[01](01-finish-portability.md) Gap-4/5 decision. The models to reuse already exist:
`generate_executor.py`'s target-dispatched resolver and `bootstrap_plugin.py`'s
`read_runtime_target()` + per-target `_detect_*_root()`.

---

## C. OpenCode build target — emitted text & frontmatter

### C1. Tool-name vocabulary in body prose (pervasive — the single largest class)
Claude tool names appear as normative instructions in skill/agent/command **bodies**, which the
adapter does not transform.

| Class | Representative sites | Scope |
|-------|---------------------|-------|
| `AskUserQuestion` (+ its `question/header/options/multiSelect` schema, 4-option cap) | every `ext-triage-*/standards/pr-comment-disposition.md` (java, js, python, oci, docs, reqs); `phase-1..6`; `scope-deviation-escalation.md`; `coverage-gathering-contract.md`; `marshall-steward` menus; recipes | all bundles |
| `Task:` dispatch + `execution-context-{level}` variant naming | `phase-3/4/5/6/SKILL.md`, `workflow-overview.md`, `profiles.md`, `ref-workflow-architecture/standards/*`, `plan-marshall/workflow/*` | plan-marshall |
| `Skill:` directive | pervasive across SKILL bodies (handled for *concrete* refs by the adapter; the `Skill: <entry>` loop placeholder is not — see [06](06-execution-context-cross-target.md)) | all bundles |
| `Read`/`Write`/`Edit`/`Glob`/`Grep`/`Monitor` named as THE tools | `dev-agent-behavior-rules/standards/tool-usage-patterns.md` + `agent-behavior-rules.md` (**propagates to every agent**), `manage-plan-documents`, `manage-solution-outline`, `manage-tasks`, `manage-findings`, `pm-documents` recipes/refs, `tools-integration-ci` standards, `workflow-integration-git` invariants | all bundles |
| Frontmatter `tools:` lists | `agents/execution-context.md:9`, `execution-context-reader.md:9`, `plan-retrospective/SKILL.md:6`, command frontmatter | plan-marshall |
| Read-only **capability stated only as Claude tool names** | `untrusted-ingestion/standards/reader-contract.md:9-13`, `threat-model.md` (security-critical containment contract) | plan-marshall |

Destination: build-target (per-target tool-name rewrite **data** + shared engine, per the
settled decision in [07](07-target-extensibility.md)); `dev-agent-behavior-rules` is the
highest-leverage fix because every agent loads it.

### C2. Level → model table (concrete aliases + Claude env var)
| Evidence | Coupling |
|----------|----------|
| `plan-marshall/standards/effort-levels.md:15-31` | `haiku/sonnet/opus/fable`, `claude-opus-4-8`, `CLAUDE_CODE_SUBAGENT_MODEL` |
| `plan-marshall/standards/effort-variants.md` | variant emission + plugin-loader + `CLAUDE_CODE_SUBAGENT_MODEL` |
| `plan-marshall/scripts/effort_presets.py:25,72,180`; `manage-config/scripts/_cmd_effort.py:59` | `opus`/`fable` aliases in shared preset library |
| `extension-api/standards/ext-point-dynamic-level-executor.md:26-99` | level→model table + "subagent runs on Opus" + session-restart + `target/claude/` paths |
| `pm-plugin-development/.../_cmd_apply.py:48`, `plugin-create/scripts/cmd_generate.py`, `frontmatter-standards.md` | emit `model: sonnet` + comma-vs-array `tools:` format |

Destination: build-target data (level-N naming is the correct abstraction; the concrete aliases,
`CLAUDE_CODE_SUBAGENT_MODEL`, and `plugin.json` variant expansion are Claude-target data —
see [06](06-execution-context-cross-target.md)).

### C3. Claude-specific filenames & emitted strings
| Evidence | Coupling |
|----------|----------|
| `pm-documents/skills/recipe-doc-verify/SKILL.md:55,118,122,207` | hardcodes `CLAUDE.md` as the doc-drift-check target (OpenCode → `AGENTS.md`) |
| `workflow-integration-git/SKILL.md:134` | commit trailer `Co-Authored-By: Claude <noreply@anthropic.com>` |
| `manage-lessons/scripts/manage-lessons.py:1396`, `_cmd_auto_suggest.py:186` | emit `/plan-marshall …` slash-command launch strings |
| `pm-plugin-development/.../_cmd_apply.py:236-261`, `cmd_validate.py:210` | `/plugin-update-*` slash-command names |

Destination: build-target (per-target filename / trailer / command-form data).

---

## D. §6 anti-patterns (target enumeration / scattering)

| Evidence | Coupling |
|----------|----------|
| `platform-runtime/scripts/runtime_base.py:126-159` | `project_install_hook` ABC signature + docstring name Claude hook events + `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` — **target-shaped interface** |
| `runtime_base.py:169-180,214-217,359-361,386-389` | ABC docstrings enumerate "On Claude / On OpenCode" |
| `platform_runtime.py:67-76` | `_TARGET_BOOTSTRAP_LIBS={"claude":..,"opencode":..}` core-owned per-target table |
| `platform_runtime.py:239,490,507,513` | silent `default="claude"` fallbacks |
| `opencode_runtime.py:411` | hardcodes `subagent_type:"execution-context-level-3"` (a fixed level) while `claude_runtime` parameterizes — a real inconsistency/bug |
| `pm-plugin-development/.../_analyze_markdown.py:306-313` | literal `if 'target/claude/' in file_path` in a core analyzer |

Destination: these are the [07](07-target-extensibility.md) structural fixes (target-opaque
interface, registry consolidation, parameterize the dispatch level).

---

## E. prose-neutralize (naming & rationale)

| Evidence | Coupling |
|----------|----------|
| `pm-requirements/README.md:7` | "provides **Claude Code** with expert knowledge…" |
| `pm-documents/.../content-review.md:411,423` | "**Claude's role**: …" |
| `pm-documents/skills/ref-svg-diagrams/SKILL.md:99` | "In **Claude Code**, use the Read tool…" |
| `dev-agent-behavior-rules` (SKILL.md + tool-usage-patterns.md) | "trips the host platform's permission UI / security prompt / Bash sandbox heuristic" rationale assumes the Claude permission model |
| `tools-integration-ci/standards/*`, `execution-context.md:38` | "Bash tool timeout (ms)", "run_in_background", "shell-heading heuristic" |
| `manage-architecture/scripts/_cmd_client.py:110-120` | `_BASH_CEILING_SECONDS=600` "capped by the host platform at 600s" |
| `pm-dev-frontend` README/css/javascript | point at the Anthropic-shipped `frontend-design` skill (Claude-only) |

Destination: reword target-neutral, or source the value from the runtime (e.g. the Bash ceiling).

---

## F. stays-agnostic (confirmed clean — no action)

CI/git/build operations (all `build-maven`/`build-gradle`/`build-npm` + most `build-pyproject`;
all `github`/`gitlab`/`sonar` providers; `tools-integration-ci` scripts); metrics
storage/aggregation; `manage-change-ledger`, `manage-locks` core, `manage-logging` format,
`manage-providers` (uses `~/.plan-marshall-credentials`, never `~/.claude`); `plan-doctor`;
all `extension.py` (shared Extension API); `script-shared` build/extension/query layers;
`ref-toon-format`, `dev-general-code-quality`, `dev-general-module-testing`. The `.plan/`
executor surface and `marshal.json` are target-agnostic by design. Env vars throughout are
`PLAN_*`/`PLAN_MARSHALL_*`, never `CLAUDE_CODE_*` (outside platform-runtime).

`input_validation.py:45` `SESSION_ID_RE` is permissive (`^[A-Za-z0-9_-]{1,128}$`) — an opaque
token, not a Claude UUID; only its "Claude Code UUID" docstring/help is prose-coupling. (The
*strict* UUID `SESSION_ID_RE` at `manage-metrics.py:79` is the transcript engine's and folds
into A2, not a shared validator — see [01](01-finish-portability.md) Gap 3.)

## G. sanctioned-ok (Claude-specific by design — no action)

`.claude-plugin/plugin.json` + `marketplace/.claude-plugin/marketplace.json` (the canonical
source-of-truth format the build target consumes); all `platform-runtime/scripts/{claude_runtime,
claude_hook,opencode_runtime}.py` internals; `tools-fix-intellij-diagnostics` (IDE/MCP-bound
command); `generate_executor.py` + `bootstrap_plugin.py` target-aware resolvers (the **models to
reuse**); `_invariants.py:134` (a deliberate anti-coupling note).

## H. cleanup byproducts (incidental, not coupling)

| Evidence | Action |
|----------|--------|
| `skills/manage-worktree/scripts/__pycache__/manage-worktree.cpython-314.pyc` | stale `.pyc`, no source — delete (skill relocated) |
| `skills/ext-self-review-plan-marshall/scripts/__pycache__/self_review.cpython-314.pyc` | stale `.pyc`, real skill is under `pm-plugin-development/` — delete |
| `doctor-skill-knowledge.md:13` ("Rule 9/10a/11"); `doctor-skills.md:101` (`domain-extension-api:validate_manifest`) | doc-drift bugs (rules are now named; stale notation) — fix in passing |

## Coverage

14 partition agents, every `.md`/`.py` under `marketplace/bundles/**` read in full; each
returned `coverage: N / N`. `platform-runtime/**` internals and `.claude-plugin` manifests were
read and classified sanctioned-ok rather than excluded.

## Related

- [01 — Finish portability gaps](01-finish-portability.md) — the gap classes these candidates back
- [07 — Target extensibility](07-target-extensibility.md) — the §D seam fixes + the build-target transform engine
- [06 — Execution-context cross-target](06-execution-context-cross-target.md) — the level→model worked example
- [principles §6](principles.md) — the N-target bar
