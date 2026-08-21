# Open Claude-Coupling Inventory

The registry of places where Claude-Code-specific behaviour, vocabulary, layout, or format sits
in general/core code instead of one of the four placement homes
([principles §6](principles.md)) — the evidence base the epic's plans draw from. Sections A–E
hold the **open** couplings; [`marketplace-audit.md`](marketplace-audit.md) extends them with the
whole-marketplace audit clusters §M1–§M11 (drawn by plans `050`–`070` where scoped); the closing
sections record the **deliberate non-migrations** and the **confirmed-clean boundary**, so intent
and open work are never conflated. The **Drawn by**
column names the plan that scopes an entry; an entry with no plan is recorded open work awaiting
a future plan — registered here precisely so a scoping exclusion is never a silent loss.

Every `file:line`-level pointer here is a **lead**: locate the site by the named symbol, not a
line. An entry that cannot be re-found by symbol is reported as such, never silently skipped.

## Closing a row

A row leaves this inventory when **the coupling it names is gone from the tree** — not when a plan
claiming it merges. The two are different: a plan can land with a deliverable descoped, renegotiated,
or partially met, and a row retired on the strength of a merge would then record work that was never
done.

So the closing test is a **re-derivation, never a plan status**. Re-run the detection the row's own
`Coupling` column describes — the search, the symbol lookup, the zero-hit grep it was written
from — and read the result:

| Re-derivation | What happens to the row |
|---|---|
| Finds nothing | The coupling is gone. **Delete the row.** |
| Still finds it | The row stays. Update `Drawn by` to the plan that will finish it, and narrow the `Coupling` text to what actually remains, so the next reader re-derives the residue rather than the original. |
| Cannot be re-derived at all (the symbol is gone, the detection no longer applies) | Treat as **not closed**. Report it, and rewrite the row against the current tree before deciding — a detection that no longer parses is an unanswered question, not a clean result. |

**A closed row is deleted, not archived.** This document records the couplings that are *open*; one
that no longer exists is not a coupling, and a "formerly open" section would turn the work list into
a changelog, which the repository's documentation standards forbid. The durable record of what was
closed, how, and under whose verification is the closing plan's run report at
`doc/plans/{epic}/{plan-name}/report-NN.md` — git holds that, so deleting the row loses nothing.

**The one case where a row must not simply vanish:** when the plan closed it by *deciding* rather
than by *removing*. A coupling deferred on purpose moves to
[Deliberate non-migrations](#deliberate-non-migrations); one sanctioned as target-specific-by-design
moves to [Confirmed clean](#confirmed-clean-no-action). Those two sections exist so intent is never
mistaken for oversight, and a decision deleted as if it were a fix is exactly the silent loss the
`Drawn by` column guards against.

A section whose rows all close keeps its heading and records that it holds nothing open. The
headings are a taxonomy of coupling kinds, not a list of outstanding items: deleting one would leave
a reader unable to tell a category that was checked and found clear from a category nobody looked at.

## A. Runtime contract shape (`platform-runtime`)

No open entries. Each row's own detection was re-derived clean: a case-sensitive search for
`On Claude` / `On OpenCode` over `runtime_base.py` returns nothing, as does one for the Claude
hook-event vocabulary, `statusLine`, `CLAUDE_CODE_*`, and every spelling of either target name;
`project_install_hook` takes a target identifier with target-defined conflict keys rather than a
settings-file path; the target→class registration is one adjacent block in `platform_runtime.py`
behind a `_DEFAULT_TARGET` constant, held in lockstep with
`marketplace_paths._DEFAULT_RUNTIME_TARGET` by test, and holding the subclass import too, so
registering a target is one contiguous edit; and `opencode_runtime.subagent_dispatch` echoes the
requested agent.

**What these detections did NOT cover**, recorded so the clean result is not read wider than it is:
they were searches for target ENUMERATION, so they say nothing about an operation whose docstring
never enumerated one. Four `Runtime` operations still document no way to decline — `project_initial_setup`
and `health_check` state `Returns: … (success or error)`, while `layout_skill_roots` and
`layout_bundle_cache_root` state no status vocabulary at all — which leaves a target that cannot
implement them nothing to point at when it says so. That is a contract-shape gap rather than a
Claude coupling, so it belongs to no row here; plan `010`'s run report records it as residue for a
later plan to scope.

## B. Claude literals and formats in general scripts

| Site | Coupling | Drawn by |
|---|---|---|
| `pm-plugin-development/…/tools-marketplace-inventory/scripts/_dep_index.py` — `CLAUDE_DIR`, `get_base_path('project')` | Resolves the `project` scope as `cwd / '.claude'` from its own module constant, while the `plugin-cache` scope beside it routes through `get_bundle_cache_roots()` | — |
| `pm-plugin-development/…/plugin-doctor/scripts/` — the analyzers that construct `… / '.claude' / 'skills'` segment-wise as live anchors (`_analyze_self_declared_rule_compliance`, `_analyze_allowed_tools_drift`, `_analyze_finalize_step_token`, `_analyze_step_configurable_contract`, `_analyze_skill_mode`, `_analyze_lesson_id_in_skill_prose`, `_analyze_mutates_source_order` — membership is a lead, re-derive by segment-wise probe) | Each re-derives the project-skills anchor instead of routing through the layout helper in `_doctor_shared.py`, and `_doctor_shared.py`'s claim that analyzers call the helper is stale for these | — |
| `script-shared/scripts/marketplace_paths.py` — `CLAUDE_DIR`, `PLUGIN_CACHE_SUBPATH`, `_DEFAULT_BUNDLE_CACHE_ROOTS`, `_DEFAULT_SKILL_ROOTS` | Composes the Claude cache and skill roots segment-wise as the fallback `get_bundle_cache_roots()` / `get_project_skill_roots()` return when the layout op is unreachable. It cannot import the runtime's composer without a cycle, so the segments are spelled in two places and can drift silently — the fallback for an op is the copy least likely to be noticed when the op's own layout changes. Remedy candidates: a shared constant neither side owns, or a lockstep test of the kind already held between `_DEFAULT_RUNTIME_TARGET` and `platform_runtime._DEFAULT_TARGET` | — |
| `pm-plugin-development/…/plugin-architecture/references/frontmatter-standards.md`, `references/token-optimization.md` | State the runtime mount point as `./.claude/skills/…` in prose. The inventory script that built the same string now derives it from the layout op; these are the doc-side residue of that class, and a script-scoped sweep does not reach them | — |
| `workflow-permission-web/scripts/permission_web.py` | Renders `WebFetch({domain})` permission-grammar strings and performs Claude settings I/O itself — the whole skill is the same grammar-in-general-script class as the permission tooling above, and a `.claude`-literal sweep does not catch the grammar half | — |
| `tools-permission-doctor/scripts/permission_common.py`, `tools-permission-fix/scripts/permission_fix.py` | Bound to `claude_runtime` by direct import rather than through the runtime registry (`platform_runtime._REGISTRY`): settings load/save, both settings-path selectors, and the default-permission renderer all resolve to the Claude implementation whatever `runtime.target` says. **Neither skill declares a `targets:` filter, and an unscoped component is emitted to every target** (`marketplace/targets/component_targets.py::emits_to`), so on an OpenCode project these are reachable through the generated executor and would write `.claude/settings*.json` — the coupling is not confined to Claude installs. It also fails the [principles §6](principles.md#6-open-to-further-targets) cost bar: adding a target means editing these general skill scripts. The settings-mapping argument is the other half — the Claude settings-file *shape* crosses into `ensure_default_permissions` as a parameter, which §1 forbids; closing that means restructuring every `permission_fix` subcommand, not one call. **Remedy:** routing through the registry with the ops declining elsewhere — but that is blocked on a vocabulary fix first, because `permission configure` and `permission fix --operation add|remove|ensure` take permission-DSL strings as arguments, so rerouting them would oblige every other runtime to parse Claude's grammar. A `targets: [claude]` filter was **considered and rejected** (PR #1319 review): these skills are mixed — the platform-routed ops already honour the target correctly, so scoping the component would remove the working half to contain the broken one, and would make them permanently unavailable on OpenCode rather than fixed | `080` |
| `tools-permission-fix/scripts/permission_fix.py` — `EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`, the `Skill(…)` / `SlashCommand(…)` wildcard generators, `TIMESTAMP_PATTERN` / `DATE_PATTERN`, `normalize_path_perm`, `is_individual_script_permission` | Renders and parses Claude permission-DSL strings in a general script. The *default* permission set is rendered behind the runtime; this residue is not, and is the same grammar-in-a-general-script class as the `workflow-permission-web` row: the executor and broad-python constants, the marketplace wildcard generation, and the timestamp-consolidation patterns all encode the DSL's shape. A `.claude`-literal sweep does not catch it, because the grammar half carries no path literal | `080` |
| `tools-permission-doctor/scripts/permission_doctor.py` analysis rules + the three permission standards documents (`permission-architecture.md`, `permission-validation-standards.md`, `permission-anti-patterns.md`) | The Claude permission model as analysis subject matter (`Skill()`/`Bash()`/`Write()` grammar, anti-pattern regexes, `.claude/commands/`) — rule-pack-class knowledge, a different shape than live render/resolve residue. Relocating it is what remains open here; `permission-architecture.md` § "Resolution Priority" describes the read preference the selectors actually apply, so nothing is open there | — |
| `plan-retrospective/scripts/extract-chat-signal.py`, `_chat_provenance.py`, `_chat_gate_decisions.py` (`OPERATOR_DECISION_TOOL = 'AskUserQuestion'`), `references/chat-history-analysis.md` | Parse raw Claude session JSONL with harness-shape recognisers (injected-envelope grammar, notice prefixes, decision markers) — transcript-format coupling of the class the metrics ops normalize; destination is platform-runtime behaviour (consume normalized signal, not raw transcript) | — |
| `tools-script-executor/scripts/generate_executor.py` — `discover_local_scripts` | Hardcodes `.claude/skills` as its sole project-local root at build time, while the *embedded* resolver the same file generates is target-aware multi-root — an asymmetry inside one file | — |
| `tools-script-executor/scripts/generate_executor.py` — the session-cache write (`~/.cache/plan-marshall/sessions/{session_id}/active-plan`) | A session-keyed side effect that belongs behind a runtime op | — |

## C. Emitted-text vocabulary and stated runtime facts

| Site | Coupling | Drawn by |
|---|---|---|
| `persona-plan-marshall-agent/standards/tool-usage-patterns.md`, `standards/agent-behavior-rules.md` | Name Claude tools (`Read`/`Write`/`Edit`/`Glob`/`Grep`) as THE tools, with literal call syntax — loaded by every agent, the highest-leverage vocabulary surface. The registered-idiom registry (`mapping.json::body_idiom_rewrites`) is the settled home for cross-target tool-name rewrites; extending it beyond the registered idioms waits on live-runtime evidence that a rewrite is needed ([validation protocol](opencode-validation-protocol.md)) | — |
| `manage-metrics` documentation and render surfaces (`SKILL.md`, `standards/data-format.md`, the renderer) | Carry the Claude `message.usage` / `<usage>` / billing-weight vocabulary in prose and column labels; the normalized-token boundary the scripts enforce must reach the doc and render surfaces too | — |
| `manage-lessons/scripts/` (emits `/plan-marshall …` launch strings), `pm-plugin-development/…/_cmd_apply.py` + `cmd_validate.py` (emit `/plugin-update-*` slash-command names) | Runtime-emitted slash-command strings assume the Claude command form; per-target command-form data is the build-target home | — |
| Prose naming Claude as the assistant: `pm-requirements/README.md` ("provides Claude Code with expert knowledge…"), `pm-documents/…/content-review.md` ("Claude's role"), `pm-documents/skills/ref-svg-diagrams/SKILL.md` ("In Claude Code, use the Read tool…"), `pm-dev-frontend` README/css/javascript (the Anthropic-ships attribution), `phase-5-execute/standards/operations.md` (`mcp__sonarqube__*` tool name) | Target-neutral rewording, or route the named value through the appropriate abstraction (the sonar tool name through the CI abstraction) | — |
| `tools-file-ops/scripts/constants.py` — `HARNESS_BASH_CEILING_SECONDS` | The 600-second Bash-tool ceiling is a per-target runtime fact stated as a single core constant; consumers derive `execution_tier` routing from it. Single-sourced, but the value itself belongs to the runtime | — |
| `manage-files/scripts/manage-files.py` — `detect_ide`, `cmd_open_in_ide` | IDE launch inside core file CRUD. Keys on host editor signals (`TERM_PROGRAM`, `__CFBundleIdentifier`), not the assistant target — per-host rather than per-target, but the same relocation argument applies | — |
| `opencode_runtime.py` — `metrics_capture` manual path vs `claude_runtime.py` — `_write_token_cursor` / `_manage_metrics_end_phase` | The metrics persistence boundary is **target-neutral** (it shells out to `plan-marshall:manage-metrics end-phase`) but lives in `claude_runtime`. The Claude implementation calls it and reports success; the OpenCode implementation reaches no boundary at all and reports the same success shape, so an explicit `--total-tokens` is acknowledged and then lost. A target reporting success for work it did not do is the exact failure the no-op policy exists to forbid. Remedy: relocate the boundary to a shared home and have both targets call it — or, if OpenCode genuinely cannot persist, decline with `no-op` | — |
| `platform-runtime/SKILL.md` — the 24-operation table (9 rows) plus the `description:` frontmatter | Nine op rows end in "no-op on OpenCode" and two additionally parenthesise Claude-specific behaviour (`session push-title-token`, `session reload-directive`); the frontmatter names both targets. This is the same coupling plan 010/D2 removed from the ABC docstrings, one file over: per-target no-op status is restated in a shared skill body instead of being read from the target's own runtime, so a third target makes all nine rows silently incomplete rather than merely unstated. Remedy: the op table states intent only, and no-op status is surfaced from each runtime per `standards/no-op-policy.md` | — |

## D. Target-specific component candidates (the `targets:` filter's consumers)

Whole capabilities that exist only on the Claude target and pass the admission test in
[principles §6](principles.md). The `targets:` frontmatter mechanism now exists (plan `020`), so a
candidate carrying its own frontmatter is scoped by declaring it. A candidate that is a file INSIDE a
skill cannot be scoped INDEPENDENTLY: the mechanism is frontmatter-level, a reference file carries no
frontmatter, and the skill's own `SKILL.md` declaration governs the whole directory — so such a file
ships wherever its parent skill ships, all-or-nothing, and scoping it alone needs a file-level
mechanism that does not exist. The `Scoped` column records which candidates have been taken.

| Candidate | Why target-specific | Drawn by | Scoped |
|---|---|---|---|
| `plan-marshall/commands/tools-fix-intellij-diagnostics.md` | IDE-MCP-bound (`mcp__ide__getDiagnostics`) + Java/Maven toolchain; the whole workflow is N/A without an IDE-MCP host | `020` | yes — declares `targets: [claude]` |
| `plan-marshall/references/hook-authoring-guide.md` | Wholly a how-to for Claude's hook-delivery channel (JSON `terminalSequence` envelope, `/dev/tty`, `$CLAUDE_CODE_SESSION_ID`); needs a file-level scoping mechanism, since references carry no frontmatter | — | no — a file inside a skill; it ships wherever its parent skill ships, and scoping it alone needs the file-level mechanism |
| `plan-retrospective/references/permission-prompt-analysis.md` | The whole retrospective aspect is the Claude settings/permission model (`~/.claude/settings.json`, allow/deny/ask, `defaultMode`); same file-level mechanism need | — | no — a file inside a skill; it ships wherever its parent skill ships, and scoping it alone needs the file-level mechanism |
| `marshall-steward` terminal-title wizard surfaces (`references/menu-terminal-title.md`, the healthcheck twin, the configuration branch, the session-restart prose) | An interactive Claude hook/statusline setup workflow naming every Claude hook event and `CLAUDE_CODE_*` env var. Requires a **split** — only these surfaces scope to Claude; the rest of the steward stays agnostic. The underlying install op stays in `platform-runtime` | — | no — needs the steward skill split, which plan `020` left out of scope |
| `pm-plugin-development/skills/plan-marshall-plugin/scripts/wrapper-tangle-scan.py` + `references/wrapper-tangle.md` | Hardcodes plan-marshall's own CI-wrapper source paths; meaningful only in this meta-repository (a repo-scoping concern rather than a target-scoping one, recorded here so the `targets:` mechanism's design accounts for it or explicitly declines it) | — | no — a repo-scoping concern, not a target-scoping one |
| `pm-plugin-development/skills/plugin-architecture/references/askuserquestion-patterns.md` | A whole-file knowledge body about the Claude `AskUserQuestion` schema (interfaces, UI behaviours, caps); passes the §6 admission test; needs the file-level mechanism like the reference candidates above ([audit](marketplace-audit.md) §M11) | — | no — a file inside a skill; it ships wherever its parent skill ships, and scoping it alone needs the file-level mechanism |
| `marshall-steward` enforcement-hook wizard surfaces (`references/menu-enforcement-hook.md` + configuration row + SKILL prose) | A second interactive Claude hook-install workflow, parallel to the terminal-title wizard split above ([audit](marketplace-audit.md) §M6) | — | no — needs the steward skill split, which plan `020` left out of scope |

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

| Site | Drift | Drawn by |
|---|---|---|
| `doc/developer/distribution.adoc` | Describes the publish matrix as single-entry Claude-only and OpenCode as hypothetical, while `.github/workflows/claude-distribute.yml` carries a live `opencode` matrix entry (`dist-opencode` branch, `opencode` tag prefix) | `040` |

## Deliberate non-migrations

Recorded as intent so their absence from the plans is never read as an oversight:

- **No existing waiting call site migrates onto the `wait_for` runtime op.** The detach-and-notify
  orchestration seam, the CI abstraction's bounded-wait verbs, the finalize CI wait, and the
  build-server long poll stay as they are; migrating them is follow-up work to take up
  deliberately, per ADR-011's placement decision, not residue to sweep.

## Confirmed clean (no action)

CI/git/build operations (`build-maven`/`build-gradle`/`build-npm`, most of `build-pyproject`,
the `github`/`gitlab`/`sonar` providers, `tools-integration-ci`); metrics storage/aggregation
(`manage-metrics` scripts consume the runtime's normalized tokens and never parse a transcript);
`manage-change-ledger`, `manage-locks` core, `manage-logging`, `manage-providers` credential
storage (`~/.plan-marshall/credentials`); `plan-doctor`; the shared Extension API; the `.plan/`
executor surface and `marshal.json`; `tools-input-validation`'s `SESSION_ID_RE` (an opaque
token, `^[A-Za-z0-9_-]{1,128}$`). Env vars throughout are `PLAN_*`/`PLAN_MARSHALL_*` outside
`platform-runtime`.

Sanctioned Claude-specific-by-design surfaces: `.claude-plugin/plugin.json` +
`marketplace/.claude-plugin/marketplace.json` (the canonical source format);
`platform-runtime/scripts/{claude_runtime,_claude_runtime_impl,claude_hook}.py` internals;
`marketplace/targets/claude/**` (the verbatim target); `bootstrap_plugin.py`'s per-target root
detection; and the **embedded** multi-root resolver `generate_executor.py` generates into the
executor, which deliberately probes both layouts. The sanction covers that embedded resolver
only — the same file's `discover_local_scripts` and session-cache write are open entries in §B.
