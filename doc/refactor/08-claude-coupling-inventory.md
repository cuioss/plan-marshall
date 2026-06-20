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
| target-specific skill (`targets:`-scoped) | whole capabilities that exist only on some targets — IDE-MCP command, Claude harness-hook wizard, future OpenCode/Cursor flows | Small |
| prose-neutralize | "Claude Code" naming, host-permission-UI rationale, per-target doc tables | Medium |
| sanctioned-ok (no action) | `.claude-plugin`/`marketplace.json` manifests; the `claude_runtime.py`/`claude_hook.py` concrete impl + env-overridable resolver models (`generate_executor.py`, `bootstrap_plugin.py`). **Not** the `Runtime`/`TargetBase` ABCs, the router, or `manage-terminal-title` — those are active seam work (§D, §A3, §07) | — |
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

### A5. Further format-leak families (surfaced by pass-2 full reads)

| Evidence | Coupling |
|----------|----------|
| `manage-metrics/SKILL.md:21,326-337`, `standards/data-format.md:64,70-77`, `manage-metrics.py:720-739` | the A2 leak is wider than the parser — the **docs and the renderer** also carry the Claude four-field / `<usage>` / billing-weight vocabulary. The normalized-token boundary must reach the doc + render surfaces too |
| `manage-architecture/scripts/_cmd_client.py:110-120` + `standards/resolve-command.md:14,57-59` | `_BASH_CEILING_SECONDS=600` bakes the Claude Bash-tool 600s timeout ceiling into core; `execution_tier` (per_task/orchestrator) routing is *derived* from it. The ceiling is a per-target runtime fact → it should come from the runtime |
| `manage-providers/scripts/_cred_ensure_denied.py:19-80` | emits Claude `permissions.deny` DSL (`Read(~/.plan-marshall-credentials/**)`, `Bash(cat …)`) into the host settings file — same class as the A1 permission-DSL leak (the SKILL prose is already neutralized to "host platform", the emitted rule strings are not) |
| `manage-locks/scripts/merge_lock.py:183-189,316-419` | duplicates the terminal-title glyph vocabulary (`⏳`/`🔒`) and reaches into the title-render surface — co-owns the A3 target-shaped interface |

Destination: all PR-behavior (normalize the contract / source the value from the runtime), except the metrics docs which are prose-neutralize alongside the A2 code fix.

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
claude_hook,opencode_runtime}.py` internals; `generate_executor.py` + `bootstrap_plugin.py`
target-aware resolvers (the **models to reuse**); `_invariants.py:134` (a deliberate
anti-coupling note). (`tools-fix-intellij-diagnostics` was previously listed here; it is better
classed as a target-specific skill — §I.)

## H. cleanup byproducts (incidental, not coupling)

| Evidence | Action |
|----------|--------|
| `skills/manage-worktree/scripts/__pycache__/manage-worktree.cpython-314.pyc` | stale `.pyc`, no source — delete (skill relocated) |
| `plan-marshall/skills/ext-self-review-plan-marshall/scripts/__pycache__/self_review.cpython-314.pyc` | stale `.pyc`, real skill is under `pm-plugin-development/` — delete. **Divergence:** the empty skill is still listed active in the available-skills header despite having no source |
| `doctor-skill-knowledge.md:13` ("Rule 9/10a/11"); `doctor-skills.md:101` (`domain-extension-api:validate_manifest`) | doc-drift bugs (rules are now named; stale notation) — fix in passing |
| `plugin-doctor/references/rule-catalog.md:236` ("PM-Workflow Rules" heading), `:252` ("seven" vs 8 rows); `commands-guide.md:23` ("9 Anti-Bloat" with uncodified names); `skills-guide.md:94`, `metadata-guide.md` (stale counts / bundle-root `plugin.json`) | doc-drift in plugin-doctor reference docs (pm-workflow bundle absorbed; stale counts) — fix in passing |
| `script-shared/SKILL.md:28` (stale `parents[6]` resolution prose); `plan-marshall-plugin/standards/doctor-plan-marshall.md:1` ("PM-Workflow Workflow" naming); `phase-6-finalize/SKILL.md:159,1291` (dispatch table says `standards/lessons-capture.md`, file is `workflow/lessons-capture.md`) | doc/path drift surfaced by pass-2 full reads — fix in passing |

## I. Target-specific skill candidates (gated 4th home)

Capabilities that exist only on some targets and pass the [01](01-finish-portability.md)
placement-model admission test — give them a `targets:` frontmatter scope and let them be absent
elsewhere, rather than shipping everywhere or forcing a runtime no-op.

Confirmed by pass 2 (full-read):

| Candidate | Why target-specific | Scope |
|-----------|---------------------|-------|
| `plan-marshall/commands/tools-fix-intellij-diagnostics.md` | IDE/MCP-bound (`mcp__ide__getDiagnostics`) + Java/maven toolchain; whole workflow N/A without an IDE-MCP host; no-op elsewhere | `targets: [claude]` |
| `marshall-steward` terminal-title **wizard** — `references/menu-terminal-title.md` + the `menu-healthcheck.md:189-231` Step-6b twin + the `menu-configuration.md` Terminal-Title branch + the `SKILL.md:417-441` session-restart prose | a whole interactive Claude hook/statusline setup workflow that names every Claude hook event + `CLAUDE_CODE_*` env + `.claude/settings.local.json` and composes the session-cache path itself; OpenCode no-ops all of it. SPLIT: only these surfaces scope to claude; the rest of steward stays agnostic. The underlying `install-hook` op stays in platform-runtime | `targets: [claude]` |
| `pm-plugin-development/skills/plan-marshall-plugin/scripts/wrapper-tangle-scan.py` + `references/wrapper-tangle.md` | hardcodes plan-marshall's own CI-wrapper source paths; meaningful only in the plan-marshall meta-repo | meta-repo-only |
| `plan-marshall/references/hook-authoring-guide.md` | wholly a how-to-author guide for Claude's hook-delivery channel (JSON `terminalSequence` envelope, `/dev/tty`, `$CLAUDE_CODE_SESSION_ID`); no agnostic content (the agnostic emit path it references already lives behind platform-runtime) | `targets: [claude]` reference |
| `plan-retrospective/.../permission-prompt-analysis.md` | the whole retrospective aspect is the Claude settings/permission model (`~/.claude/settings.json`, allow/deny/ask, `defaultMode`) | `targets: [claude]` reference |
| (future) `opencode-marketplace-install`, Cursor-rules authoring | exist only on those targets | `targets: [opencode]` / `[cursor]` |

**Rejected by pass 2 (NOT target-specific — they normalize):**

- `tools-sync-agents-file` — **CORRECTION** (was listed here): it is the cross-assistant *bridge* that emits the OpenAI-spec `agents.md`; `CLAUDE.md` is merely an optional input source, not its reason to exist. It applies regardless of host target → `stays-agnostic`. Scoping it to claude would be normalization-dodging.
- `plugin-doctor` — make **target-aware**, not Claude-only: an OpenCode author would lint OpenCode output. A target-agnostic linting engine + a swappable Claude rule-pack (the Claude tool/permission/model-DSL rules are build-target; `rule-provenance.md` is the natural fork point).
- the plugin-**authoring** toolset (`plugin-create`/`plugin-maintain`/`plugin-architecture`) — the *capability* is target-aware-make; only the emitted/validated *vocabulary* is Claude-specific → build-target (`frontmatter-standards.md` densest).

**Guard:** the list is short by design. The admission test keeps format-coupling out — the
permission *model* knowledge, metrics *format*, and tool-name *vocab* do NOT come here; they
normalize into the runtime/build-target homes (§A, §C). Only target-bound *capabilities* qualify.

## Coverage

**Pass 1** — 14 partition agents, every `.md`/`.py` under `marketplace/bundles/**` read in full;
each returned `coverage: N / N`. `platform-runtime/**` internals and `.claude-plugin` manifests
were read and classified sanctioned-ok rather than excluded.

**Pass 2 — COMPLETE** (four-home re-classification, char-by-char full reads — no grep/sampling).
All 17 partition slices were full-read across the whole `marketplace/bundles/**` tree. Every
slice **confirmed** pass 1, and — the headline result — **no candidate needed a home beyond the
four**. The placement model holds end-to-end.

Pass-2 verdicts (the "which home / is it target-specific" questions):

- **IDE launch** (`manage-files` `detect_ide`/`cmd_open_in_ide`) → **platform-runtime-behavior**,
  not target-specific and not build-target: it keys off host OS/editor signals
  (`__CFBundleIdentifier`/`TERM_PROGRAM`/`sys.platform`), never on the assistant target.
- **plugin-doctor** → make **target-aware** (agnostic engine + Claude rule-pack), not a 4th-home case.
- **authoring tools** (`plugin-create`/`maintain`/`architecture`) → **build-target** vocabulary, not 4th-home.
- **`tools-sync-agents-file`** → **stays-agnostic** (cross-assistant bridge).
- **target-specific (4th home) confirmed:** `tools-fix-intellij-diagnostics`, the marshall-steward
  terminal-title wizard (split), `wrapper-tangle-scan.py` (meta-repo), and
  `plan-marshall/references/hook-authoring-guide.md` + `plan-retrospective/.../permission-prompt-analysis.md`
  (whole Claude hook/settings how-to references).

Pass-2 net-new items (all fit existing homes):

- `phase-5-execute/standards/operations.md:68` `mcp__sonarqube__*` tool name → build-target (route via the sonar/CI abstraction).
- `phase-1-init/.../inject_project_dir.py` rewrites the executor command-DSL string → platform-runtime-layout (format dependency).
- `plan-retrospective/scripts/extract-chat-signal.py` + `references/chat-history-analysis.md` parse raw Claude session JSONL → platform-runtime-behavior (the A2 transcript-format leak; consume normalized signal, not raw transcript).
- **CORRECTION:** `workflow-integration-git/scripts/git-workflow.py` does **not** emit the `Co-Authored-By: Claude` trailer — only `SKILL.md:134,170` does (build-target); the script carries a comment only (prose-neutralize).
- **CORRECTION:** the `frontend-design` skill pointer (pm-dev-frontend README/css/javascript) is **not** target-specific — only the "Anthropic ships" attribution is prose-neutralize.
- The `ext-triage-*/pr-comment-disposition.md` `AskUserQuestion` block is byte-identical across all domains → neutralize uniformly (one build-target vocab decision).

## Related

- [01 — Finish portability gaps](01-finish-portability.md) — the gap classes these candidates back
- [07 — Target extensibility](07-target-extensibility.md) — the §D seam fixes + the build-target transform engine
- [06 — Execution-context cross-target](06-execution-context-cross-target.md) — the level→model worked example
- [principles §6](principles.md) — the N-target bar
