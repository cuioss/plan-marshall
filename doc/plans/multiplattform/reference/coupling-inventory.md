# Open Claude-Coupling Inventory

The registry of places where Claude-Code-specific behaviour, vocabulary, layout, or format sits
in general/core code instead of one of the four placement homes
([principles §6](principles.md)). This file lists **open** couplings only — it is the evidence
base the epic's plans draw their deliverables from, and it shrinks as they land.

Every `file:line` here is a **lead**: line numbers drift, so a plan acting on an entry locates
the site by the named symbol, not the line. An entry that cannot be re-found by symbol is
reported as such, never silently skipped.

## A. Runtime contract shape (`platform-runtime`)

| Site | Coupling |
|---|---|
| `platform-runtime/scripts/runtime_base.py` — `project_install_hook` | Target-shaped interface: the ABC docstring names the Claude hook-event vocabulary (`SessionStart`, `UserPromptSubmit`, `Notification`, `Stop`, `PreToolUse:AskUserQuestion`, `PreToolUse:Bash`, `PostToolUse:*`), the `statusLine` command, and `env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE`; the `target` parameter is a settings-file path (e.g. `.claude/settings.local.json`), not a target-opaque handle; `overwrite_statusline` / `overwrite_env_disable` are named for Claude mechanisms |
| `platform-runtime/scripts/runtime_base.py` — `layout_skill_roots`, `layout_bundle_cache_root`, `session_capture`, `metrics_capture`, `metrics_normalized_tokens` docstrings | Target enumeration: each reads "On Claude: … On OpenCode: …" instead of target-neutral intent + the no-op fallback; `subagent_dispatch` names both targets inline ("`Task:` on Claude, `task` on OpenCode") |
| `platform-runtime/scripts/platform_runtime.py` — `_REGISTRY`, `_TARGET_BOOTSTRAP_LIBS` | Registration is scattered: two separate per-target dicts, plus `default="claude"` argparse fallbacks and a bare `target = "claude"` fallback repeated through the module, with no single `_DEFAULT_TARGET` constant; `script-shared/scripts/marketplace_paths.py` repeats its own `'claude'` fallback returns |
| `platform-runtime/scripts/opencode_runtime.py` — `subagent_dispatch` | Hardcodes `subagent_type: "execution-context-level-3"` (a fixed level) while the Claude implementation parameterizes the agent name — both a bug and a target-shaped assumption |

## B. Claude literals in general scripts

| Site | Coupling |
|---|---|
| `tools-permission-fix/scripts/permission_fix.py` — `DEFAULT_PERMISSIONS` | Carries the literal permission string `Read(~/.claude/plugins/cache/**)` — Claude permission-grammar residue that belongs rendered inside `claude_runtime` |
| `tools-permission-doctor/scripts/permission_common.py` — `get_project_settings_path` | The read-preference selector inlines `.claude/settings.local.json` / `.claude/settings.json`; only the write path (`get_project_settings_path_for_write`) delegates to the runtime, and the module docstring claims a delegation the read path does not perform |
| `manage-providers/scripts/_cred_ensure_denied.py` | Renders Claude `permissions.deny` DSL strings (`Read(...)`, `Bash(...)` over `_BASH_VECTORS`) and writes them into `settings['permissions']['deny']` — the same grammar-in-core class as the permission tooling above |
| `extension-api/scripts/extension_discovery.py` — `_scan_project_for_implementors` | Builds `project_root / '.claude' / 'skills'` segment-wise instead of routing through `get_project_skill_roots()` — on another target, project-local finalize-step implementors do not resolve |
| `pm-plugin-development/…/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py` | Builds a `./.claude/skills/{skill}/scripts/…` `runtime_mount` display string (the discovery path beside it is already target-neutral via `iter_project_skill_dirs`) |
| `plan-retrospective/scripts/check-manifest-consistency.py`, `check-routing-decisions.py` — `_BOOKKEEPING_PREFIXES` | `('.plan/', '.claude/')` filter tuple names the Claude project-local root directly |

## C. Emitted-text vocabulary (build-target data)

| Site | Coupling |
|---|---|
| `persona-plan-marshall-agent/standards/tool-usage-patterns.md`, `standards/agent-behavior-rules.md` | Name Claude tools (`Read`/`Write`/`Edit`/`Glob`/`Grep`) as THE tools, with literal call syntax — loaded by every agent, so this is the highest-leverage vocabulary surface. The registered-idiom registry (`mapping.json::body_idiom_rewrites`) is the settled home for cross-target tool-name rewrites; extending it beyond the four registered idioms waits on live-runtime evidence that a rewrite is needed ([validation protocol](opencode-validation-protocol.md)) |
| `tools-file-ops/scripts/constants.py` — `HARNESS_BASH_CEILING_SECONDS` | The 600-second Bash-tool ceiling is a per-target runtime fact stated as a single core constant; consumers derive `execution_tier` routing from it. Single-sourced, but the value itself belongs to the runtime |
| `manage-files/scripts/manage-files.py` — `detect_ide`, `cmd_open_in_ide` | IDE launch inside core file CRUD. Keys on host editor signals (`TERM_PROGRAM`, `__CFBundleIdentifier`), not the assistant target — per-host rather than per-target, but the same relocation argument applies |

## D. Target-specific component candidates (the `targets:` filter's first consumers)

Whole capabilities that exist only on the Claude target and pass the admission test in
[principles §6](principles.md). Until the `targets:` frontmatter mechanism exists, they ship to
every target:

| Candidate | Why target-specific |
|---|---|
| `plan-marshall/commands/tools-fix-intellij-diagnostics.md` | IDE-MCP-bound (`mcp__ide__getDiagnostics`) + Java/Maven toolchain; the whole workflow is N/A without an IDE-MCP host |
| `plan-marshall/references/hook-authoring-guide.md` | Wholly a how-to for Claude's hook-delivery channel (JSON `terminalSequence` envelope, `/dev/tty`, `$CLAUDE_CODE_SESSION_ID`); the agnostic emit path it references already lives behind `platform-runtime` |
| `plan-retrospective/references/permission-prompt-analysis.md` | The whole retrospective aspect is the Claude settings/permission model (`~/.claude/settings.json`, allow/deny/ask, `defaultMode`) |
| `marshall-steward` terminal-title wizard surfaces (`references/menu-terminal-title.md`, the healthcheck twin, the configuration branch, the session-restart prose) | An interactive Claude hook/statusline setup workflow naming every Claude hook event and `CLAUDE_CODE_*` env var. Requires a **split** — only these surfaces scope to Claude; the rest of the steward stays agnostic. The underlying install op stays in `platform-runtime` |

Rejected candidates, recorded so they are not re-proposed:

- `tools-sync-agents-file` — the cross-assistant *bridge* that emits the OpenAI-spec `AGENTS.md`;
  `CLAUDE.md` is merely an optional input source. It applies regardless of host target →
  stays-agnostic. Scoping it to Claude would be normalization-dodging.
- `plugin-doctor` — target-aware, not Claude-only: an OpenCode author lints OpenCode output. The
  documented split (`plugin-doctor/references/rule-provenance.md`) is a target-agnostic linting
  engine plus a swappable Claude rule-pack; the fork point is documentary, with no separate
  dispatch path.
- The plugin-authoring toolset (`plugin-create`/`plugin-maintain`/`plugin-architecture`) — the
  *capability* is target-aware; only the emitted/validated *vocabulary* is Claude-specific →
  build-target data.

## E. Documentation drift

| Site | Drift |
|---|---|
| `doc/developer/distribution.adoc` | Describes the publish matrix as single-entry Claude-only and OpenCode as hypothetical, while `.github/workflows/claude-distribute.yml` carries a live `opencode` matrix entry (`dist-opencode` branch, `opencode` tag prefix) |

## Confirmed clean (no action)

CI/git/build operations (`build-maven`/`build-gradle`/`build-npm`, most of `build-pyproject`,
the `github`/`gitlab`/`sonar` providers, `tools-integration-ci`); metrics storage/aggregation
(`manage-metrics` consumes the runtime's normalized tokens and never parses a transcript);
`manage-change-ledger`, `manage-locks` core, `manage-logging`, `manage-providers` credential
storage (`~/.plan-marshall/credentials`); `plan-doctor`; the shared Extension API; the `.plan/`
executor surface and `marshal.json`; `tools-input-validation`'s `SESSION_ID_RE` (an opaque
token, `^[A-Za-z0-9_-]{1,128}$`). Env vars throughout are `PLAN_*`/`PLAN_MARSHALL_*` outside
`platform-runtime`.

Sanctioned Claude-specific-by-design surfaces: `.claude-plugin/plugin.json` +
`marketplace/.claude-plugin/marketplace.json` (the canonical source format);
`platform-runtime/scripts/{claude_runtime,_claude_runtime_impl,claude_hook}.py` internals;
`marketplace/targets/claude/**` (the verbatim target); the target-aware multi-root resolvers in
`generate_executor.py` and `bootstrap_plugin.py`, which deliberately probe both layouts.
