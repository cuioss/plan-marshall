# Marketplace Audit — Claude-Coupling Clusters

The whole-marketplace audit registry: every Claude-specific structure found in
`marketplace/bundles/**` that is not registered in the [coupling inventory](coupling-inventory.md)'s
§A–§E tables and not sanctioned. Sites are **leads** — locate by symbol/section, re-derive
membership before acting. **Drawn by** names the plan that scopes a cluster.

## M1 — `Read:` full-line load directive (cross-bundle structural vocabulary gap)

The Claude `Read` tool name used as a normative full-line load directive
(```` ```text``` fences containing `Read: standards/{file}.md`) — structurally the sibling of the
registered `Skill:` directive, but absent from `STRUCTURAL_VOCABULARY`
(`marketplace/targets/body_transform_engine.py`), so `assert_source_vocabulary_mapped` never fires
for it and it emits verbatim to every non-verbatim target. ~130 occurrences repo-wide: pm-dev-java
(10 skills), pm-dev-frontend (5), pm-dev-java-cui (5), pm-dev-python (1), plan-marshall (13 files),
pm-plugin-development (11), pm-documents (3), pm-requirements (1) — re-derive the set. Home:
build-target data (`directive_rewrites.read_directive` + engine matcher). **Drawn by `050`.**

## M2 — Normative tool-invocation prose beyond the registered idioms

- The ext-triage `pr-comment-disposition.md` escalation lines, byte-identical across **seven**
  skills (`ext-triage-python`/`-java`/`-js`/`-oci`/`-docs`/`-reqs`/`-plugin` — the set is a lead,
  re-derive): of four `AskUserQuestion` occurrences on three lines per file only the backticked
  one is reachable by `rewrite_inline_code`; the ESCALATE-row "AskUserQuestion call" and the
  flow-branch line are bare normative instruction.
- `pm-dev-java/skills/manage-maven-profiles/SKILL.md` § Step 2 — a full `AskUserQuestion:` YAML
  call block (`question`/`header`/`options[].label/.description`/`multiSelect`): the Claude
  parameter model as workflow, unreachable by every transform.
- "using the Write tool" steps: `pm-dev-java-cui/recipe-cui-logging-enforce/SKILL.md` 4e;
  `pm-documents` `recipe-verify-architecture-diagrams`, `recipe-verify-ascii-diagrams`,
  `recipe-doc-verify` (its `CLAUDE.md`/`AGENTS.md` half is target-aware; the tool-name half is not).
- `pm-documents/skills/ref-asciidoc/workflow/link-verification.md` — `AskUserQuestion:` blocks and
  literal `Read(file_path=…)`/`Glob(pattern=…)`/`Edit(` call syntax.
- `pm-dev-python/skills/pytest-testing/standards/testing-pytest.md` — cites `CLAUDE.md` as the
  authority for a target-neutral rule; `pm-dev-java-cui/README.md` — `/plan-marshall action=recipe`
  invocation form (READMEs are outside the body-transform path);
  `pm-documents/…/content-review.md` "Apply careful analysis (Claude)" (second site in that file).

Home: prose-neutralize in source (name the act, not the tool), keeping one backticked
registered-idiom carrier where the mechanism must be named. **Drawn by `050`.**

## M3 — pm-plugin-development authoring surfaces are Claude-only

- `plugin-create/scripts/cmd_generate.py` emits Claude-only frontmatter (comma-joined `tools`,
  raw `model` passthrough) with no `resolve_runtime_target()` — asymmetric with the target-aware
  `plugin-doctor/scripts/_cmd_apply.py::apply_missing_frontmatter`.
- `plugin-create/scripts/cmd_validate.py` — Claude schema/tool enums in the validator (array-tools
  error, Task prohibition, `prohibited_fields`), undeclared as rule-pack; its 3-field skill enum
  additionally disagrees with `frontmatter-standards.md` and `fix-templates.json`.
- `plugin-doctor/assets/fix-templates.json` — Claude-only payloads (`model: sonnet`,
  comma-tools, `/plugin-update-*`), with `missing-frontmatter` and `array-syntax-tools` entries
  dead (ignored by the target-aware consumer).
- `plugin-doctor/scripts/_cmd_apply.py::apply_array_syntax_fix` — unconditional Claude-form
  rewrite, undeclared as a rule-pack mutator.
- `plugin-architecture/references/frontmatter-standards.md` — Claude parser rules, tool set, model
  aliases (`sonnet`/`opus`/`haiku`), color enum, `.claude` mount paths, and settings-permission
  sections stated as THE authoring standard (three "host platform" rewordings are the only
  neutralization); named authoritative by `_analyze_skill_mode.py`.
- `plugin-create/references/agent-guide.md` + `standards/workflow-create-agent.md`,
  `plugin-doctor/references/{agents-guide,fix-catalog,skills-guide}.md` — model aliases, Claude
  schema URLs, `~/.claude` scope prose.
- `plugin-doctor/workflow/tool-coverage.md` — a second, wider (13-name) Claude tool vocabulary,
  not named in the rule-pack split; `_analyze_askuserquestion_reachability.py`,
  `agent-glob-resolver-workaround`, and the bash-chain/shell-substitution/tmp-redirect rules are
  rule-pack members by content but not by declaration in `rule-provenance.md`.
- `plugin-doctor/references/commands-guide.md` § Reference Format — `SlashCommand:`/`Task:`/
  `Skill:` dispatch grammar as prose.
- `_analyze_markdown.py::_BUILD_OUTPUT_PREFIXES` — core-owned per-target table with a Claude
  fallback default (principles §6 anti-pattern); `standards/doctor-agents.md` still states the
  `target/claude/` literal; `_doctor_shared.resolve_runtime_target` falls back to `"claude"`.

Home: build-target data + rule-pack declaration + platform-runtime for mounts/settings sections.
**Drawn by `060`.**

## M4 — pm-plugin-development layout/settings/permission residue

- `tools-marketplace-inventory/scripts/_dep_index.py` — own `CLAUDE_DIR`, `project` scope as
  `cwd/.claude` (bypasses `get_project_skill_roots()`), duplicated
  `_first_existing_bundle_cache_root`; `--scope global` is an orphan flag that crashes
  (`ValueError: Invalid scope: global`); `plugin-cache` as user-facing CLI vocabulary.
- `plan-marshall-plugin/extension.py` Axis-D — `('.claude', 'pm-plugin-development')` claimed
  prefix + `.claude/settings.json` "harness configuration" docstring (SKILL.md mirror).
- `plugin-doctor/SKILL.md` — "Glob `~/.claude/{component}/`" discovery prose (+ commands-guide
  twin) contradicting the analyzers' layout-op discipline; `.claude/skills/…` example paths.
- `plugin-doctor/scripts/_plugin_pin_trap.py` — models the Claude plugin manager's stores and
  parses the `~/.claude/plugins/cache/…` announced-path grammar (oracle logic is agnostic).
- `tools-corpus-language-server/SKILL.md` — `${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PROJECT_DIR}`
  placeholders + deployed-cache path in the `lspServers` registration form.
- Permission-grammar doc twins: `plugin-doctor/SKILL.md` § Non-Prompting Requirements,
  `tools-marketplace-inventory/SKILL.md`, `verification-mode` (SKILL + two standards),
  `_analyze_tmp_redirect_in_skills.py` docstring + `rule-catalog.md` rows,
  `plugin-architecture/references/token-optimization.md` + `minimal-wrapper-pattern.md`
  `Bash(./.claude/…)` examples.
- `ext-outline-workflow/SKILL.md` § Human-Gated Harness-Config Classification (+
  `standards/change-types.md` restatement) — the predicate table IS Claude paths/keys
  (`.claude/settings*.json`, `hooks` events, `permissions.allow/deny`); the intent stays, the
  table becomes per-target runtime data.
- `plugin-task-plan/SKILL.md` — PreToolUse hook-matching semantics as the stated reason for a
  command-authoring rule.
- Terminology: `harness` across ~10 pm-plugin-development files.

Home: platform-runtime for layout/settings queries; build-target for grammar examples;
prose-neutralize elsewhere. **Drawn by `060`.**

## M5 — plan-marshall layout & `.claude` contract text

- Live code: `extension-api/scripts/configurable_contract.py::resolve_step_doc_path` (segment-wise
  `.claude/skills`, twin of the registered `_scan_project_for_implementors`);
  `tools-script-executor/templates/execute-script.py.template::_newest_cache_scripts_dir`
  (Claude-only recovery root — the template file, not the sanctioned emitted resolver);
  `script-shared/scripts/marketplace_paths.py::get_base_path` `global`/`project` scopes (no
  runtime routing, distinct from the registered fallback returns).
- Contract prose: `extension-api/SKILL.md` resolution table + `standards/extension-contract.md`
  cache structure + `ext-point-execution-context-workflow.md` (incl. "Claude Code session has
  been restarted"); `manage-execution-manifest/standards/manifest-schema.md`;
  `manage-config/standards/data-model.md`; `tools-script-executor/SKILL.md` bootstrap Glob;
  `phase-3-outline/SKILL.md` harness-config routing rule keyed on `.claude/settings*`;
  `plan-marshall/workflow/q-gate-validation.md` validators (`.claude/skills/**`,
  `.claude/worktrees/`); phase-3/4 never-mutate lists; `phase-6-finalize/standards/`
  "`.claude/` ruff coverage" dimension.
- General-script docstrings enumerating "Claude → …; OpenCode → …": `_config_core.py`,
  `marketplace_paths.py` helpers, `extension_discovery.py`, `build-pyproject/extension.py`.
- Coverage prose naming `.claude/**` as the dotfile tree (`manage-architecture`,
  `consumer-sweep.md`, `q-gate-validation.md`, `data-model.md`) and wizard/help prose naming
  `.claude/skills` (`skill-domains-setup.md`, `menu-recipes.md`, `_cmd_skill_domains.py`,
  `determine_mode.py` argparse help).

Home: platform-runtime (route/query) + prose-neutralize. **Drawn by `070`.**

## M6 — plan-marshall hook/channel/runtime-fact prose

- `manage-terminal-title` — the skill self-declares "knows no hook-event vocabulary" while its
  SKILL.md carries the event→state mapping table and
  `standards/terminal-title-architecture.md` is a full Claude channel specification
  (`terminalSequence`/`sessionTitle`/`statusLine`, `SessionStart:clear` release point, nine
  render triggers, settings probes, session-cache mapping). Needs the same split as the steward
  wizard: channel spec → platform-runtime docs; pure composer contract stays.
- Hook-event facts in general skills: `manage-status` build-busy concurrency contract
  (standards + SKILL + three scripts), `manage-locks/scripts/merge_lock.py` comment (narrows its
  Confirmed-clean listing), `persona-plan-orchestrator/standards/orchestration-model.md`
  (`terminalSequence` as "the sole channel"), `manage-architecture` search justification
  ("refused by the PreToolUse enforcement hook"), `phase-1-init`/`execution.md`/
  `tool-usage-patterns.md` (`SessionStart` as THE session-id mechanism),
  `plan-marshall/scripts/_invariants.py`, `worktree-handling.md` § "Why Not a PreToolUse Hook".
- `marshall-steward/references/menu-enforcement-hook.md` (+ menu-configuration row, SKILL.md) — a
  second interactive Claude hook-install wizard, unlisted in §D's terminal-title split; and the
  steward `--settings ~/.claude/settings*.json` invocations (menu-configuration, wizard-flow,
  menu-healthcheck) violating the permission skills' own "no settings-path literal" rule.
- Bash-tool runtime facts as universal prose: `build-systems-common.md` auto-backgrounding,
  `wait-pattern.md`/`run-config-standard.md` 120 s/600000 ms, CI standards "Bash tool timeout"
  directives, `blocking-wait-pattern.md`, `pyproject-impl.md` duplicate 600 s,
  `execute-task`/`phase-5-execute` call-shape rules stated unconditionally.
- `<usage>` envelope outside the registered metrics surfaces: `phase-1-init/SKILL.md` transition
  rule, `_config_defaults.py` calibration comment.
- Claude-as-runtime prose: bundle `README.md` install path, `credentials.py` help +
  `_cred_ensure_denied.py` docstring, `trusted-domains.md` + `domain-lists.json` seeded
  `code.claude.com`/`www.anthropic.com` full-trust defaults, `dispatch-granularity.md`
  "Anthropic system prompt", plugin-GC and agent-registry rationales, cache script docstrings.
- Terminology: `harness` ~60 sites; the persisted `harness_cancellation` enum is a
  deliberate-non-migration candidate (data-migration cost).

Home: platform-runtime for the facts (ceiling/session/channel), prose-neutralize for rationale.
**Drawn by `070`, except the enforcement-hook wizard split — a §M11 candidate with no drawing
plan (plan `070` fixes only its `--settings` literals).**

## M7 — effort/model table restated outside the build-target single source

`plan-marshall/standards/effort-levels.md` (full table + `claude-opus-4-8` +
`CLAUDE_CODE_SUBAGENT_MODEL` rationale + the cross-target note that `model_map` in the OpenCode
mapping "is reused by the Claude target"), `effort-variants.md`, `effort_presets.py` docstrings
and argparse help, `_cmd_effort.py` "sits above Opus", `ext-point-dynamic-level-executor.md`
re-tabulation. The build-target single source (`LEVEL_TABLE` + `model_map`) also has a
cross-target import direction principles §6 forbids. Home: build-target data; bundle surfaces
reference, never restate. **Drawn by `070`.**

## M8 — slash-command form emitted or persisted by general scripts

`/marshall-steward` remediation strings across `manage-config` (nine scripts),
`workflow-integration-github`/`-gitlab`, `tools-integration-ci`, `manage-run-config`,
`workflow-integration-git`, `prepare_execute.py`, `tools-file-ops/constants.py`,
`generate_executor.py` (also `/sync-plugin-cache`); `gitignore_setup.py` persists
`# Planning system (managed by /marshall-steward)` into a tracked file. Home: build-target data
(per-target command form via one lookup). **Drawn by `070`.**

## M9 — `CLAUDE.md` as THE agent-instructions file

`marshall-steward/references/architecture-setup.md` (whole sub-operation keyed on `CLAUDE.md`),
`determine_mode.py` asymmetric `['CLAUDE.md']` vs `['CLAUDE.md','AGENTS.md']` rule files (bug +
coupling), and "`CLAUDE.md` § …" cited as authority in `pr_intent_section.py`, `create-pr.md`,
steward SKILL/landing-cycle, `adr-template.adoc`, `testing-methodology.md`, `git-workflow.py`.
Home: platform-runtime agent-instructions-file resolution + prose-neutralize. **Drawn by `070`.**

## M10 — repo-scoping references (meta-repo `.claude/` tree as normative)

`finalize-step-preference-emitter.md` six-level relative link into `.claude/skills/…`;
`manage-metrics/standards/data-format.md` lock-step obligation on the meta-repo audit script;
`analyze-logs.py` comment; `cwd-keyed-store-resolution-audit.md`, steward maintenance/upgrade
references; `_gate_coverage.py` ParityCell "`.claude`" lint-scope strings. Same class as the §D
`wrapper-tangle` note — recorded so the repo-scoping design accounts for them. **Registered; no
drawing plan yet.**

## M11 — target-specific component candidates (additions to §D)

`pm-plugin-development/skills/plugin-architecture/references/askuserquestion-patterns.md` — a
whole-file knowledge body about the Claude `AskUserQuestion` schema; passes the §6 admission
test; needs the same file-level `targets:` mechanism as the registered reference candidates.
`marshall-steward` enforcement-hook wizard surfaces (M6). **Registered; blocked on plan `020`'s
mechanism plus the file-level extension.**

## Zero-finding coverage

The audit's pattern battery returned zero new findings for: `.claude` literals in the seven
pm-dev/code-intelligence bundles (manifests only); `CLAUDE_CODE_*` env vars outside registered
surfaces (`CLAUDE_CODE_SUBAGENT_MODEL` moved to M7); transcript/`message.usage` parsing outside
the registered chat-signal cluster; `mcp__` names outside registered/candidate surfaces;
`Co-Authored-By` literals in scripts; model IDs outside the sanctioned tables; `plan-doctor`
confirmed clean. The seven plugin-doctor analyzer anchors re-derived independently — the
inventory's membership list is complete.
