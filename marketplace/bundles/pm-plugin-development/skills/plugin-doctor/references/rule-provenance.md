# Plugin-Doctor Rule Provenance

Every rule emitted by `plugin-doctor` must have a documented provenance — the lesson, decision, or design contract that introduced it. This catalog is the source-of-truth audit trail; if a rule appears in `_doctor_shared.py` registries or in any `_analyze_*.py` / `_doctor_analysis.py` emitter without a row here, that rule is unsupported and must be removed.

## Classification

| Class | Meaning |
|-------|---------|
| **structural** | Validates file / component / argparse / metadata structure. Failure means the artifact does not match its declared schema. |
| **content** | Validates the textual content of a marketplace artifact — bloat thresholds, prose drift, hard-coded paths, checklist patterns. |
| **style** | Naming conventions, ordering, formatting conventions that do not affect runtime behaviour but degrade authoring experience when drifted. |
| **safety** | Enforces a `dev-agent-behavior-rules` hard rule. Violations are runtime hazards (security prompts, shell-construct rejection, prefix-binding silent failures). |

## Rule Provenance Table

The table enumerates every rule emitted by the in-tree analyzers. The `Emitter` column names the module that constructs the finding; `Source` cites the lesson, decision, or architectural contract that introduced the rule.

### Agent rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `agent-task-tool-prohibited` | safety | `_doctor_analysis.py` | Project convention — Anthropic schema retains `Task` as an alias for `Agent` (https://code.claude.com/docs/en/sub-agents#restrict-which-subagents-can-be-spawned, verified 2026-05-17) so this is not a schema violation; plan-marshall forbids `Task` in agent `tools:` because spawning generic subagents from inside a phase bypasses workflow enforcement (lesson `2026-04-24-12-001`). See `pm-plugin-development:plugin-architecture` references/agent-design.md. |
| `agent-maven-restricted` | safety | `_doctor_analysis.py` | Build-system isolation contract — only `maven-builder` may execute Maven commands. See `pm-plugin-development:plugin-architecture` references/agent-design.md. |
| `agent-lessons-via-skill` | structural | `_doctor_analysis.py` | Plugin architecture contract — agents record lessons via `manage-lessons`, not via self-invoked commands. See `pm-plugin-development:plugin-architecture` references/agent-design.md. |
| `agent-skill-tool-visibility` | structural | `_doctor_analysis.py` | Project convention — Anthropic schema does not require `Skill` in `tools:` (https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields, verified 2026-05-17); plan-marshall requires it because agents that cannot invoke skills cannot participate in workflow dispatch chains. See `pm-plugin-development:plugin-architecture` references/agent-design.md. |
| `agent-glob-resolver-workaround` | safety | `_doctor_analysis.py` (delegates to `_analyze_shared.check_agent_glob_resolver_workaround`) | Lesson `2026-04-27-18-005` — `Glob` in agent `tools:` invites hand-rolled discovery that should be delegated to a canonical resolver script. Exemption mechanism: structured frontmatter flag `forwards_tool_capabilities: true` (lowercase YAML boolean). The legacy body-comment marker `# resolver-glob-exempt:` is no longer authoritative. |

### Workflow / prose rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `workflow-hardcoded-script-path` | structural | `_doctor_analysis.py` | Executor-notation contract — workflows must reference scripts via `{bundle}:{skill}:{script}` notation, never via hard-coded relative paths. See `plan-marshall:tools-script-executor`. |
| `workflow-prose-parameter-inconsistency` | content | `_doctor_analysis.py` | Plugin architecture contract — prose adjacent to `execute-script.py` bash blocks must reference parameter values consistent with the actual script API. |
| `prose-verb-chain-consistency` | content | `_analyze_verb_chains.py` (via `_doctor_analysis.py`) | Lesson `2026-04-18-16-001` — drift between prose verb chains and registered argparse subcommands produced silent runtime rejections. |
| `refine-contract-violation` | safety | `_analyze_phase2_refine_contract.py` (via `_doctor_analysis.py`) | Lesson `2026-05-16-14-001` and recurring anti-pattern `feedback_phase2_refine_never_implements` — phase-2-refine MUST NOT write outside `.plan/local/plans/{plan_id}/**` or `.plan/local/worktrees/{plan_id}/**`. See `plan-marshall:phase-2-refine/SKILL.md` § Enforcement → Allowed write paths. Runtime complement: `plan-marshall:plan-marshall:planning.md` § "Post-dispatch contract assertion". |
| `notation-staleness` | structural | `_analyze_notation_staleness.py` (via `_doctor_analysis.py`) | Lesson `2026-05-22-12-002` — `generate_executor` derives a script's three-part executor notation from its filename, so renaming an entrypoint script silently changes its public notation; callers that still reference the old third segment resolve to `Unknown notation`. The analyzer flags any notation whose third segment has no matching `{script}.py` file under the resolved `scripts/` directory and suggests the hyphen/underscore-flipped canonical form. Runtime complement: the `generate_executor` drift warning. |

### Skill rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `missing-frontmatter` | structural | `_doctor_analysis.py` | Anthropic skills schema — "Every skill needs a `SKILL.md` file with two parts: YAML frontmatter between `---` markers ..." See https://code.claude.com/docs/en/skills#frontmatter-reference (verified 2026-05-17). |
| `invalid-yaml` | structural | `_doctor_analysis.py` | Anthropic skills schema — frontmatter is YAML between `---` markers; parsing must succeed. See https://code.claude.com/docs/en/skills#frontmatter-reference (verified 2026-05-17). |
| `missing-name-field` | structural | `_doctor_analysis.py` | Project convention — Anthropic schema treats `name` as optional ("If omitted, uses the directory name", see https://code.claude.com/docs/en/skills#frontmatter-reference, verified 2026-05-17), but plan-marshall requires explicit `name` for executor-notation stability. See `pm-plugin-development:plugin-architecture` references/skill-design.md. |
| `missing-description-field` | structural | `_doctor_analysis.py` | Project convention — Anthropic schema treats `description` as recommended (see https://code.claude.com/docs/en/skills#frontmatter-reference, verified 2026-05-17); plan-marshall promotes it to required so skill catalogs render deterministically. See `pm-plugin-development:plugin-architecture` references/skill-design.md. |
| `missing-tools-field` | structural | `_doctor_analysis.py` | Project convention — Anthropic schema treats `tools` as optional ("Inherits all tools if omitted", see https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields, verified 2026-05-17); plan-marshall requires explicit tool declarations on agents/commands for least-privilege auditability. See `pm-plugin-development:plugin-architecture` references/agent-design.md. |
| `misspelled-user-invocable` | style | `_doctor_analysis.py` | Anthropic skills schema — canonical spelling is `user-invocable` with hyphen. See https://code.claude.com/docs/en/skills#frontmatter-reference (verified 2026-05-17). |
| `missing-user-invocable` | structural | `_doctor_analysis.py` | Project convention — Anthropic schema makes `user-invocable` optional (defaults to `true`, see https://code.claude.com/docs/en/skills#frontmatter-reference, verified 2026-05-17); plan-marshall requires explicit declaration so the value is auditable per component. See `pm-plugin-development:plugin-architecture` references/skill-design.md. |
| `skill-invokable-mismatch` | structural | `_doctor_analysis.py` | Project convention — internal consistency invariant between SKILL.md frontmatter and `plugin.json` registration. No Anthropic schema rule. See `pm-plugin-development:plugin-architecture` references/skill-design.md. |
| `skill-naming-noun-suffix` | style | `_doctor_analysis.py` | Plugin architecture contract — skill directory names must not end with a reserved noun suffix (`-executor`, `-manager`, etc.) because those suffixes are reserved for spawnable marketplace agents. See `pm-plugin-development:plugin-architecture` references/skill-design.md § "Skill Naming Convention". |
| `skill-resolver-gap` | content | `_doctor_analysis.py` | Lesson `2026-04-27-18-005` — LLM-Glob discovery prose without an adjacent `execute-script.py` invocation re-introduces the resolver-gap anti-pattern. |

### Sub-document rules

Sub-documents are `standards/*.md`, `references/*.md`, `workflow/*.md`, `recipes/*.md`, and `templates/*.md` inside skill directories.

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `subdoc-bloat` | content | `_doctor_analysis.py` | Plugin architecture contract — sub-documents have BLOATED / CRITICAL line-count thresholds; suppressible via `quality.file-bloat: ack-<slug>` frontmatter. See `file-bloat-ack` entry below. |
| `subdoc-forbidden-metadata` | structural | `_doctor_analysis.py` | Project convention — Anthropic schema is silent on sub-document frontmatter; plan-marshall forbids component metadata in sub-documents because the marketplace inventory scanner indexes any file with `name:` as a component and creates phantom entries. See `pm-plugin-development:plugin-architecture` references/skill-design.md. |
| `subdoc-hardcoded-script-path` | structural | `_doctor_analysis.py` | Executor-notation contract — sub-documents must reference scripts via `{bundle}:{skill}:{script}` notation, never via hard-coded relative paths. |
| `subdoc-checklist-pattern` | content | `_doctor_analysis.py` | Lesson — checkbox patterns (`- [ ]`, `- [x]`) are human UI elements with zero value for LLMs. Exception: `templates/` files (rendered by GitHub). |
| `subdoc-display-detail-violation` | content | `_doctor_analysis.py` | Agent-return-shape contract — `display_detail` ≤80 chars, ASCII-only, no trailing period. Source: `plan-marshall:ref-workflow-architecture/standards/agents.md`. |

### File-level rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `file-bloat` | content | `_doctor_analysis.py` | Plugin architecture contract — agents/commands have BLOATED / CRITICAL line-count thresholds; suppressible via `quality.file-bloat: ack-<slug>` frontmatter. |
| `checklist-pattern` | content | `_doctor_analysis.py` | Lesson — checkbox patterns in LLM-consumed component markdown. Exception: `templates/` files. |
| `backup-pattern` | safety | `_doctor_analysis.py` | Repository-hygiene contract — `*.bak`, `*.orig`, `*~` files indicate uncommitted backup artefacts. |

### Cross-file rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `duplication` | content | `_cmd_cross_file.py` | Standards-coherence contract — content duplicated across skills should be extracted to a single canonical location. |
| `extraction` | content | `_cmd_cross_file.py` | Standards-coherence contract — content present in multiple files should be extracted to one. |
| `terminology` | style | `_cmd_cross_file.py` | Standards-coherence contract — same concept must use the same terminology across files. |

### Argument-naming rules (rule pack)

Activated unconditionally per lesson `2026-04-29-23-002`. Cross-checks marketplace prose against the actual argparse declarations of the scripts that prose references. All four rules emit `severity: error` and `fixable: false`.

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `ARGUMENT_NAMING_NOTATION_INVALID` | structural | `_analyze_argument_naming.py` | Lesson `2026-04-29-23-002` — three recurrences of stale-notation drift in ~3 days. |
| `ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN` | structural | `_analyze_argument_naming.py` | Lesson `2026-04-29-23-002`. |
| `ARGUMENT_NAMING_FLAG_UNKNOWN` | structural | `_analyze_argument_naming.py` | Lesson `2026-04-29-23-002`. |
| `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` | structural | `_analyze_argument_naming.py` | Lesson `2026-04-29-23-002` — the Canonical Forms table at `plan-marshall:dev-agent-behavior-rules/standards/argument-naming.md` is the documented contract; if it drifts from argparse, every author who consults it writes broken prose. |

### manage-* invocation rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `manage-findings-invocation-invalid` | structural | `_analyze_manage_findings_invocation.py` (via `_doctor_analysis.py`) | Lesson `2026-04-29-23-002` recurrence — three canonical invalid spellings of `manage-findings` notation surfaced as LLM hallucinations. |
| `manage-invocation-invalid` | structural | `_analyze_manage_invocation.py` | Lesson `2026-04-29-23-002` generalization — same drift class across seven heaviest-referenced `manage-*` / `workflow-integration-*` script families. |
| `missing-canonical-block` | style | `_analyze_manage_invocation.py` | D1 of the argparse-surface-drift remediation plan — every in-scope SKILL.md must publish a `## Canonical invocations` section as the in-skill source-of-truth mirror of the `manage-invocation-invalid` rule. |

### Phase-6 finalize step termination

Four rules guarding `mark-step-done` invocations. Source: phase-6 finalize-orchestration contract (silent-failure surface).

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `MARK_STEP_DONE_STALE_NOTATION` | structural | `_analyze_markdown.py::check_mark_step_done_violations` (via `_doctor_analysis.py`) | Phase-6 finalize-orchestration contract — the stale underscored `manage-status:manage_status` does not resolve; canonical form is `manage-status:manage-status`. |
| `MARK_STEP_DONE_MISSING_PHASE` | structural | same | Phase-6 finalize-orchestration contract — without `--phase`, the step termination is routed to the wrong phase record. |
| `MARK_STEP_DONE_MISSING_OUTCOME` | structural | same | Phase-6 finalize-orchestration contract — without `--outcome`, the step cannot be terminated unambiguously. |
| `finalize-step-token-mismatch` | structural | `_analyze_finalize_step_token.py::scan_finalize_step_token` (via `doctor-marketplace.py::cmd_quality_gate`) | Phase-6 finalize-orchestration contract — a finalize-step skill's documented `mark-step-done --step <token>` (under `--phase 6-finalize`) must equal the skill's manifest step_id (`{bundle}:{skill}` for `OPTIONAL_BUNDLE_FINALIZE_STEPS` members; `project:{name}` for `.claude/skills/finalize-step-*`). A drifted token mis-keys `phase_steps`, so the `phase_steps_complete` handshake reports the step missing and the halt-and-retry recovery loops forever. |

### Script-safety rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `argparse_safety` | safety | `_doctor_analysis.py::scan_argparse_safety` | Lesson `2026-04-17-012` — argparse prefix-matching silently binds retired flags when `allow_abbrev=True`. |

### Simplification rules (SIMPLICITY_*)

Five static detectors that are the mechanical enforcement layer for the "minimum viable code" posture in `plan-marshall:dev-general-code-quality` `standards/code-organization.md` § `#minimum-viable-code`. The seven anti-patterns enumerated there are the source-of-truth definitions; these five rules detect the deterministically-recognisable subset in marketplace bundle scripts. The cognitive judgement calls are handled by `default:finalize-step-simplify`. Emitter: `_analyze_simplicity.py` (aggregated via `_doctor_analysis.py::scan_simplicity`, invoked from `doctor-marketplace.py::cmd_analyze`).

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `SIMPLICITY_UNUSED_PARAMETER` | content | `_analyze_simplicity.py` | `plan-marshall:dev-general-code-quality` `standards/code-organization.md` § `#minimum-viable-code` — "Unused parameters preserved for future use". A parameter discarded via `del <param>` or tagged `# unused` is surplus structure; remove it and add it back against a real caller. |
| `SIMPLICITY_BACKWARD_COMPAT_REEXPORT` | content | `_analyze_simplicity.py` | `plan-marshall:dev-general-code-quality` `standards/code-organization.md` § `#minimum-viable-code` — "Thin/backward-compat re-exports with <= 1 live caller". Inline the import at its single call site and delete the shim. |
| `SIMPLICITY_DEFENSIVE_CATCHALL` | content | `_analyze_simplicity.py` | `plan-marshall:dev-general-code-quality` `standards/code-organization.md` § `#minimum-viable-code` — "Defensive try/except around already-handled or should-fail-loudly failures". Let the exception propagate. |
| `SIMPLICITY_THIN_WRAPPER` | content | `_analyze_simplicity.py` | `plan-marshall:dev-general-code-quality` `standards/code-organization.md` § `#minimum-viable-code` and § Over-Abstraction — a function whose body is a single argument-forwarding `return`; inline it at the call site. |
| `SIMPLICITY_SIGNATURE_DOCSTRING` | content | `_analyze_simplicity.py` | `plan-marshall:dev-general-code-quality` `standards/code-organization.md` § `#minimum-viable-code` — "Signature-restating docstrings/comments". The one safe auto-apply fix (delete the restating docstring); fix handler `_cmd_apply.py::apply_signature_docstring_fix`. |

### Lesson-2026-05-05-18-001 rule pack

Seven forward-looking lint rules added by the lesson-2026-05-05-18-001 remediation plan.

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `shell-active-tokens` | safety | `_analyze_shell_active_tokens.py` | Lesson `2026-05-05-18-001` — shell-active constructs (backticks, brace expansion, glob wildcards, dollar tokens) inside skill standards prose cause unintended shell expansion when copied to a terminal. |
| `metadata-field-undefined` | structural | `_analyze_metadata_field_validity.py` | Lesson `2026-05-05-18-001` — metadata field names referenced in prose without a corresponding `set-metadata --key` writer somewhere in the marketplace. |
| `resolution-branch-side-effect-undocumented` | content | `_analyze_resolution_branch_markers.py` | Lesson `2026-05-05-18-001` — every named `## Resolution` branch must document at least one observable side effect (log / metadata / status / artifact write). |
| `executor-path-in-production` | structural | `_analyze_executor_path_in_production.py` | Lesson `2026-05-05-18-001` — production Python scripts must not embed `.plan/execute-script.py`; the literal path creates a runtime coupling to `.plan/` that breaks when called from an unexpected location. |
| `plan-path-in-scripts` | structural | `_analyze_plan_path_in_scripts.py` | Ghost-plan-dir bug — two CI-completion scripts (`ci_complete_precondition.py` and `manage-ci-artifacts.py`) shipped hand-rolled `_resolve_plan_base_dir()` helpers that returned `cwd/.plan` instead of the canonical `cwd/.plan/local`, producing a ghost `.plan/plans/{plan_id}/` tree on every invocation. Production scripts must use `get_plan_dir(plan_id)` from `tools-file-ops:file_ops`; code-literal `.plan/plans/` occurrences in marketplace `scripts/*.py` are runtime hazards. Docstring-only matches are out of scope. |
| `orphan-argparse-flag` | structural | `_analyze_orphan_argparse_flags.py` | Lesson `2026-05-05-18-001` — argparse flags declared but never read in their handler accumulate when config keys are removed without also removing the declaration. |
| `cmd-root-anchoring-missing` | structural | `_analyze_cmd_root_anchoring.py` | Lesson `2026-05-05-18-001` — every `cmd_*` dispatcher must call `find_marketplace_root(...)` and declare `--marketplace-root` to avoid hidden cwd coupling. |
| `file-bloat-ack` (extension of `file-bloat` / `subdoc-bloat`) | content | `_doctor_analysis.py::_has_file_bloat_ack` | Lesson `2026-05-05-18-001` — allow explicitly acknowledged bloated files to suppress the `file-bloat` / `subdoc-bloat` findings via `quality.file-bloat: ack-<rationale>` frontmatter. |

### Shell-substitution invariant

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `shell-substitution-in-skills` | safety | `_analyze_shell_substitution_in_skills.py` | Plan `remove-lesson-ref-noise` (2026-05-15) — `$(` command substitution in plan-marshall skill markdown violates the dev-agent-behavior-rules "Bash: no shell constructs" hard rule. Structural exemptions: inline-code spans and fenced blocks with `markdown`/`text` info-string. |
| `WORKFLOW_DOC_TOON_ERROR_FIELD` | safety | `_analyze_workflow_doc_toon_error_field.py` | Lesson `2026-06-10-13-001` and the canonical error-envelope contract at `plan-marshall/skills/plan-marshall/workflow/planning.md` — fenced ` ```toon ` workflow/agent error blocks must use `error:` as the category discriminator (with the message carried by `display_detail:`), not the non-canonical `error_type:`. The orchestrator and the execution-context dispatcher branch on the field name they read out of the TOON block, so a drifted key silently desynchronises the read-side match. Detection scope: fenced ` ```toon ` blocks only; the key must be at the start of a TOON line. Inline `{status: error, error_type: ...}` brace shorthands, prose references outside any fence, and non-`toon` fences are out of scope by design. Quality-gate-active (zero residual findings after the normalization sweep). |

### Bash chain-shape invariant

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `bash-chain-shapes-in-skills` | safety | `_analyze_bash_chain_shapes_in_skills.py` | Plan `bash-compound-command-with-tmp-redirect-triggered` — compound Bash command sequences (`&&`, `;`, trailing `&`) inside fenced `bash`/`sh` blocks in plan-marshall skill markdown violate the dev-agent-behavior-rules "Bash: one command per call" hard rule. The canonical anti-pattern (`python3 … > /tmp/… 2>&1; grep …`) triggered a 25-minute permission-prompt pause during plan execution. Structural exemptions: comment lines and inline-code spans; only `bash`/`sh`-fenced blocks are scanned. |
| `tmp-redirect-in-skills` | safety | `_analyze_tmp_redirect_in_skills.py` | Plan `bash-compound-command-with-tmp-redirect-triggered` — `>` / `>>` redirects targeting `/tmp/` or `/var/tmp/` inside fenced `bash`/`sh` blocks violate the project policy that all temporary files must live under `.plan/temp/`. The violation is frequently paired with a compound chain (`;`, `&&`), which is the pattern from the source incident. Structural exemptions: comment lines and inline-code spans; only `bash`/`sh`-fenced blocks are scanned. |
| `bash-fence-inline-code-exemption` | structural | `_analyze_bash_fence_inline_code_exemption.py` | Lesson Detection proposal — reintroduction guard flagging any analyzer module that scans inside a bash/sh fence (defines `_BASH_FENCE_INFO_STRINGS`) while also carrying a markdown inline-code exemption (`_INLINE_CODE_RE` / `_inline_code_spans`). Inside a bash fence backticks are command substitution, not markdown inline-code, so the two markers are mutually exclusive in a single analyzer; co-presence silently skips real command-substitution shapes. Matches zero files in the current (post-PR-#474) tree. |

### Script-call drift

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `script-call-drift` | structural | `_analyze_script_call_drift.py` | Plan `fix-generate-executor-ast-subcommands` (2026-05-26) — replaces the deleted runtime SUBCOMMANDS pre-flight validator with a dev-time `--help`-based drift detector. Probes `python3 .plan/execute-script.py {notation} --help` per documented invocation to validate the published argparse interface. Lessons `2026-04-29-23-002`, `2026-05-25-21-001`, `2026-05-26-09-001`. Opt-in via `--rules script_call_drift` — NOT in the unconditional quality-gate set due to subprocess overhead. |

### Lesson-ID prose hygiene

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `no-lesson-id-in-skill-prose` | content | `_analyze_lesson_id_in_skill_prose.py` | Plan `remove-lesson-ref-noise` (2026-05-19) — narrative lesson-ID citations in skill prose add no durable value to the rule/decision content they accompany. Extended to also detect the backtick-prefixed form (`lesson \`YYYY-...\``) where "lesson" is prose context outside the backtick — that form is a narrative citation regardless of the backtick. Structural exemptions: allowlisted skill paths, YAML frontmatter, fenced code blocks, `Source:` provenance lines, and bare inline-code spans (without a prose "lesson" prefix). Suppressible per-line via `<!-- doctor-ignore: lesson-id-prose -->`. |
| `no-historical-prose-in-skills` | content | `_analyze_historical_prose_in_skills.py` | Audit of `worktree-handling.md` and marketplace-wide sweep — skill documents must describe present-tense rules, not historical events. Seven pattern families detected: driving-lesson prefix, back-reference prefix, earlier-proposal narrative, historical-activation descriptions, seed-failure/observation citations, plan/task-authorship annotations, and guard-introduction prose. Allowlisted: `manage-lessons/**`, `phase-6-finalize/workflow/lessons-*.md`, `phase-6-finalize/standards/lessons-*.md`, `plan-retrospective/**`, `plugin-doctor/references/rule-provenance.md`, `plugin-doctor/references/rule-catalog.md`, `plan-doctor/standards/**`. Suppressible per-line via `<!-- doctor-ignore: historical-prose -->`. |
| `phase-5-step-missing-role-field` | structural | `_analyze_role_field.py` | Plan `fix-manifest-name-drift-decision-log` — phase-5-execute step standards files MUST declare a `role:` frontmatter field so the `manage-execution-manifest` composer's structural role-based intersection (Rows 2/3/4/5 of the seven-row decision matrix) can resolve candidate step IDs to their canonical role. A missing `role:` field causes the composer to silently drop the candidate from every role-based intersection, producing the `name_drift=true` failure mode. Path-scoped to `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/*.md`; step files are identified by the frontmatter triple `name: default:…`, `description:`, `order:`. See `plan-marshall:manage-execution-manifest/standards/decision-rules.md` § Role-Field Intersection. |
| `resolver-matrix-coverage` | content | `_analyze_resolver_matrix_coverage.py` | Plan `fix-terminal-title-integration` — N-input skip-on-miss resolvers (function whose body is a sequence of `if {guard}: return ...` tiers followed by a final fallback `return`) with `tier_count >= 3` require a `@pytest.mark.parametrize` matrix covering every `tier x {hit, miss}` cell (`tier_count * 2` cells) so the inter-tier contract cannot drift silently. Surfaces a `tip`-severity finding when the corresponding `test/{bundle}/{skill}/test_{module}.py` declares fewer parametrize cells + distinct test methods than `tier_count * 2`. |

### Skill self-consistency rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `allowed-tools-body-drift` | structural | `_analyze_allowed_tools_drift.py` | Lesson 2026-06-05-10-002 — allowed-tools frontmatter drifts from workflow body. Flags a component whose body invokes a tool absent from its declared, non-empty `allowed-tools`/`tools` list. A consistency check, NOT a schema prohibition — components that omit the declaration entirely are never flagged (the "inherit all tools" default; the retired `unsupported-skill-tools-field` rule stays deleted). Reuses `_analyze_coverage.py::parse_declared_tools` for frontmatter parsing. Suppressible per-line via `<!-- doctor-ignore: allowed-tools-drift -->`. |
| `skill-self-declared-rule-violation` | structural | `_analyze_self_declared_rule_compliance.py` | Lesson 2026-06-05-11-001 (consolidated into 2026-06-05-10-002) — a skill that authors a numbering-discipline rule must obey it in its own body. Flags a `SKILL.md` that declares a flat-numbering / no-sub-numbering rule yet uses sub-numbered (`1a`/`3a`/`5a`-style) step headings in that same file. Self-referential — a file that uses sub-numbering without declaring such a rule is NOT flagged (not a global numbering ban). Scoped narrowly to the numbering-discipline class, the one self-rule class that is regex-checkable. Suppressible per-line via `<!-- doctor-ignore: self-declared-rule -->`. |

### Reference-resolution rules

Five rules added by the `reference-resolution-linting-gaps-declared-vs-dis` plan, catching gaps between declared and on-disk-discoverable marketplace components. Each gap resolves to a dead reference at runtime. Unconditionally active under `analyze`; NOT in `quality-gate`. `notation-bundle-skill-drift` is emitted from `_analyze_notation_staleness.py` alongside the existing `notation-staleness` rule.

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `declared-component-vs-disk` | structural | `_analyze_declared_vs_disk.py` (via `doctor-marketplace.py::cmd_analyze`) | Plan `reference-resolution-linting-gaps-declared-vs-dis` (D1, rule 1) — forward manifest-integrity check: every component declared in a bundle's `.claude-plugin/plugin.json` (`agents`/`commands`/`skills`) must resolve to a file on disk; a declared-but-missing entry is a dead manifest reference the plugin loader fails on. |
| `plugin-json-orphan-component` | structural | `_analyze_plugin_json.py` (via `doctor-marketplace.py::cmd_analyze`) | Plan `reference-resolution-linting-gaps-declared-vs-dis` (D1, rule 4) — reverse manifest-integrity check: an on-disk `user-invocable: true` skill / agent / command not declared in its bundle's `plugin.json` ships but is invisible to the plugin loader. Honours the registration convention (`user-invocable: false` skills are legitimately unregistered and exempt). Advisory `warning` severity. |
| `skill-notation-unresolved` | structural | `_analyze_skill_notation.py` (via `doctor-marketplace.py::cmd_analyze`) | Plan `reference-resolution-linting-gaps-declared-vs-dis` (D1, rule 2) — a `Skill: {bundle}:{skill}` directive whose target skill directory `bundles/{bundle}/skills/{skill}/` does not exist is a dead reference the dispatcher cannot load. |
| `notation-bundle-skill-drift` | structural | `_analyze_notation_staleness.py` (via `_doctor_analysis.py`) | Plan `reference-resolution-linting-gaps-declared-vs-dis` (D1, rule 3) — extends `notation-staleness` (which validates only the script segment) to validate the bundle and skill notation segments against the on-disk layout. Evaluated only for executor-anchored (`execute-script.py {notation}`) notations to remove the bundle/skill ambiguity that bare tokens carry. |
| `recipe-missing-implements` | structural | `_analyze_frontmatter.py` (via `doctor-marketplace.py::cmd_analyze`) | Plan `reference-resolution-linting-gaps-declared-vs-dis` (D1, rule 5) — recipe-* skills are recipe-extension-point implementors discovered via the `implements:` frontmatter field; a missing / divergent value makes the recipe undiscoverable. Required value `implements: plan-marshall:extension-api/standards/ext-point-recipe`. See `plan-marshall:extension-api/standards/ext-point-recipe.md` § Implementor Frontmatter. Scoped to `marketplace/bundles/*/skills/recipe-*` and `.claude/skills/recipe-*`. |

### Test-convention rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `unique-fixture-basenames` | structural | `_analyze_test_conventions.py` | Test-organisation contract — sibling test fixtures must have unique basenames to avoid pytest fixture shadowing. |
| `subprocess-pythonpath` | structural | `_analyze_test_conventions.py` | Test-infrastructure contract — `subprocess.run` calls in tests must forward `PYTHONPATH` so the spawned scripts can resolve marketplace imports. |
| `identifier-validator-corpus` | structural | `_analyze_test_conventions.py` | Test-infrastructure contract — identifier-validator tests must consume the canonical corpus rather than open-coded fixtures. |

### Fix-only rules (handler registered, emitter pending audit)

The following rule IDs appear in `_doctor_shared.py::FIXABLE_ISSUE_TYPES` because the apply / verify handlers exist, but no `_analyze_*.py` module currently emits the finding. They are kept in the registry for backward compatibility with externally-authored fix payloads (a caller hand-constructs the fix JSON). Each entry awaits either an analyzer emitter (in which case it transitions to one of the sections above) or removal from the registry.

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `array-syntax-tools` | structural | `_cmd_apply.py` / `_cmd_verify.py` only (no analyzer emitter) | Plugin schema contract — `tools:` field must use the array/list syntax rather than the comma-separated string form. Handler retained for backward-compatible fix payloads. |
| `trailing-whitespace` | style | `_cmd_apply.py` / `_cmd_verify.py` only (no analyzer emitter) | Whitespace hygiene contract — trailing whitespace on lines is normalised by the fix handler. Retained for backward-compatible fix payloads. |
| `improper-indentation` | style | handler-only | Whitespace hygiene contract — YAML indentation normalisation. Retained for backward-compatible fix payloads. |
| `missing-blank-line-before-list` | style | handler-only | Markdown formatting contract — list rendering correctness. Retained for backward-compatible fix payloads. |
| `unused-tool-declared` | structural | handler-only (risky) | Plugin architecture contract — declared `tools:` entries with no SKILL.md / agent-body reference. Risky because the analyzer cannot prove semantic non-use. |
| `tool-not-declared` | structural | handler-only (risky) | Plugin architecture contract — tool usage in body without a frontmatter `tools:` entry. Risky because frontmatter inference can drift. |
| `backup-file-pattern` | safety | handler-only (risky) | Repository-hygiene contract — `*.bak` / `*.orig` / `*~` are uncommitted backup artefacts. The `backup-pattern` analyzer rule emits findings; the fix handler is keyed under the longer `backup-file-pattern` form for handler dispatch. |
| `ci-rule-self-update` | safety | handler-only (risky) | CI-rule self-update contract — risky fix retained for backward-compatible fix payloads. |

### Resolver-gap rule

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `skill-resolver-gap` (already listed under Skill rules) | content | `_doctor_analysis.py` (also surfaced under sub-docs via `subdoc-skill-resolver-gap` channel inside `_doctor_analysis.py`) | Lesson `2026-04-27-18-005`. Listed once under Skill rules. |

## Provenance contract for new rules

Adding a new rule to plugin-doctor requires three artifacts created in lockstep:

1. **Emitter** — a new branch in an `_analyze_*.py` module (or a new module under the same convention) that constructs the finding with `'type'` or `'rule_id'` set to the new rule ID.
2. **Catalog entry** — a row in `references/rule-catalog.md` under the appropriate section, plus a row in this `rule-provenance.md` table with the class and source citation.
3. **Source citation** — a lesson ID, a referenced architectural standard, or a `decision.log` entry that explains why the rule exists. Rules without a citation are inadmissible — they get removed in the next provenance audit (see the `unsupported-skill-tools-field` precedent removed in plan `harden-phase3-outline-plugin-doctor-audit`).

Fix-handler rules additionally require:

4. **Fix entry in `_cmd_apply.py::FIX_HANDLERS`** — registers the apply handler keyed by the rule ID.
5. **Verify entry in `_cmd_verify.py::cmd_verify`** — dispatches to the type-specific verifier (or routes to `verify_generic` for content-only rules).
6. **Catalog entry in `references/fix-catalog.md`** — documents the safe/risky classification and the fix payload shape.
7. **Membership in `_doctor_shared.py::FIXABLE_ISSUE_TYPES`** (plus `SAFE_FIX_TYPES` or `RISKY_FIX_TYPES`) — the static registry that gates whether the rule can be auto-fixed via `cmd_apply`.

The seven-artifact contract is enforced by the regression test introduced in plan `harden-phase3-outline-plugin-doctor-audit` (TASK-006): every rule ID emitted by an `_analyze_*.py` module must have an entry in this `rule-provenance.md` table, every fixable rule must appear in `FIXABLE_ISSUE_TYPES`, and every entry in `FIX_HANDLERS` must have a corresponding row in `fix-catalog.md`.

## Audit history

| Date | Plan | Rules removed | Rationale |
|------|------|---------------|-----------|
| 2026-05-16 | `harden-phase3-outline-plugin-doctor-audit` | `unsupported-skill-tools-field` | Fabricated rule — no lesson, no architectural source, no ecosystem support. Skills MAY declare `allowed-tools` per the Claude Code skills schema. |
| 2026-05-17 | post-merge citation pass | (none retired) | Followed-up the Class A claim audit: WebFetched https://code.claude.com/docs/en/skills and https://code.claude.com/docs/en/sub-agents, confirmed 3 rules as truly Anthropic-schema-derived (`missing-frontmatter`, `invalid-yaml`, `misspelled-user-invocable`), and reclassified 8 rules from "Plugin schema contract" wording to "Project convention" with internal architectural-doc citations. Also struck the orphan `skill-unused-tools-declared` reference from `rule-catalog.md` and `SKILL.md` (no emitter exists). |
