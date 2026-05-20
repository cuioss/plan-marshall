# Rule Catalog

Rules that plugin-doctor validates in other components. See the Enforcement block in SKILL.md for this skill's own constraints.

> **Related**: For architectural principles with rationale and examples, see `plugin-architecture:architecture-rules`. This catalog lists validation rules only.
>
> **Provenance**: For the source-of-truth classification and lesson / contract citation behind every rule below, see [rule-provenance.md](rule-provenance.md). Adding a rule without a corresponding provenance entry is inadmissible — the rule will be removed by the next provenance audit.

## Agent Rules

**agent-task-tool-prohibited**: Agents cannot declare the Task tool (unavailable at runtime).

**agent-maven-restricted**: Only the maven-builder agent may execute Maven commands.

**agent-lessons-via-skill**: Agents record lessons via manage-lessons skill, not self-invoke commands.

**agent-skill-tool-visibility**: Agents declaring explicit tools must include Skill, otherwise invisible to Task dispatcher.

**agent-glob-resolver-workaround** (severity: error): Flags `agents/*.md` whose YAML frontmatter `tools:` field includes `Glob` unless the same frontmatter declares `forwards_tool_capabilities: true` as a typed boolean flag. Scope: `marketplace/bundles/*/agents/*.md`.

- **Rationale**: Agents granted `Glob` access overwhelmingly use it to hand-roll discovery that should be delegated to a canonical resolver script. This is the same resolver-gap anti-pattern as `skill-resolver-gap`, but at the agent permission layer: once `Glob` is in the agent's tool list, prose-driven discovery becomes the path of least resistance and resolver scripts go unused.
- **Discovery approach**: Parse YAML frontmatter, check the `tools:` array for the `Glob` token (handles both inline `tools: Read, Write, Glob` and block-list forms). If present, check the same frontmatter for `forwards_tool_capabilities: true` (canonical lowercase YAML boolean, top-level key). Absence emits an `agent-glob-resolver-workaround` finding pointing at the agent file.
- **Fix**: Remove `Glob` from the agent's `tools:` field and replace any Glob-driven discovery with a `python3 .plan/execute-script.py` call to a canonical resolver. If the agent legitimately forwards tool capabilities to dispatched subagents (the recognized exemption case — e.g., dispatchers that need to pass `Glob` access through), add `forwards_tool_capabilities: true` to the agent's frontmatter to declare intent structurally.
- **Exemptions**: Add `forwards_tool_capabilities: true` as a top-level YAML key in the agent's frontmatter. The value MUST be the unquoted lowercase YAML boolean `true`; quoted forms (`"true"`, `'true'`), `True`, and `yes` are NOT accepted. The legacy body-comment marker `# resolver-glob-exempt: <justification>` is no longer scoped as an exemption — agents still carrying that marker without the frontmatter flag will be flagged.

## Workflow Rules

**workflow-explicit-script-calls**: All script/tool invocations in workflow documentation have explicit bash code blocks with the full `python3 .plan/execute-script.py` command.

**workflow-hardcoded-script-path**: Use executor notation (`bundle:skill:script`) instead of hardcoded file paths.

**workflow-prose-parameter-consistency**: Prose instructions adjacent to `execute-script.py` bash blocks must reference parameter values consistent with the actual script API.

**prose-verb-chain-consistency** (severity: error): Flags prose sentences in workflow documentation that reference a `{notation} {verb-chain}` combination where the verb chain is not a registered subcommand path of the referenced script. Scope: `SKILL.md` plus every `standards/*.md` inside each script-bearing skill directory under `marketplace/bundles/*/skills/`.

- **Rationale**: Prose drift lets workflow instructions reference verb chains the script never exposed. Concrete drift incident driving this rule: `phase-2-refine/SKILL.md` prose referenced `manage-plan-documents request clarify` when the script only registered `request read` and `request mark-clarified` — a human-reader would copy the command and hit an argparse error at runtime, with no structural check catching the mismatch.
- **Discovery approach**: AST-based, mirroring `argparse_safety`. The rule walks each script's argparse tree (`add_subparsers` → `add_parser` calls) recursively to enumerate the set of registered verb chains, then greps prose for `{notation} {tokens...}` occurrences and reports any token sequence that is not a valid prefix path in the registered tree. No subprocess execution, no imports of the target script — pure static analysis.
- **Fix**: Update the prose to use a registered verb chain. If the intended verb chain does not yet exist in the script, either add it to the argparse tree or choose the nearest registered command.
- **Exemptions**: Place `<!-- doctor-ignore: verb-check -->` on the line immediately preceding a bash fence to suppress verb-chain validation for that specific block (use sparingly — only when prose deliberately documents a command the script does not expose, e.g., illustrative or aspirational examples).

## Command Rules

**command-self-contained-notation**: Components that execute scripts have the exact notation (`bundle:skill:script`) explicitly defined within themselves.

Four detection modes:

| Mode | Catches |
|------|---------|
| A: Delegation | "Execute command from section Nb" - parent-passed |
| B: Notation | `execute-script.py artifact_store` - missing bundle:skill |
| C: Missing Section | "Log the assessment" without ## Logging Command section |
| D: Parameters | `--plan-id` when should be positional (via --help) |

**command-thin-wrapper**: Commands delegate all logic to skills; they are thin orchestrators.

**command-progressive-disclosure**: Load skills on-demand, not all at once.

**command-completion-checks**: Mandatory post-fix verification after applying changes.

**command-no-embedded-standards**: No standards blocks in commands; standards belong in skills.

## Skill Rules

**skill-enforcement-block-required**: Script-bearing skills need an `## Enforcement` block.

**skill-naming-noun-suffix**: Skill directory names must not end with a reserved noun suffix (`-executor`/`-executors`, `-manager`/`-managers`, `-runner`/`-runners`, `-handler`/`-handlers`, `-orchestrator`/`-orchestrators`). These suffixes are reserved for spawnable marketplace agents. Skills must use verb-first names (e.g. `execute-task` instead of `task-executor`). See `pm-plugin-development:plugin-architecture` `references/skill-design.md` "Skill Naming Convention" for the full rationale. Detection runs during skill structure analysis.

**skill-resolver-gap** (severity: warning): Flags skill `SKILL.md` and `standards/*.md` prose containing LLM-Glob discovery patterns (`Use Glob:`, `Glob pattern:`, `Discover ... using Glob`, `find ... using Glob patterns`) without an adjacent `python3 .plan/execute-script.py` invocation within the next 5 lines. Scope: `marketplace/bundles/*/skills/*/SKILL.md` and `marketplace/bundles/*/skills/*/standards/*.md`.

- **Rationale**: Skills that direct an LLM to perform discovery via `Glob`/`Grep` when a canonical resolver script already exists for that domain re-introduce the resolver-gap anti-pattern: the LLM hand-rolls discovery logic that should live in a deterministic script, and successive runs drift in coverage and ordering. Concrete drift incident: prose like "Use Glob: marketplace/bundles/*/skills/*/SKILL.md" appearing without a follow-up `execute-script.py` call to a resolver — a human-reader copies the suggestion and produces non-deterministic results compared to the resolver's output.
- **Discovery approach**: Line-by-line regex scan over markdown content. For each match of an LLM-Glob trigger phrase, the analyzer inspects the next ≤5 lines for `python3 .plan/execute-script.py`. If absent, a `skill-resolver-gap` finding is emitted with the line of the prose match. Pure static analysis — no script execution, no imports.
- **Fix**: Replace the LLM-Glob prose with a `python3 .plan/execute-script.py {bundle}:{skill}:{script}` invocation that delegates discovery to a canonical resolver. If no resolver exists yet, add one before relying on Glob from prose.
- **Exemptions**: Place `<!-- doctor-ignore: resolver-gap -->` on the line immediately preceding the prose block to suppress the finding for that occurrence (use sparingly — only when prose deliberately documents an LLM-driven discovery for which no resolver is appropriate, e.g., debugging instructions or single-shot diagnostics).

## Script Rules

**argparse_safety** (severity: error): Flags every `argparse.ArgumentParser(...)` constructor call and every `subparsers.add_parser(...)` call in marketplace Python scripts that does not pass `allow_abbrev=False`. Scope: files under `marketplace/bundles/*/skills/*/scripts/` and `marketplace/targets/**/*.py`. Tests are exempt (files under `test/`/`tests/` directories or named `test_*.py` / `*_test.py`).

- **Rationale**: Without `allow_abbrev=False`, argparse matches unknown long options by unique prefix. When a flag is renamed or retired, old callers keep working silently via prefix binding — the contract rot is invisible until something behaves wrong under a rename.
- **Fix**: Add `allow_abbrev=False` to the constructor or `add_parser(...)` call. The rule is a lightweight AST walk (no parser execution); it flags the exact line and call name (`ArgumentParser` or `add_parser`).
- **Exemptions**: Test files may intentionally exercise argparse default behavior and are excluded from the scan.

## Argument Naming Rules

The `ARGUMENT_NAMING_*` rule cluster cross-checks marketplace prose against the actual argparse declarations of the scripts that prose references. The cluster also cross-checks the Canonical Forms table in `marketplace/bundles/plan-marshall/skills/dev-general-practices/standards/argument-naming.md` against the same argparse declarations. All four rules emit findings with `severity: error` and `fixable: false`, mirroring the `DISPLAY_DETAIL_*` finding shape used elsewhere in plugin-doctor.

**Activation**: This cluster is unconditionally active. See lesson `2026-04-29-23-002` for the rationale (three recurrences of stale-flag drift in skill workflows within ~3 days drove the move from a gated transitional period to default-on enforcement). Tests exercise the cluster directly against synthetic fixtures.

**Scope**: every `python3 .plan/execute-script.py {notation} ...` token across SKILL.md, agents/*.md, commands/*.md, skills/*/standards/*.md, skills/*/references/*.md, skills/*/recipes/*.md within `marketplace/bundles/*/`. The Canonical Forms cross-check additionally reads the table at `marketplace/bundles/plan-marshall/skills/dev-general-practices/standards/argument-naming.md`.

**Discovery approach**: Pure static analysis — line-by-line regex extraction of executor invocations, plus AST walks of the referenced scripts to enumerate argparse subparsers and `add_argument` flag declarations. Mirrors the existing `argparse_safety` and `prose-verb-chain-consistency` patterns. No subprocess execution, no module imports.

**ARGUMENT_NAMING_NOTATION_INVALID** (severity: error): Flags `python3 .plan/execute-script.py {notation}` tokens whose 3-part `{bundle}:{skill}:{script}` notation is not present in the executor's embedded `SCRIPTS` dict. The finding `details.reason` distinguishes three failure modes: `snake_case_not_registered` (the notation contains underscores where the registry expects kebab-case), `third_segment_repeats_second` (the script segment exactly repeats the skill segment, e.g. `manage-providers:manage-providers`), and `not_registered` (the notation does not appear in the registry for any other reason). The `details.notation` field carries the offending notation verbatim.

- **Rationale**: A mistyped notation routes through `.plan/execute-script.py` to a missing entry; the executor errors out at the caller's site, but no static check has caught the drift earlier. The cluster moves the failure forward to plugin-doctor time so reviewers see the issue before merge.
- **Fix**: Update the prose to use a registered notation. Run `/marshall-steward` after bundle changes to regenerate the executor with updated mappings.
- **Exemptions**: None — every executor invocation in marketplace prose is expected to resolve.

**ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN** (severity: error): Flags `python3 .plan/execute-script.py {notation} {sub}` tokens where `{sub}` is not a registered subcommand on the resolved script. The cluster AST-walks the referenced script's argparse tree (`add_subparsers` → `add_parser('name', ...)`) and reports any `{sub}` that is not in the resulting set. The `details.known_subcommands` field lists the registered subcommands, and `details.subcommand` carries the offending token.

- **Rationale**: Prose drift lets workflow instructions reference subcommands the script never exposed (e.g., the historical `manage-references list` and `manage_status get-plan-dir` patterns). A reader who copies the command hits an argparse error at runtime; the cluster catches the drift statically.
- **Fix**: Update the prose to use a registered subcommand, or add the missing subcommand to the script's argparse tree.
- **Exemptions**: Scripts that declare no subparsers are skipped — any token following the notation is a positional argument, not a subcommand. Scripts whose argparse declarations cannot be parsed (syntax error, missing file) are skipped silently; the notation rule reports the missing script when applicable.

**ARGUMENT_NAMING_FLAG_UNKNOWN** (severity: error): Flags `--{flag}` tokens following a notation+sub pair when `{flag}` is not declared via `add_argument(...)` on the matching subparser (or on the root parser when no subcommand is present). The `details.known_flags` field lists the declared long flags, and `details.flag` carries the offending name.

- **Rationale**: Renaming or retiring a flag while leaving prose unchanged silently breaks instructions. Concrete drift incidents: `--content-stdin`, `--field`, `--limit`, and `--json` references in prose where the script declared none of them. The cluster moves these failures from runtime to review time.
- **Fix**: Update the prose to use a declared flag, or add the missing flag to the script's `add_argument` declarations.
- **Exemptions**: Short flags (`-f`) are not subject to canonical-forms convention and are excluded from the scan. Flags whose script has no resolvable AST entry (missing file, parse error) are skipped silently — the notation rule reports the missing script.

**ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT** (severity: error): Cross-checks every row of the Canonical Forms table at `marketplace/bundles/plan-marshall/skills/dev-general-practices/standards/argument-naming.md` against the argparse declarations of the script the row prescribes. The cluster parses each row's `{script} {sub} --{flag1} {value1} --{flag2} ...` shape, resolves the `{script}` shorthand to a registered notation (matching on either the third segment of the notation or the second when the script shares its skill name), and confirms that `{sub}` is a declared subcommand and every `--{flag}` is declared on that subparser. Failure modes carried in `details.reason`: `shorthand_unresolved`, `subcommand_drift`, `flag_drift`.

- **Rationale**: The Canonical Forms table is the documented contract for argument naming across `manage-*` scripts. If the table prescribes a spelling the argparse declarations no longer honor, every author who consults the table for guidance writes broken prose. The cross-check guarantees the table stays in sync with the implementations it governs.
- **Fix**: Update either the Canonical Forms row or the argparse declaration so the two agree. When the table is correct and the script lags, rename the argparse flag; when the script is correct and the table lags, update the row.
- **Exemptions**: None within the table's scope. Rows whose `{script}` shorthand resolves to multiple registered notations are reported with `reason: shorthand_unresolved` so the table can be tightened to use the full bundle:skill:script form when ambiguity arises.

**manage-findings-invocation-invalid** (severity: error): Catches three canonical invalid spellings of the `plan-marshall:manage-findings:manage-findings` notation and its argparse tree that have surfaced as LLM hallucinations at runtime: (1) **script-position underscore** — `plan-marshall:manage-findings:manage_findings` (snake_case where the executor registry uses kebab-case); (2) **invalid top-level subcommand** — any token other than the registered `add, query, get, resolve, promote, qgate, assessment`; the historically recurring invented form is `list-qgate`; (3) **invalid `qgate` sub-verb** — any sub-verb other than the registered `add, query, resolve, clear`; the historically recurring invented form is `qgate list`. The rule also catches invalid `assessment` sub-verbs as defence in depth. Findings carry `details.canonical_hint` with the closest correct spelling.

- **Discovery approach**: Pure static analysis — line-anchored regex extraction of `plan-marshall:manage-findings:*` notation tokens from skill markdown bodies (`SKILL.md`, `standards/*.md`, `references/*.md`, `workflow/*.md`, `recipes/*.md`). The registered argparse tree (`add, query, get, resolve, promote, qgate, assessment` top-level; `add, query, resolve, clear` under `qgate`; `add, query, get, clear` under `assessment`) is baked into the analyzer as the source-of-truth constant; the rule does not import `manage-findings.py` or subprocess-execute the script. Mirrors `_analyze_argument_naming.py` and `_analyze_verb_chains.py` patterns. No `did-you-mean` runtime changes to `manage-findings.py`.
- **Fix**: Update the prose to use the canonical-form hint emitted in the finding payload. For `list-qgate`, use `qgate query --plan-id {plan_id} --phase {phase}`. For `qgate list`, use `qgate query --plan-id {plan_id} --phase {phase}`. For snake_case script position, replace `manage_findings` with `manage-findings` in the third notation segment.
- **Rationale**: Three invalid `manage-findings` invocation shapes surfaced as LLM hallucinations at runtime, producing silent argparse rejections that the calling workflow swallowed. Grepping `marketplace/bundles/` for these shapes returns zero matches at source time — the failure mode is recurrence-prone LLM drift, not source drift. Catching the shapes at edit time via plugin-doctor moves the structural guard from runtime to review time, in the same spirit as the `ARGUMENT_NAMING_*` cluster.
- **Exemptions**: None — every `plan-marshall:manage-findings:*` invocation in skill markdown is expected to resolve to a registered notation, subcommand, and sub-verb. The rule is gated on the `manage-findings-invocation-invalid` opt-in token in `active_rules` (mirroring the `verb_chain` opt-in semantics), so it only runs when the caller explicitly requests it.

**manage-invocation-invalid** (severity: error): Generalization of the `manage-findings-invocation-invalid` rule across the seven in-scope script families — `plan-marshall:manage-status:manage_status`, `plan-marshall:manage-tasks:manage-tasks`, `plan-marshall:manage-logging:manage-logging`, `plan-marshall:manage-references:manage-references`, `plan-marshall:manage-config:manage-config`, `plan-marshall:workflow-integration-git:git_workflow`, and `plan-marshall:workflow-integration-github:github_ops`. For each invocation found in skill markdown, the analyzer extracts the `(subcommand, sub_verb, flags)` tuple and validates it against the script's canonical argparse tree built at scan time. Four failure modes are reported independently, each with `details.canonical_hint` carrying the closest correct form: (1) unknown top-level subcommand (`details.reason: subcommand_unknown`); (2) unknown sub-verb under a subcommand that declares its own subparser (`details.reason: sub_verb_unknown`); (3) unknown long flag `--{flag}` under the resolved leaf parser (`details.reason: flag_unknown`); (4) missing required flag declared by the resolved leaf parser (`details.reason: required_flag_missing`).

- **Discovery approach**: Pure static analysis — `ast.parse` walk of each in-scope script (whitelisted in `IN_SCOPE_SCRIPTS`) builds a canonical tree `{subcommand: {sub_verb_or_none: {flags, required_flags}}}`. The markdown scan is line-anchored regex extraction of `python3 .plan/execute-script.py {bundle}:{skill}:{script}` invocations from `SKILL.md`, `standards/*.md`, `references/*.md`, `workflow/*.md`, and `recipes/*.md`. Each occurrence is tokenized into positional + flag args and cross-checked against the canonical tree. No subprocess execution, no import of the target scripts. Mirrors the `_analyze_argument_naming.py` and `_analyze_manage_findings_invocation.py` precedents. The implementation lives in `_analyze_manage_invocation.py` (analyzer module) — see the canonical-block convention published in each in-scope SKILL.md's `## Canonical invocations` section for the authoritative spelling reference.
- **Fix**: Update the markdown invocation to match the script's canonical argparse surface. The finding's `details.canonical_hint` names the closest correct subcommand / sub-verb / flag spelling; the corresponding `## Canonical invocations` section in the script's owning SKILL.md is the full reference.
- **Rationale**: Argparse-surface drift in LLM-authored prose has surfaced as a recurring failure mode (lesson `2026-04-29-23-002` plus the recurrence chain that triggered this remediation plan). The `manage-findings-invocation-invalid` rule covers one script; this rule generalizes the same structural guard across the seven heaviest-referenced `manage-*` and `workflow-integration-*` families. Catching token-tree mismatches at edit time moves a class of runtime argparse rejections to review time.
- **Exemptions**: Notations outside `IN_SCOPE_SCRIPTS` are skipped silently — the rule does not expand its scope automatically when new scripts land. Adding a family requires a deliberate edit to `IN_SCOPE_SCRIPTS` in `_analyze_manage_invocation.py`. Scripts whose AST cannot be parsed (syntax error, missing file) are dropped from the index silently; the notation-validity rule (`ARGUMENT_NAMING_*` cluster) reports the missing-script case independently.

**missing-canonical-block** (severity: warning): Emitted when a SKILL.md that owns an in-scope `manage-*` / `workflow-integration-*` script (from the enumerated `IN_SCOPE_SCRIPTS` list) lacks a `## Canonical invocations` section. The section is the documented source-of-truth contract published by D1 of the argparse-surface-drift remediation plan: it carries one `### {subcommand}` heading per registered top-level subcommand with a fenced bash block showing the canonical invocation shape (positional sub-verbs + required flags + optional flags). Authors consult the block when writing prose that invokes the script; missing it leaves them with no in-skill reference. Findings carry `details.notation` (the in-scope notation triple owned by the skill) and `details.canonical_hint` (the relative path to repair).

- **Discovery approach**: Pure regex scan — search each in-scope SKILL.md for `^##\s+Canonical\s+invocations\s*$` (case-insensitive). Absence emits one finding per skill directory (deduplicated when multiple notation triples share the same owning skill). The rule is severity `warning` because absence does not break runtime — it merely degrades the editing experience.
- **Fix**: Add a `## Canonical invocations` section to the named SKILL.md, with one `### {subcommand}` subsection per registered top-level subcommand. Each subsection contains a fenced bash block showing the canonical invocation shape. See `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` for the reference layout.
- **Rationale**: The canonical-block convention is the in-skill mirror of the `manage-invocation-invalid` rule above. The rule machine-validates markdown invocations against the argparse AST; the canonical block gives human authors the same view in the spelling they will write. Together they close the drift surface from both ends. Surfacing the missing-block case at warning severity nudges new script-owning skills to adopt the convention without breaking the build.
- **Exemptions**: Skills outside `IN_SCOPE_SCRIPTS` are not checked — the convention is opt-in for now, with a fixed whitelist. Adding a skill to the rule's scope requires a deliberate edit to `IN_SCOPE_SCRIPTS` in `_analyze_manage_invocation.py`.

## Content Rules

**checklist-pattern**: Checkbox patterns (`- [ ]`, `- [x]`) in LLM-consumed files. These are human UI elements with zero value for LLMs. Exception: files in `/templates/` directories (rendered by GitHub).

## Phase-6 Finalize Step Termination

Three rules guard against defective `mark-step-done` invocations inside marketplace skill/agent markdown. They fire on any bash code fence that references `mark-step-done` and inspect the single logical invocation (including backslash-continued continuation lines). Each defect code is emitted independently, so a single malformed invocation may produce multiple findings.

**Rationale**: Phase-6 finalize step termination is a silent-failure surface. A mistyped notation resolves to a non-existent script and is swallowed by the executor; a missing `--phase` routes the termination to the wrong phase record; a missing `--outcome` leaves the step in an ambiguous `in_progress` state even though the workflow believes it completed. Static detection in plugin-doctor is the cheapest way to catch these errors before they ship.

**MARK_STEP_DONE_BAD_NOTATION** (severity: error): The invocation line contains the hyphenated notation `manage-status:manage-status` instead of the canonical underscored form `manage-status:manage_status`. The executor uses notation segments as literal keys — the hyphenated form simply does not resolve. Detection is a substring check on every line of the invocation (including continuation lines, since the notation often lives on the command line itself).

Incorrect:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --phase phase-6-finalize --outcome done
```

Correct:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --phase phase-6-finalize --outcome done
```

**MARK_STEP_DONE_MISSING_PHASE** (severity: error): The full `mark-step-done` invocation (single line or backslash-continued multi-line) does not contain `--phase`. Without it, the status manager cannot route the step termination to the correct phase record, and finalize-phase orchestration reads stale status.

Incorrect:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --outcome done
```

Correct:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --phase phase-6-finalize --outcome done
```

**MARK_STEP_DONE_MISSING_OUTCOME** (severity: error): The full invocation does not contain `--outcome`. Without an explicit outcome (e.g. `done`, `skipped`, `deferred`), the step cannot be definitively terminated and the phase status entry remains ambiguous.

Incorrect:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --phase phase-6-finalize
```

Correct:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --phase phase-6-finalize --outcome done
```

Detection lives in `_analyze_markdown.py::check_mark_step_done_violations`; findings are surfaced through the standard markdown reporting channel in `_doctor_analysis.py::extract_issues_from_markdown_analysis` with the defect code as the issue `type`.

## PM-Workflow Rules

**pm-implicit-script-call** (PM-001): Script operations without explicit bash code blocks.

**pm-generic-api-reference** (PM-002): Generic API references instead of specific script notation.

**pm-wrong-plan-parameter** (PM-003): Incorrect plan parameter values in script calls.

**pm-missing-plan-parameter** (PM-004): Missing required plan parameters.

**pm-invalid-contract-path** (PM-005): Invalid contract file path references.

**pm-contract-non-compliance** (PM-006): Contract specification violations.

## Rule Pack: Plugin-doctor lint guards

Seven forward-looking lint rules.

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `shell-active-tokens` | Detect shell-active constructs (backticks in flags, brace expansion, glob wildcards, dollar tokens) in skill standards prose | Four specific token classes; `glob-wildcard` exempt inside fenced blocks and inline code | None — fix the offending prose |
| `metadata-field-undefined` | Flag backtick snake_case tokens near metadata prose that reference field names not written by any `set-metadata --key` invocation | Heuristic proximity (±3 lines); builtin fields always exempt | Add `set-metadata --key <field>` write anywhere in the marketplace |
| `resolution-branch-side-effect-undocumented` | Require `## Resolution` branches in standards to document at least one observable side effect | Allowlist-gated branch names; non-allowlist headings ignored | Add a log/metadata/status/artifact mention to the branch body |
| `executor-path-in-production` | Detect `.plan/execute-script.py` in production Python scripts outside whitelisted categories | Whitelist covers generator, lint analyzers, permission tooling | Add path to whitelist in `_analyze_executor_path_in_production.py` |
| `plan-path-in-scripts` | Detect code-literal `.plan/plans/` occurrences in marketplace Python scripts outside whitelisted categories — the canonical path is `.plan/local/plans/` (resolved via `tools-file-ops:file_ops.get_plan_dir`) | Whitelist covers only the analyzer's own self-referential occurrence; docstring-only hits (inside `"""..."""` / `'''...'''`) are structurally exempt | Add path to whitelist in `_analyze_plan_path_in_scripts.py` with a rationale comment, or route the call site through `get_plan_dir(plan_id)` |
| `file-bloat-ack` | Allow explicitly acknowledged bloated files to suppress the `file-bloat` finding | Ack tag must match `^ack-[a-z0-9_-]+$`; bare `ack-` or generic values do not suppress | Add `quality.file-bloat: ack-<rationale>` to the file's YAML frontmatter |
| `orphan-argparse-flag` | Flag argparse flags declared but never read in their handler | Conservative: `vars(args)`, `**kwargs`, or `getattr` usage suppresses the check | Read the flag in the handler, or remove the declaration |
| `cmd-root-anchoring-missing` | Require `cmd_*` dispatcher functions to call `find_marketplace_root(...)` and declare `--marketplace-root` | Dispatcher-heuristic gated: only fires for scripts with `set_defaults(func=cmd_*)` | Add both the prelude call and the `--marketplace-root` flag to the subparser |

## Rule Pack: Shell-substitution invariant

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `shell-substitution-in-skills` | Forbid `$(` command substitution in plan-marshall skill markdown — violates the dev-general-practices "Bash: no shell constructs" hard rule | Two structural exemptions: any occurrence inside a markdown inline-code span (`` `…` ``), or any occurrence inside a fenced block with `markdown`/`text` info-string. Subagents do not execute either context | None — convert to the documented two-call + text-substitution pattern |

### shell-substitution-in-skills

**Rule ID**: `shell-substitution-in-skills`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shell_substitution_in_skills.py`

**Scope**: All `*.md` files under `marketplace/bundles/plan-marshall/skills/`.

**Intent**: Enforce the dev-general-practices "Bash: no shell constructs" hard rule (`dev-general-practices/SKILL.md` § "Bash: One command per call", `tool-usage-patterns.md` § "Bash safety rules") at the skill-documentation layer. A `$(` in a workflow doc gets interpreted by subagents that copy the snippet into a Bash call literally — the host platform's permission UI then either pops a security prompt or rejects the dispatch outright. The rule prevents regressions of the sweep that removed all such patterns.

**Detection logic**: Scans every line of every markdown file under `marketplace/bundles/plan-marshall/skills/`. Each `$(` two-character occurrence is a candidate finding unless it falls into one of the two exempt documentary contexts below.

**Permitted contexts**:
1. **Inline-code span** — A `$(` inside a markdown inline-code span (`` `…` ``). Subagents do not execute inline-code tokens; these are structural token references (e.g., when a standards doc says "the `$(...)` form is forbidden"), not runnable commands.
2. **Verbatim-source fenced block** — A `$(` inside a fenced block whose info-string is `markdown` or `text`. These fences hold verbatim source examples (before/after illustrations) that subagents do not interpret as instructions.

**Rationale**: The two-call + text-substitution pattern (run the script as a bare command, then use a `{placeholder}` slot in the next command's narrative substitution) is the documented safe alternative — see `dev-general-practices/SKILL.md` § "Bash: One command per call" and the request body for lesson `2026-05-15-13-001`. The exemption logic is purely structural (inline-code span or `markdown`/`text` fence) so the rule does not depend on a fragile keyword heuristic in the surrounding prose.

**Recommended fix**: Replace `target=$(python3 .plan/execute-script.py …)` with the bare `python3 .plan/execute-script.py …` invocation followed by a one-sentence narrative ("Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below."). Replace `$var` references in subsequent bash blocks with `{var}` placeholders.

**Suppression mechanism**: None — convert the substitution to the documented safe alternative. If the occurrence is genuinely documentary (a standards doc that names the forbidden pattern), wrap it in an inline-code span (`` `…` ``) so the structural exemption applies.

---

## Rule Pack: Lesson-ID prose hygiene

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `no-lesson-id-in-skill-prose` | Forbid narrative lesson-ID citations in skill prose — strip the ID and trivia, keep the rule content | Five structural exemptions: allowlisted skill paths (manage-lessons/**, phase-6-finalize/workflow/lessons-*.md, phase-6-finalize/standards/lessons-*.md, plugin-doctor/references/rule-provenance.md), YAML frontmatter, fenced code blocks, `Source:` provenance lines, and inline-code spans | Inline marker `<!-- doctor-ignore: lesson-id-prose -->` (same line or immediately preceding line) suppresses the finding on the marked line only |

### no-lesson-id-in-skill-prose

**Rule ID**: `no-lesson-id-in-skill-prose`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_lesson_id_in_skill_prose.py`

**Scope**: All `*.md` files under `marketplace/bundles/*/{skills,agents,commands}/**`.

**Intent**: Strip narrative lesson-ID citations and recurrence trivia from skill prose so the surface documents present-tense rules rather than the historical incidents that motivated them. The rule recognises two lesson-ID format families — `YYYY-MM-DD-NNN` and `YYYY-MM-DD-HH-NNN` — and the prose-prefixed forms `lesson XXX` and `lesson-XXX`.

**Detection logic**: Scans every line of every in-scope markdown file. Each lesson-ID token occurrence is a candidate finding unless it falls into one of the five structural exemptions listed below.

**Allowlist** (file-level skip — the entire file is exempt because it operates ON lessons as domain content):

- `marketplace/bundles/plan-marshall/skills/manage-lessons/**`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-*.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/lessons-*.md`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md` — the canonical citation home for plugin-doctor rules.

**Per-line structural exemptions** (skip the match, not the file):

1. **YAML frontmatter** — between the leading `---` fences at the start of a markdown file.
2. **Fenced code block** — any line inside a ``` ``` ``` fence regardless of info-string.
3. **`Source:` line** — provenance citation marker (e.g., `Source: lesson-XXX`).
4. **Inline-code span** — a lesson-ID inside backticks (`` `…` `` ). Token references are not narrative prose.

**Suppression mechanism**: Place `<!-- doctor-ignore: lesson-id-prose -->` on the same line as the match, or on the immediately preceding line, to suppress the finding on the marked line only. Use sparingly — the marker is for genuinely structural citations whose context the analyzer cannot detect (extremely rare; nearly every legitimate citation already qualifies as `Source:` or inline-code).

**Recommended fix**: Locate the line cited by the finding. If the lesson-ID + trivia is parenthetical or sits in its own sentence whose only payload is the citation, remove the entire sentence/parenthetical. Otherwise, strip the lesson-ID, the bracketed citation form (`(lesson XXX)`, `lesson-XXX`, `see lesson XXX`), and the recurrence-trivia phrases (`three recurrences in ~3 days`, `within ~3 days`, `N recurrences in M days`, etc.) while preserving the surrounding rule/decision content. The rule remains; the citation goes.

---

### shell-active-tokens

**Rule ID**: `shell-active-tokens`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shell_active_tokens.py`

**Scope**: `standards/*.md` within each skill directory.

**Intent**: Detect shell-active constructs embedded in skill markdown prose that would cause unintended shell expansion when copied into a terminal session. Four token classes are checked:

1. **backtick-in-flag** — Backtick characters inside `--detail`, `--message`, or `--title` flag values.
2. **brace-expansion** — Bash brace expansion (`{a..b}`, `{x,y,z}`) inside fenced `bash`/`sh` blocks or inline-code path-pattern regions.
3. **glob-wildcard** — Unquoted `*` or `?` outside fenced code blocks.
4. **dollar-token** — Unescaped `$VAR` or `$(...)` in inline-code spans.

**False-positive policy**: Glob wildcards inside fenced blocks and inline-code spans are exempt. Backtick checks are restricted to the three flag names listed. Dollar tokens are restricted to inline-code spans.

**Recommended fix**: Replace the shell-active token with a shell-safe equivalent (quoted string, escaped form, or narrative description).

**Suppression mechanism**: None — modify the prose.

---

### metadata-field-undefined

**Rule ID**: `metadata-field-undefined`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_metadata_field_validity.py`

**Scope**: All markdown under each skill directory (`SKILL.md`, `standards/`, `references/`, `workflow/`, `templates/`).

**Intent**: Flag backtick snake_case tokens that appear within three lines of a `metadata` or `set-metadata` mention and refer to field names not established by any `set-metadata --key {field}` invocation in the marketplace.

**False-positive policy**: Heuristic-based (±3 line proximity window). Builtin core fields (`change_type`, `worktree_path`, `use_worktree`, `confidence`, `plan_id`, etc.) are always exempt. Tokens shorter than 4 characters are ignored.

**Recommended fix**: Either add a `set-metadata --key <field>` write for the field, or correct the field name to a known one.

**Suppression mechanism**: The field is automatically recognized once a `set-metadata --key <field>` write appears anywhere in the marketplace.

---

### resolution-branch-side-effect-undocumented

**Rule ID**: `resolution-branch-side-effect-undocumented`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_resolution_branch_markers.py`

**Scope**: `standards/*.md` within each skill directory.

**Intent**: Every named branch under a `## Resolution` section must document at least one observable side effect — a write to a log, metadata, status, or artifact — so readers know what the branch actually does beyond its label.

**False-positive policy**: The branch-name allowlist gates which `###` headings are treated as resolution branches (`Hold`, `Accept`, `Split`, `Defer`, `Reject`, etc.). Non-allowlist headings inside Resolution sections are ignored. Side-effect keyword set: `log`, `metadata`, `status`, `artifact`, `decision.log`, `work.log`, `record`, `emit`, `persist`, `update`, `write`.

**Recommended fix**: Add a sentence to the branch body that explicitly names the side effect (e.g., "Record the decision to decision.log.").

**Suppression mechanism**: None — add the side-effect documentation.

---

### executor-path-in-production

**Rule ID**: `executor-path-in-production`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_executor_path_in_production.py`

**Scope**: `marketplace/bundles/**/scripts/**/*.py`.

**Intent**: Production Python scripts must not embed the `.plan/execute-script.py` literal path, because this creates a runtime coupling to the `.plan/` directory structure that breaks when the script is called from an unexpected location. Interactive Claude / manage-* invocations use executor notation; production code uses direct module imports.

**Whitelist categories** (path-component-anchored, not substring):
- `tools-script-executor/scripts/generate_executor.py` (executor generator)
- `tools-script-executor/templates/execute-script.py.template` (the template)
- `_analyze_verb_chains.py`, `_analyze_argument_naming.py`, `_analyze_markdown.py`, `_analyze_executor_path_in_production.py` (lint analyzers that inspect markdown)
- `tools-permission-fix/scripts/permission_fix.py` (permission tooling)

**Finding categories**: `production_script` or `test_assertion` (test files categorised separately).

**Recommended fix**: Remove the executor path literal. Replace with a direct module import or a documented interface contract.

**Suppression mechanism**: Add the file to the whitelist inside `_analyze_executor_path_in_production.py` with a comment explaining the rationale.

---

### plan-path-in-scripts

**Rule ID**: `plan-path-in-scripts`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_plan_path_in_scripts.py`

**Scope**: `marketplace/bundles/**/scripts/**/*.py`.

**Intent**: Production Python scripts must not embed the `.plan/plans/` literal path. The canonical plan-directory helper is `get_plan_dir(plan_id)` from `tools-file-ops:file_ops`, which resolves to `<repo>/.plan/local/plans/{plan_id}`. Any script that joins `plans/{plan_id}` against `cwd/.plan` directly resolves to the wrong path and produces a "ghost" `.plan/plans/{plan_id}/` tree at the repo root on every invocation. The originating failure mode is documented under the ghost-plan-dir bug, where two CI-completion scripts (`ci_complete_precondition.py` and `manage_ci_artifacts.py`) shipped hand-rolled `_resolve_plan_base_dir()` helpers that drifted from the canonical layout.

**Whitelist categories** (path-component-anchored, not substring):

- `_analyze_plan_path_in_scripts.py` — the analyzer's own file, which contains the marker literal as its detection target (self-referential).

**Docstring exemption**: The scanner deliberately ignores occurrences that fall entirely inside a `"""..."""` or `'''...'''` block. Many legacy docstring examples still cite the shorter shorthand; sweeping those is out of scope for this rule. Only code-literal hits in module-level or function-body source produce findings.

**Finding categories**: `production_script` or `test_assertion` (test files categorised separately by directory or `test_*` filename heuristic).

**Recommended fix**: Replace the hand-rolled resolver with `from file_ops import get_plan_dir` and use `get_plan_dir(plan_id)` directly. The helper returns `<repo>/.plan/local/plans/{plan_id}` and is the single source of truth for plan-directory resolution.

**Suppression mechanism**: Add the file to the whitelist inside `_analyze_plan_path_in_scripts.py` with a comment explaining the rationale. Suppression should be rare; the canonical alternative (`get_plan_dir`) covers nearly every legitimate use case.

---

### file-bloat-ack

**Rule ID**: Extension of `file-bloat` / `subdoc-bloat`

**Mechanism**: `_doctor_analysis.py` — `_has_file_bloat_ack()` helper called before `file-bloat` and `subdoc-bloat` issue emission.

**Intent**: Allow explicitly acknowledged bloated files to suppress the `file-bloat` and `subdoc-bloat` findings. The ack tag provides a human-readable rationale slug so the suppression is auditable.

**Ack format**: Add to the file's YAML frontmatter:

```yaml
quality:
  file-bloat: ack-<rationale-slug>
```

The ack tag must match `^ack-[a-z0-9_-]+$`. The slug after `ack-` must be non-empty and lowercase alphanumeric-or-hyphen-or-underscore. Examples: `ack-validator-registry`, `ack-large-reference-doc`, `ack-legacy-content`.

**Audit trail**: When an ack suppresses a finding, the tag value is stored under `bloat_ack_tag` in the analysis output dict for downstream reporting.

**False-positive policy**: Malformed values (`yes`, `true`, `ack-`, bare words) do not suppress — the finding is still emitted. Only well-formed `ack-*` values suppress.

**Suppression mechanism**: Add `quality.file-bloat: ack-<rationale>` to the file's YAML frontmatter. The plugin.json per-component override is explicitly out of scope — frontmatter is the only suppression channel.

---

### orphan-argparse-flag

**Rule ID**: `orphan-argparse-flag`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_orphan_argparse_flags.py`

**Scope**: Individual Python scripts passed to `analyze_orphan_argparse_flags(script_path)`.

**Intent**: Flag argparse flags that are declared in a `manage-*` script but never read in the corresponding subcommand handler body. Orphan flags accumulate when configuration keys are removed or renamed without also removing the argparse declaration.

**Detection**: AST walk. For each `add_argument('--flag', ...)` on a known parser variable, the analyzer resolves the handler via `set_defaults(func=cmd_*)` and checks whether `args.{dest}` appears in the function body.

**False-positive policy**: Conservative — when a handler uses `vars(args)`, `getattr(args, ...)`, or `**vars(args)` unpacking, the analyzer emits no findings for any flag in that handler (static analysis cannot determine which attrs are accessed).

**Recommended fix**: Either read the flag in the handler body, or remove the `add_argument` declaration.

**Suppression mechanism**: Use `vars(args)` or `getattr(args, ...)` in the handler body (triggers the conservative path), or remove the orphan flag declaration.

---

### cmd-root-anchoring-missing

**Rule ID**: `cmd-root-anchoring-missing`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_cmd_root_anchoring.py`

**Scope**: Dispatcher scripts — identified by the heuristic: at least one `set_defaults(func=cmd_*)` call with a `cmd_*` function name.

**Intent**: Every `cmd_*` function in a dispatcher script must (a) call `find_marketplace_root(...)` to anchor itself to the marketplace root, and (b) have a corresponding argparse subparser that declares `--marketplace-root` so callers can override the root path. Missing either piece creates a hidden coupling to the script's working directory.

**Three missing modes**:
- `prelude`: `find_marketplace_root(...)` call absent from the function body.
- `flag`: `--marketplace-root` flag absent from the corresponding subparser.
- `both`: neither the prelude call nor the flag is present.

**False-positive policy**: Non-dispatcher scripts (no `set_defaults(func=cmd_*)`) are out of scope. Prelude detection is order-tolerant — intermediate assignments and comments before the `find_marketplace_root(...)` call are allowed.

**Recommended fix**: Add `marketplace_root = find_marketplace_root(args.marketplace_root)` at the start of the function body, and add `p_sub.add_argument('--marketplace-root', dest='marketplace_root', ...)` to the corresponding subparser.

**Suppression mechanism**: None — implement the anchoring contract.

---

## Provenance Contract for New Rules

Every rule emitted by plugin-doctor must have a documented provenance entry before merge. This contract is enforced by the regression tests in `test/pm-plugin-development/plugin-doctor/test_rule_provenance_table.py`.

**Required artifacts for any new rule** (created in a single PR):

1. **Emitter** — a new branch in an `_analyze_*.py` module (or a new module under the same convention) that constructs the finding with `'type'` or `'rule_id'` set to the new rule ID.
2. **Row in [rule-provenance.md](rule-provenance.md)** under the appropriate section, carrying:
   - **Rule ID** (verbatim — the string that appears in the emitter)
   - **Class** (`structural` / `content` / `style` / `safety`)
   - **Emitter** (the module file that constructs the finding)
   - **Source** citation — a lesson ID (`2026-MM-DD-HH-NNN`), a referenced architectural standard, or a `decision.log` entry. The Source field MUST be non-empty.
3. **Row in this `rule-catalog.md`** documenting the rule's intent, detection approach, fix strategy, and suppression mechanism (if any).
4. **Test** in `test/pm-plugin-development/plugin-doctor/` exercising the rule against synthetic fixtures.

**Additional artifacts for fixable rules**:

5. **Apply handler** in `_cmd_apply.py::FIX_HANDLERS` keyed by the rule ID.
6. **Verify branch** in `_cmd_verify.py::cmd_verify` (or a deliberate route to `verify_generic`).
7. **Row in [fix-catalog.md](fix-catalog.md)** documenting the safe/risky classification and the fix payload shape.
8. **Membership in `_doctor_shared.py::FIXABLE_ISSUE_TYPES`** plus either `SAFE_FIX_TYPES` or `RISKY_FIX_TYPES`.

**Inadmissible rules** — rules without a provenance entry are fabricated and will be removed in the next provenance audit. See the audit history at the bottom of `rule-provenance.md` for precedents.

**Audit gate**: The `test_every_emitted_rule_id_has_provenance_entry` regression test in `test_rule_provenance_table.py` will fail the build if any analyzer-emitted rule ID is missing a provenance row. The `test_fixable_issue_types_have_provenance` test enforces the same constraint for the fix registry.
