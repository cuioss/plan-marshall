# Plugin-Doctor Rule Provenance

Every rule emitted by `plugin-doctor` must have a documented provenance — the lesson, decision, or design contract that introduced it. This catalog is the source-of-truth audit trail; if a rule appears in `_doctor_shared.py` registries or in any `_analyze_*.py` / `_doctor_analysis.py` emitter without a row here, that rule is unsupported and must be removed.

## Classification

| Class | Meaning |
|-------|---------|
| **structural** | Validates file / component / argparse / metadata structure. Failure means the artifact does not match its declared schema. |
| **content** | Validates the textual content of a marketplace artifact — bloat thresholds, prose drift, hard-coded paths, checklist patterns. |
| **style** | Naming conventions, ordering, formatting conventions that do not affect runtime behaviour but degrade authoring experience when drifted. |
| **safety** | Enforces a `dev-general-practices` hard rule. Violations are runtime hazards (security prompts, shell-construct rejection, prefix-binding silent failures). |

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
| `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` | structural | `_analyze_argument_naming.py` | Lesson `2026-04-29-23-002` — the Canonical Forms table at `plan-marshall:dev-general-practices/standards/argument-naming.md` is the documented contract; if it drifts from argparse, every author who consults it writes broken prose. |

### manage-* invocation rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `manage-findings-invocation-invalid` | structural | `_analyze_manage_findings_invocation.py` (via `_doctor_analysis.py`) | Lesson `2026-04-29-23-002` recurrence — three canonical invalid spellings of `manage-findings` notation surfaced as LLM hallucinations. |
| `manage-invocation-invalid` | structural | `_analyze_manage_invocation.py` | Lesson `2026-04-29-23-002` generalization — same drift class across seven heaviest-referenced `manage-*` / `workflow-integration-*` script families. |
| `missing-canonical-block` | style | `_analyze_manage_invocation.py` | D1 of the argparse-surface-drift remediation plan — every in-scope SKILL.md must publish a `## Canonical invocations` section as the in-skill source-of-truth mirror of the `manage-invocation-invalid` rule. |

### Phase-6 finalize step termination

Three rules guarding `mark-step-done` invocations. Source: phase-6 finalize-orchestration contract (silent-failure surface).

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `MARK_STEP_DONE_BAD_NOTATION` | structural | `_analyze_markdown.py::check_mark_step_done_violations` (via `_doctor_analysis.py`) | Phase-6 finalize-orchestration contract — `manage-status:manage-status` (hyphenated) does not resolve; canonical form is `manage-status:manage_status`. |
| `MARK_STEP_DONE_MISSING_PHASE` | structural | same | Phase-6 finalize-orchestration contract — without `--phase`, the step termination is routed to the wrong phase record. |
| `MARK_STEP_DONE_MISSING_OUTCOME` | structural | same | Phase-6 finalize-orchestration contract — without `--outcome`, the step cannot be terminated unambiguously. |

### Script-safety rules

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `argparse_safety` | safety | `_doctor_analysis.py::scan_argparse_safety` | Lesson `2026-04-17-012` — argparse prefix-matching silently binds retired flags when `allow_abbrev=True`. |

### Lesson-2026-05-05-18-001 rule pack

Seven forward-looking lint rules added by the lesson-2026-05-05-18-001 remediation plan.

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `shell-active-tokens` | safety | `_analyze_shell_active_tokens.py` | Lesson `2026-05-05-18-001` — shell-active constructs (backticks, brace expansion, glob wildcards, dollar tokens) inside skill standards prose cause unintended shell expansion when copied to a terminal. |
| `metadata-field-undefined` | structural | `_analyze_metadata_field_validity.py` | Lesson `2026-05-05-18-001` — metadata field names referenced in prose without a corresponding `set-metadata --key` writer somewhere in the marketplace. |
| `resolution-branch-side-effect-undocumented` | content | `_analyze_resolution_branch_markers.py` | Lesson `2026-05-05-18-001` — every named `## Resolution` branch must document at least one observable side effect (log / metadata / status / artifact write). |
| `executor-path-in-production` | structural | `_analyze_executor_path_in_production.py` | Lesson `2026-05-05-18-001` — production Python scripts must not embed `.plan/execute-script.py`; the literal path creates a runtime coupling to `.plan/` that breaks when called from an unexpected location. |
| `orphan-argparse-flag` | structural | `_analyze_orphan_argparse_flags.py` | Lesson `2026-05-05-18-001` — argparse flags declared but never read in their handler accumulate when config keys are removed without also removing the declaration. |
| `cmd-root-anchoring-missing` | structural | `_analyze_cmd_root_anchoring.py` | Lesson `2026-05-05-18-001` — every `cmd_*` dispatcher must call `find_marketplace_root(...)` and declare `--marketplace-root` to avoid hidden cwd coupling. |
| `file-bloat-ack` (extension of `file-bloat` / `subdoc-bloat`) | content | `_doctor_analysis.py::_has_file_bloat_ack` | Lesson `2026-05-05-18-001` — allow explicitly acknowledged bloated files to suppress the `file-bloat` / `subdoc-bloat` findings via `quality.file-bloat: ack-<rationale>` frontmatter. |

### Shell-substitution invariant

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `shell-substitution-in-skills` | safety | `_analyze_shell_substitution_in_skills.py` | Lesson `2026-05-15-13-001` — `$(` command substitution in plan-marshall skill markdown violates the dev-general-practices "Bash: no shell constructs" hard rule. Structural exemptions: inline-code spans and fenced blocks with `markdown`/`text` info-string. |

### Lesson-ID prose hygiene

| Rule ID | Class | Emitter | Source |
|---------|-------|---------|--------|
| `no-lesson-id-in-skill-prose` | content | `_analyze_lesson_id_in_skill_prose.py` | Plan `remove-lesson-ref-noise` (2026-05-19) — narrative lesson-ID citations in skill prose add no durable value to the rule/decision content they accompany. Structural exemptions: allowlisted skill paths (`manage-lessons/**`, `phase-6-finalize/workflow/lessons-*.md`, `phase-6-finalize/standards/lessons-*.md`, `plugin-doctor/references/rule-provenance.md`), YAML frontmatter, fenced code blocks, `Source:` provenance lines, and inline-code spans. Suppressible per-line via `<!-- doctor-ignore: lesson-id-prose -->`. |

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
