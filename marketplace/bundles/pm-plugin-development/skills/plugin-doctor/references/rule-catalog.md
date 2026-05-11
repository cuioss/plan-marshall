# Rule Catalog

Rules that plugin-doctor validates in other components. See the Enforcement block in SKILL.md for this skill's own constraints.

> **Related**: For architectural principles with rationale and examples, see `plugin-architecture:architecture-rules`. This catalog lists validation rules only.

## Agent Rules

**agent-task-tool-prohibited**: Agents cannot declare the Task tool (unavailable at runtime).

**agent-maven-restricted**: Only the maven-builder agent may execute Maven commands.

**agent-lessons-via-skill**: Agents record lessons via manage-lessons skill, not self-invoke commands.

**agent-skill-tool-visibility**: Agents declaring explicit tools must include Skill, otherwise invisible to Task dispatcher.

**agent-glob-resolver-workaround** (severity: error): Flags `agents/*.md` whose YAML frontmatter `tools:` field includes `Glob` unless the agent body contains a `# resolver-glob-exempt:` marker followed by a one-line non-empty justification. Scope: `marketplace/bundles/*/agents/*.md`.

- **Rationale**: Agents granted `Glob` access overwhelmingly use it to hand-roll discovery that should be delegated to a canonical resolver script. This is the same resolver-gap anti-pattern as `skill-resolver-gap`, but at the agent permission layer: once `Glob` is in the agent's tool list, prose-driven discovery becomes the path of least resistance and resolver scripts go unused. See driving lesson 2026-04-27-18-005.
- **Discovery approach**: Parse YAML frontmatter, check the `tools:` array for the `Glob` token (handles both inline `tools: Read, Write, Glob` and block-list forms). If present, scan the body for a `# resolver-glob-exempt:` marker followed by a non-empty justification on the same line. Absence emits a `agent-glob-resolver-workaround` finding pointing at the agent file.
- **Fix**: Remove `Glob` from the agent's `tools:` field and replace any Glob-driven discovery with a `python3 .plan/execute-script.py` call to a canonical resolver. If the agent legitimately needs raw `Glob` access (rare — typically only for diagnostics or one-off introspection), add a `# resolver-glob-exempt: <one-line justification>` line in the agent body to declare intent.
- **Exemptions**: Add a `# resolver-glob-exempt: <justification>` line in the agent body. The justification text must be non-empty; an empty marker does not suppress the finding.

## Workflow Rules

**workflow-explicit-script-calls**: All script/tool invocations in workflow documentation have explicit bash code blocks with the full `python3 .plan/execute-script.py` command.

**workflow-hardcoded-script-path**: Use executor notation (`bundle:skill:script`) instead of hardcoded file paths.

**workflow-prose-parameter-consistency**: Prose instructions adjacent to `execute-script.py` bash blocks must reference parameter values consistent with the actual script API.

**prose-verb-chain-consistency** (severity: error): Flags prose sentences in workflow documentation that reference a `{notation} {verb-chain}` combination where the verb chain is not a registered subcommand path of the referenced script. Scope: `SKILL.md` plus every `standards/*.md` inside each script-bearing skill directory under `marketplace/bundles/*/skills/`.

- **Rationale**: Prose drift lets workflow instructions reference verb chains the script never exposed. Concrete drift incident driving this rule: `phase-2-refine/SKILL.md` prose referenced `manage-plan-documents request clarify` when the script only registered `request read` and `request mark-clarified` — a human-reader would copy the command and hit an argparse error at runtime, with no structural check catching the mismatch. See driving lesson 2026-04-18-16-001.
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

**skill-unused-tools-declared**: Skills declare `allowed-tools` that are never referenced in SKILL.md content. Detection is structural (frontmatter extraction); semantic usage analysis is delegated to tool-coverage-agent.

**skill-naming-noun-suffix**: Skill directory names must not end with a reserved noun suffix (`-executor`/`-executors`, `-manager`/`-managers`, `-runner`/`-runners`, `-handler`/`-handlers`, `-orchestrator`/`-orchestrators`). These suffixes are reserved for spawnable marketplace agents. Skills must use verb-first names (e.g. `execute-task` instead of `task-executor`). See `pm-plugin-development:plugin-architecture` `references/skill-design.md` "Skill Naming Convention" for the full rationale. Detection runs during skill structure analysis.

**skill-resolver-gap** (severity: warning): Flags skill `SKILL.md` and `standards/*.md` prose containing LLM-Glob discovery patterns (`Use Glob:`, `Glob pattern:`, `Discover ... using Glob`, `find ... using Glob patterns`) without an adjacent `python3 .plan/execute-script.py` invocation within the next 5 lines. Scope: `marketplace/bundles/*/skills/*/SKILL.md` and `marketplace/bundles/*/skills/*/standards/*.md`.

- **Rationale**: Skills that direct an LLM to perform discovery via `Glob`/`Grep` when a canonical resolver script already exists for that domain re-introduce the resolver-gap anti-pattern: the LLM hand-rolls discovery logic that should live in a deterministic script, and successive runs drift in coverage and ordering. Concrete drift incident: prose like "Use Glob: marketplace/bundles/*/skills/*/SKILL.md" appearing without a follow-up `execute-script.py` call to a resolver — a human-reader copies the suggestion and produces non-deterministic results compared to the resolver's output. See driving lesson 2026-04-27-18-005.
- **Discovery approach**: Line-by-line regex scan over markdown content. For each match of an LLM-Glob trigger phrase, the analyzer inspects the next ≤5 lines for `python3 .plan/execute-script.py`. If absent, a `skill-resolver-gap` finding is emitted with the line of the prose match. Pure static analysis — no script execution, no imports.
- **Fix**: Replace the LLM-Glob prose with a `python3 .plan/execute-script.py {bundle}:{skill}:{script}` invocation that delegates discovery to a canonical resolver. If no resolver exists yet, add one before relying on Glob from prose.
- **Exemptions**: Place `<!-- doctor-ignore: resolver-gap -->` on the line immediately preceding the prose block to suppress the finding for that occurrence (use sparingly — only when prose deliberately documents an LLM-driven discovery for which no resolver is appropriate, e.g., debugging instructions or single-shot diagnostics).

## Script Rules

**argparse_safety** (severity: error): Flags every `argparse.ArgumentParser(...)` constructor call and every `subparsers.add_parser(...)` call in marketplace Python scripts that does not pass `allow_abbrev=False`. Scope: files under `marketplace/bundles/*/skills/*/scripts/` and `marketplace/targets/**/*.py`. Tests are exempt (files under `test/`/`tests/` directories or named `test_*.py` / `*_test.py`).

- **Rationale**: Without `allow_abbrev=False`, argparse matches unknown long options by unique prefix. When a flag is renamed or retired, old callers keep working silently via prefix binding — the contract rot is invisible until something behaves wrong under a rename. See driving lesson 2026-04-17-012 (argparse prefix-matching silently binds retired flags).
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

## Rule Pack: Plugin-doctor lint guards (lesson 2026-05-05-18-001)

Seven forward-looking lint rules added as part of the lesson-2026-05-05-18-001 plan.

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `shell-active-tokens` | Detect shell-active constructs (backticks in flags, brace expansion, glob wildcards, dollar tokens) in skill standards prose | Four specific token classes; `glob-wildcard` exempt inside fenced blocks and inline code | None — fix the offending prose |
| `metadata-field-undefined` | Flag backtick snake_case tokens near metadata prose that reference field names not written by any `set-metadata --key` invocation | Heuristic proximity (±3 lines); builtin fields always exempt | Add `set-metadata --key <field>` write anywhere in the marketplace |
| `resolution-branch-side-effect-undocumented` | Require `## Resolution` branches in standards to document at least one observable side effect | Allowlist-gated branch names; non-allowlist headings ignored | Add a log/metadata/status/artifact mention to the branch body |
| `executor-path-in-production` | Detect `.plan/execute-script.py` in production Python scripts outside whitelisted categories | Whitelist covers generator, lint analyzers, permission tooling | Add path to whitelist in `_analyze_executor_path_in_production.py` |
| `file-bloat-ack` | Allow explicitly acknowledged bloated files to suppress the `file-bloat` finding | Ack tag must match `^ack-[a-z0-9_-]+$`; bare `ack-` or generic values do not suppress | Add `quality.file-bloat: ack-<rationale>` to the file's YAML frontmatter |
| `orphan-argparse-flag` | Flag argparse flags declared but never read in their handler | Conservative: `vars(args)`, `**kwargs`, or `getattr` usage suppresses the check | Read the flag in the handler, or remove the declaration |
| `cmd-root-anchoring-missing` | Require `cmd_*` dispatcher functions to call `find_marketplace_root(...)` and declare `--marketplace-root` | Dispatcher-heuristic gated: only fires for scripts with `set_defaults(func=cmd_*)` | Add both the prelude call and the `--marketplace-root` flag to the subparser |

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

**Scope**: All markdown under each skill directory (`SKILL.md`, `standards/`, `references/`, `workflows/`, `templates/`).

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
