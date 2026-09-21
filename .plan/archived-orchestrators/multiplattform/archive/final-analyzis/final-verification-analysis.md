= Final Verification Analysis
:toc: macro

_Reviewed commit: HEAD of `main`_ +
_Verification method: static tree inspection (grep / read / glob) against HEAD_ +
_Evidence labels: OBSERVED (file/symbol read), HYPOTHESIS (named artifact found but would require further inspection to settle)_

== Requirement Rows

=== 010 — Runtime Seam Neutrality

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|010-D1
|010/plan.md
|Target-opaque install op: `project_install_hook` states intent only; no Claude hook-event name, no `CLAUDE_CODE_*`, no settings-file path; absolute-path override is `claude-runtime-internal`
|completely implemented
|OBSERVED `runtime_base.py:228-294` ABC docstring states intent only; zero `CLAUDE_CODE_`, `hook-event`, `On Claude`/`On OpenCode` hits; concrete override in `_claude_runtime_impl.py:264-276` resolves `'claude'` to local settings path; absolute path documented as "Claude-INTERNAL" override
|

|010-D2
|010/plan.md
|Target-neutral ABC docstrings: zero `On Claude` and `On OpenCode` hits in `runtime_base.py`
|completely implemented
|OBSERVED grep `On Claude|On OpenCode` across `runtime_base.py` (1213 lines): zero matches
|

|010-D3
|010/plan.md
|Registration consolidated: `_DEFAULT_TARGET` constant, `_REGISTRY` and `_TARGET_BOOTSTRAP_LIBS` adjacent, `marketplace_paths` fallback uses constant
|completely implemented
|OBSERVED `platform_runtime.py:209-213` — `_DEFAULT_TARGET`, `_REGISTRY`, `_TARGET_BOOTSTRAP_LIBS` all derived from `_TARGET_RECORDS` on adjacent lines; `marketplace_paths.py:134-144` `_default_runtime_target()` lazily imports `platform_runtime._DEFAULT_TARGET` with `'claude'` sentinel fallback
|

|010-D4
|010/plan.md
|Parameterized OpenCode dispatch: `subagent_type` echoes requested agent
|completely implemented
|OBSERVED `opencode_runtime.py:707` `'subagent_type': agent`; `test_opencode_runtime.py:614-623` asserts echo for multiple agent names; `runtime_base.py:1122-1126` documents cross-target contract
|

=== 020 — Target-Scoped Components

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|020-D1
|020/plan.md
|Filter mechanism: `component_targets.py` parses `targets:`, `emits_to()` exists, all emitters honor it
|completely implemented
|OBSERVED `component_targets.py` (651 lines) — `read_target_scope()` (line 397), `emits_to()` (line 469), `excluded_emission_roots()` (line 576); `opencode/emitter.py:563-599` and `claude/emitter.py:143` and `claude/plugin_json_gen.py:98,129` all honor the filter
|

|020-D2
|020/plan.md
|Fail-closed validation: rejects unknown target, empty list, list of only non-component-tree targets
|completely implemented
|OBSERVED `component_targets.py:368-394` `_validate` — three `TargetScopeError` rejection branches: empty list (375-380), unknown target (381-387), only non-component-tree targets (388-393); additional rejections in `read_target_scope()` for malformed YAML, non-list value, non-string item
|

|020-D3
|020/plan.md
|First consumer: `tools-fix-intellij-diagnostics.md` declares `targets: [claude]`
|completely implemented
|OBSERVED `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md:5` frontmatter declares `targets: [claude]`; only component in the marketplace with a `targets:` declaration
|

|020-D4
|020/plan.md
|Authoring surface: `plugin-doctor` targets-scope-invalid rule
|completely implemented
|OBSERVED `_analyze_target_scope.py` (666 lines) `RULE_ID = 'targets-scope-invalid'` (line 105); wired into quality gate at `_runner.py:306`; tested in `test_analyze_target_scope.py` (802 lines)
|

=== 030 — Claude Literal Residuals

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|030-D1
|030/plan.md
|Default permissions render in the runtime: default permissions blob arrives at project-local caller without Claude-only artifacts
|completely implemented
|OBSERVED `permission_fix.py:70-80` delegates via `ensure_default_permissions`; `permission_common.py:143-161` routes through `_active_runtime().permission_ensure_defaults()`; `claude_runtime.py:2654` performs the render + write inside the runtime; callers receive only semantic ids (`defaults_added`/`defaults_removed`)
|

|030-D2
|030/plan.md
|Settings-path reads delegate: `_plugin_cache_root()` has exactly one permission-surface owner; script no longer hardcodes plugin path
|partially implemented
|OBSERVED delegation exists via `_active_runtime().permission_ensure_defaults()` and `layout_bundle_cache_root()`; the plan's named artifacts (`_plugin_cache_root_permission_surface.py`, `plugin_cache_root` constant) were never created; `extension_discovery.py:29-41` `get_plugin_cache_path()` still composes cache root independently (env override + layout op) — not consolidated under single named owner
|Plan-specified symbols/files absent; cache-root resolution not consolidated under one named owner

|030-D3
|030/plan.md
|Credential deny rules render in the runtime: output shows per-credential deny rules without `.claude/settings.json` literal
|completely implemented
|OBSERVED `_cred_ensure_denied.py:90` — `runtime.permission_fix(target, 'protect-path', ...)` — full runtime delegation; zero `.claude` literals in module (grep confirmed); old constants (`_creddeny`, `_CRED_DENY_PREFIX`) fully removed
|

|030-D4
|030/plan.md
|Implementor scan routes through layout resolution: scanner no longer walks `.claude/` for implements-tool registrations
|completely implemented
|OBSERVED `extension_discovery.py:1303` `_scan_project_for_implementors()` iterates `_project_skill_trees()` which resolves via `get_project_skill_roots()` (layout op); only `.claude` strings are in prose/docstrings (lines 35, 1308), not executable code
|

|030-D5
|030/plan.md
|Display and filter strings stop naming `.claude/`: display string no longer contains `.claude/`; `filter_keys` no longer contains `["commands"]`
|partially implemented
|OBSERVED `filter_keys` symbol does not exist anywhere in tree (grep: zero matches) — removed or never landed; `.claude/` literals remain in plugin-doctor display code: `_claude_runtime_impl.py:2148-2149, 2204-2205, 2216-2224` contain `Path('.claude') / 'settings.json'` in display/detail strings
|`filter_keys` removal unverifiable (symbol absent); `.claude/` display literals remain in plugin-doctor hook/settings checks

=== 040 — sync-opencode Inner Loop

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|040-D1
|040/spec.md
|The sync-opencode project-local skill: skill exists at `~/.claude/skills/sync-opencode/`
|refuted
|HYPOTHESIS `~/.claude/skills/` directory does not exist on this machine; what exists is `.opencode/scripts/sync_opencode.py` (deploy engine) and `.opencode/commands/sync-opencode.md` (command wrapper) — the implementation diverged to a different location and runtime target
|Skill exists at `.opencode/` not `~/.claude/skills/`; `_GLOBAL_SKILLS` lead never existed

|040-D2
|040/spec.md
|Unit tests: `python -m pytest sync-opencode -v` shows green gate
|completely implemented
|OBSERVED `test/sync-opencode/test_sync_opencode.py` (412 lines, 16 test functions) covering singular→plural mapping, deploy counts, dry-run, pruning, error paths; registered in `pyproject.toml:445`; `__pycache__` artifacts confirm pytest collection
|

|040-D3
|040/spec.md
|Inner-loop documentation: `distribution.adoc` § "OpenCode" states the symlink rule and flags "optional, un-version-controlled"
|refuted
|OBSERVED `distribution.adoc` (121 lines) has no "OpenCode" section, no `symlink` mentions, no "optional, un-version-controlled" flag; inner-loop docs live in `marketplace-build.adoc:175-232` instead — different file than spec named
|Required section absent from distribution.adoc; equivalent docs exist in marketplace-build.adoc

|040-D4
|040/spec.md
|distribution.adoc states the live matrix: both `claude` and `opencode` rows, opencode row carries `-✓-` across columns
|partially implemented
|OBSERVED `distribution.adoc:84-98` — matrix has both `claude` and `opencode` rows with real values; but `-✓-` token not present anywhere (grep: zero matches), no `bundle-install` column exists
|Both rows present; exact `-✓-` schema and `bundle-install` column absent

=== 050 — Structural Directive Coverage

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|050-D1
|050/spec.md
|`read_directive` in the structural vocabulary: `STRUCTURAL_VOCABULARY` includes `read_directive` with step guards
|completely implemented
|OBSERVED `body_transform_engine.py:95-99` `STRUCTURAL_VOCABULARY` includes `'read_directive': 'directive_rewrites'`; line 107-110 `REQUIRED_PLACEHOLDERS` has `'read_directive': frozenset({'path'})`; line 144-147 `READ_DIRECTIVE_RE` regex; line 285 `rewrite_read_directives()`; line 235-262 load-time validation; full test coverage in `test_body_transforms.py`
|

|050-D2
|050/spec.md
|Call-schema block neutralized: the step-schema block reading "On Claude — `call git ...` / On OpenCode — `call bash ...`" replaced by target-neutral directive language
|still open
|HYPOTHESIS grep for `call-schema`, `Call-schema`, `call git`, `call bash` step-schema patterns returns zero matches across tree; `git log -S` returns empty — artifact has no history of existing in committed form
|Target artifact never existed in committed tree; done-when unverifiable against a concrete before-state

|050-D3
|050/spec.md
|ext-triage escalation lines neutralized: `plugin-escalation-from-triage` and `triage-escalation-to-plugin` blocks no longer carry `On Claude` / `On OpenCode` labels
|still open
|HYPOTHESIS grep for `plugin-escalation-from-triage` and `triage-escalation-to-plugin` returns zero matches; `git log -S` returns empty — blocks have no git history; current ext-triage SKILL.md files are already target-neutral
|Target artifact never existed in committed tree; done-when unverifiable

|050-D4
|050/spec.md
|Remaining normative tool-prose sites: zero `On Claude` / `On OpenCode` hits across the bundle
|partially implemented
|OBSERVED grep `On Claude|On OpenCode` across `marketplace/bundles/**/*.md`: 13 distinct sites across 7 files (phase-5-execute, phase-6-finalize, ext-point-execution-context-workflow, platform-runtime contract/terminal-title-architecture/no-op-policy, plan-retrospective, marshall-steward)
|13 `On Claude`/`On OpenCode` sites remain; ~10 are platform-runtime behavioral descriptions, ~3 are tool/directive references

=== 060 — Authoring Surface Target Awareness

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|060-D1
|060/spec.md
|Target-aware generation and validation: `generate.py` respects targets, emits target tree; plugin-doctor or build step rejects unknown/empty targets
|completely implemented
|OBSERVED `generate.py:40,54` `--target` choices from `TARGET_REGISTRY.keys()` + `all`; line 403 unknown targets rejected; `component_targets.py:385` build rejects unknown targets; `_analyze_target_scope.py:438` authoring-time scanner derives names from `register_target` calls; `TARGET_REGISTRY` (`__init__.py:26`) is single source of truth
|

|060-D2
|060/spec.md
|`frontmatter-standards.md` split: cleanly readable, two-section layout, no long inline tables
|completely implemented
|OBSERVED `frontmatter-standards.md` — "Target split" callout at document head (line 5-13); Claude-target material marked with explicit callout blocks throughout; target-agnostic field semantics first and main sections; no long inline tables; clean TOC (lines 15-24)
|

|060-D3
|060/spec.md
|Rule-pack declaration closed: canonical list single-sourced, referenced by `generate.py`, `plugin_doctor`, and `plugin-create`
|partially implemented
|OBSERVED `rule-provenance.md:14-25` "Engine / Claude rule-pack split" section is canonical single source; `plugin_doctor` (19 hits) and `plugin-create` (`cmd_validate.py:19,71`) reference it; NOT OBSERVED `generate.py` has no reference to rule-pack — generator manages target generation, not linting
|`generate.py` does not reference rule-pack list (spec error — generator has no lint concern)

|060-D4
|060/spec.md
|Layout and store literals routed: layout literal policy pinned to one authoritative list; scripts read that list rather than emitting ad hoc path lists
|partially implemented
|OBSERVED layout resolution routed through platform-runtime `layout skill-roots` / `layout bundle-cache-root` ops; `marketplace_paths.get_project_skill_roots` uses layout op; NOT OBSERVED `STORE_LITERAL` or `store_literal` — zero matches across tree; no explicit layout-literal list constant exists
|Layout routing functionally achieved via runtime ops; explicit `STORE_LITERAL` constant absent

|060-D5
|060/spec.md
|Settings/permission prose normalized: permission rule authoring docs reflect current runtime; no lingering Claude-only settings references
|partially implemented
|OBSERVED `permission-architecture.md`, `permission-anti-patterns.md`, `permission-validation-standards.md` all carry explicit "Provenance: Claude rule-pack" + Claude-only scope markers; `tools-permission-doctor/SKILL.md:22,26` routes through `platform_runtime permission analyze`, forbids hardcoded settings paths; NOT OBSERVED no OpenCode permission-architecture equivalent exists
|Claude-only docs properly scoped; no complementary OpenCode permission standards document

=== 070 — Runtime Fact Prose and Single Sources

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|070-D1
|070/spec.md
|Layout code routed: layout literal documented across bundle is single authoritative list; scripts read that list
|completely implemented
|OBSERVED `configurable_contract.py:103,147` uses `get_project_skill_roots()` via layout op; `generate_executor.py:1282-1292` resolves cache-recovery roots through `layout_bundle_cache_root` op; `marketplace_paths.py:900-910` `get_base_path()` routes through `_invoke_settings_op()`; `CLAUDE_DIR` retained only as fallback anchor (line 114)
|

|070-D2
|070/spec.md
|`manage-terminal-title` split: doc/policy separated from script; "when to run" docs and "how to compute" code read from same source
|completely implemented
|OBSERVED `terminal-title-architecture.md:5-19` documents three-way split; `claude_runtime.py:382-389` confirms icon palette/body logic in manage-terminal-title; `manage-terminal-title/SKILL.md` is pure leaf library with no hook-event vocabulary
|

|070-D3
|070/spec.md
|Hook/session/ceiling facts sourced: docs use runtime-detected facts; no hardcoded counts
|completely implemented
|OBSERVED `runtime_base.py:398-399,510-560` — session tracking via `session_bind()`, `session_resolve_plan()` in ABC; zero `claude.json` hits anywhere (grep: zero matches); zero `max_tokens`/`600000` hits in skill py files; `effort-levels.md:37` documents consumer-controlled `CLAUDE_CODE_SUBAGENT_MODEL` sourced from Level Table
|

|070-D4
|070/spec.md
|Effort table single-sourced: effort table authored in one place, referenced from docs
|completely implemented
|OBSERVED `effort-levels.md:1-3` "Single source of truth" declaration; Level Table at lines 13-21; both `variant_emitter.py` (claude + opencode) cite `effort-levels.md` and carry `LEVEL_TABLE`; zero `claude-haiku`/`claude-sonnet`/`claude-opus` hits outside `effort-levels.md`
|

|070-D5
|070/spec.md
|Command form and agent-instructions file: file already loaded
|completely implemented
|OBSERVED `marketplace_paths.py:355-366` `agent_instructions_filename()` returns per-target (`'AGENTS.md'` for opencode, `'CLAUDE.md'` for claude); `determine_mode.py:439-443` `file_ops` rule resolved per target; `test_determine_mode.py:215-230` pins asymmetry assertion; `run --command-args` notation shared across build scripts
|

=== 080 — Permission Skills Through the Registry

|===
|ID |Source |Requirement |Verdict |Evidence |Missing / Refuted

|080-D1
|080/spec.md
|The crossing inventory, and the stop condition: defined crossing inventory exists and a stop condition is stated
|still open
|HYPOTHESIS `coupling-inventory.md` does not exist in version-controlled tree; grep for `claude_runtime` across three permission scripts returns 4 hits (not zero); `doc/plans/multiplattform/reference/` directory does not exist
|Crossing inventory artifact absent; stop condition (zero grep hits) not met

|080-D2
|080/spec.md
|A semantic vocabulary for the crossings: invoke/consume/define/register vocabulary exists and is authoritative
|completely implemented
|OBSERVED `runtime_base.py:639-648` `permission_configure(scope, grants: list[dict])` — "semantic permission intents"; `runtime_base.py:676-702` `permission_fix(operation, arguments)` — semantic dicts; `runtime_base.py:751-771` `permission_web_apply(scope, add, remove)` — domain names; `contract.md:350-672` all permission ops documented by intent; DSL constants live in `permission_fix.py` (target renders layer), not at boundary
|

|080-D3
|080/spec.md
|The skills route through the registry: per-skill domain resolution via registry working and documented
|partially implemented
|OBSERVED `permission_common.py:32-33` imports `_runtime_for_target` from `platform_runtime`, not `claude_runtime`; `opencode_runtime.py:334-363` honest no-ops for all permission ops; `test_permission_rendering_protect_path.py:391-410` pins Claude succeeds / OpenCode no-op; HYPOTHESIS `grep -n "claude_runtime"` across three permission scripts: 4 matches (3 docstrings + 1 function-local isinstance check in `permission_common.py:49`)
|4 `claude_runtime` mentions remain (3 docstrings + 1 isinstance type check); isinstance check architecturally necessary

|080-D4
|080/spec.md
|Retire the inventory rows by re-derivation: inventory rows retired after re-derivation
|still open
|HYPOTHESIS `coupling-inventory.md` does not exist in tree; `doc/plans/multiplattform/reference/` directory does not exist; without the inventory, no rows to retire
|Inventory artifact absent; retirement meaningless without the inventory

== Tally Tables

=== By Source Document

|===
|Source |Completely |Partially |Refuted |Still Open |Total

|010/plan.md
|4
|0
|0
|0
|4

|020/plan.md
|4
|0
|0
|0
|4

|030/plan.md
|3
|2
|0
|0
|5

|040/spec.md
|1
|1
|2
|0
|4

|050/spec.md
|1
|1
|0
|2
|4

|060/spec.md
|2
|3
|0
|0
|5

|070/spec.md
|5
|0
|0
|0
|5

|080/spec.md
|1
|1
|0
|2
|4

|===
|*Total*
|*21*
|*8*
|*2*
|*4*
|*35*

=== By Category

|===
|Verdict |Count |%

|Completely implemented
|21
|60.0

|Partially implemented
|8
|22.9

|Refuted to implement
|2
|5.7

|Still open
|4
|11.4

|*Total*
|*35*
|*100.0*
|===

== Operator Rulings (post-verification review)

The tables above are the executor's report, preserved as provenance. Follow-up
history checks overturned four verdicts and the operator disposed of the rest.
Corrected dispositions:

*040-D1, 040-D3 — complete with relocation.* The sync engine
(`.opencode/scripts/sync_opencode.py` + command wrapper) and the inner-loop
docs (`marketplace-build.adoc` "OpenCode inner loop") exist; only the paths
diverged from the spec. Not refuted — the taxonomy's refuted class requires a
recorded reason, and relocation is none.

*050-D2, 050-D3 — complete (vacuously satisfied).* `git log -S` over the full
history returns nothing for the call-schema block, the ext-triage escalation
blocks, or `call bash`; the sole `call git` hit is an unrelated June test
file. The artifacts never existed, so there was nothing to neutralize.

*030-D5(a) — dissolved; 030-D5 stays partial on (b) alone.* `filter_keys` has
zero git history — the symbol never existed rather than being renamed. The
`.claude/` display literals in `_claude_runtime_impl.py` remain but are ruled
out of scope (Claude-target-specific runtime code).

*080-D1, 080-D4 — complete.* The crossing inventory exists ledger-resident at
`.plan/orchestrator/multiplattform/reference/coupling-inventory.md`
(163 lines, §§A–E, §A retired, §§B–D rows live); the standalone copy was
deleted deliberately at ingest per operator decision. Row retirement operates
through the ledger report-and-rederive mechanism. The remaining 4
`claude_runtime` mentions (3 docstrings + 1 isinstance gate) are accepted as
type-level necessities.

*All other partials — accepted as satisfying intent, no work owed:* 030-D2
(layout op is the implicit single owner), 040-D4 (matrix with both rows plus
prose verification suffices), 050-D4 (per-target behavioral docs stay; only
tool-instruction prose converts), 060-D3 (spec was wrong — `generate.py` runs
no lint rules), 060-D4 (runtime-op routing suffices, no `STORE_LITERAL`
owed), 060-D5 (no OpenCode permission-arch doc needed), 080-D3 (accepted
above).

Corrected tally: *35 completely implemented (100%), 0 partial, 0 refuted,
0 still open* — with the qualifications above. Every item in
`final-verification-open-tasks.md` is thereby disposed; that document remains
as the record of what was asked, not of what is owed.

Follow-up noted, not staged: the ingested `archive/README.md` still links
`reference/coupling-inventory.md` relatively, resolving to a nonexistent
`archive/reference/` — one-line fix for the multiplattform owner.
