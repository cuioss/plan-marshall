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

## Simplification Rules

The `SIMPLICITY_*` rule cluster is the mechanical enforcement layer for the "minimum viable code" posture defined in `plan-marshall:dev-general-code-quality` `standards/code-organization.md` [#minimum-viable-code](../../../plan-marshall/skills/dev-general-code-quality/standards/code-organization.md). The seven anti-patterns in that section are the source-of-truth definitions; these five rules detect the deterministically-recognisable subset in marketplace bundle scripts. The cognitive judgement calls (the remaining anti-patterns and the non-mechanical instances of these five) are handled by the `default:finalize-step-simplify` phase-6 cognitive pass — the two layers compose, the doctor catching the static patterns and the finalize step reasoning about the rest. No new registered entry-point: the rules run behind the existing `doctor-marketplace analyze` interface, alongside `argparse_safety`.

**Scope**: `marketplace/bundles/*/skills/*/scripts/**/*.py` (test files excluded). **Discovery approach**: one `ast.parse` walk plus a per-line regex pass per script — pure static analysis, no subprocess, no module imports. Implemented in `_analyze_simplicity.py`.

**SIMPLICITY_UNUSED_PARAMETER** (severity: warning, fixable: false): Flags a function whose body discards a declared parameter via `del <param>` (the "preserved for future use" pattern that keeps a signature stable while no code path reads the argument), or a parameter/assignment line tagged with a trailing `# unused` marker.

- **Rationale**: A parameter that no code path reads, kept "because a caller might need it later", is surplus structure. Remove it and add it back against a real caller. Maps to the `#minimum-viable-code` "Unused parameters preserved for future use" bullet.
- **Fix**: Remove the parameter from the signature and the discarding `del`. Confirm-before-apply (risky) because it changes a public signature — surfaced for human review rather than auto-applied.

**SIMPLICITY_BACKWARD_COMPAT_REEXPORT** (severity: warning, fixable: false): Flags an `import`/`from` line carrying a `# backward compat` or `# re-exported for` comment.

- **Rationale**: A module that exists only to re-export a symbol, with at most one importer, is a shim. Inline the import at the single call site and delete the shim. Maps to the "Thin/backward-compat re-exports with <= 1 live caller" bullet.
- **Fix**: Inline the import at its call site and delete the re-export. Confirm-before-apply (risky) — requires verifying the live-caller count.

**SIMPLICITY_DEFENSIVE_CATCHALL** (severity: warning, fixable: false): Flags an `except Exception` / `except BaseException` / bare `except` handler tagged `# defensive only` or `# pragma: no cover -- defensive` on the handler header or its first body line.

- **Rationale**: A guard that swallows or re-wraps an exception the caller already handles, or that masks a programming error that should crash loudly, hides failures. Let it propagate. Maps to the "Defensive try/except around already-handled or should-fail-loudly failures" bullet.
- **Fix**: Remove the handler and let the exception propagate. Confirm-before-apply (risky) — the propagation path must be verified.

**SIMPLICITY_THIN_WRAPPER** (severity: warning, fixable: false): Flags a function whose body (after an optional docstring) is a single `return <call>(...)` forwarding its arguments to one other call.

- **Rationale**: A thin pass-through wrapper adds an indirection layer with no value. Inline it at the call site. Maps to the Over-Abstraction "Utility methods called from only one place" / wrapper-class bullets.
- **Fix**: Inline the wrapper at its call sites and delete it. Confirm-before-apply (risky) — inlining requires rewriting every caller, which is not a single-file mechanical edit.

**SIMPLICITY_SIGNATURE_DOCSTRING** (severity: warning, fixable: true): Flags a function docstring whose first paragraph only restates `Args:`/`Returns:` structural headers with no intent ("WHY") content.

- **Rationale**: A docstring that names the parameters and return type without adding intent beyond the signature is noise. Delete it or replace it with a rationale. Maps to the "Signature-restating docstrings/comments" bullet.
- **Fix**: **Safe auto-apply** — the fix handler re-parses the file and deletes every signature-restating docstring node. This is the one mechanically-safe simplification fix: deleting a pure-structural docstring changes no behaviour and no signature.
- **Exemptions**: Docstrings carrying any prose summary line in their first paragraph (intent content) are not flagged.

## Argument Naming Rules

The `ARGUMENT_NAMING_*` rule cluster cross-checks marketplace prose against the actual argparse declarations of the scripts that prose references. The cluster also cross-checks the Canonical Forms table in `marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/argument-naming.md` against the same argparse declarations. All four rules emit findings with `severity: error` and `fixable: false`, mirroring the `DISPLAY_DETAIL_*` finding shape used elsewhere in plugin-doctor.

**Activation**: This cluster is unconditionally active. Multiple recurrences of stale-flag drift in skill workflows drove the move from a gated transitional period to default-on enforcement. Tests exercise the cluster directly against synthetic fixtures.

**Scope**: every `python3 .plan/execute-script.py {notation} ...` token across SKILL.md, agents/*.md, commands/*.md, skills/*/standards/*.md, skills/*/references/*.md, skills/*/recipes/*.md within `marketplace/bundles/*/`. The Canonical Forms cross-check additionally reads the table at `marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/argument-naming.md`.

**Discovery approach**: Pure static analysis — line-by-line regex extraction of executor invocations, plus AST walks of the referenced scripts to enumerate argparse subparsers and `add_argument` flag declarations. Mirrors the existing `argparse_safety` and `prose-verb-chain-consistency` patterns. No subprocess execution, no module imports.

**ARGUMENT_NAMING_NOTATION_INVALID** (severity: error): Flags `python3 .plan/execute-script.py {notation}` tokens whose 3-part `{bundle}:{skill}:{script}` notation is not present in the executor's embedded `SCRIPTS` dict. The finding `details.reason` distinguishes three failure modes: `snake_case_not_registered` (the notation contains underscores where the registry expects kebab-case), `third_segment_repeats_second` (the script segment exactly repeats the skill segment, e.g. `manage-providers:manage-providers`), and `not_registered` (the notation does not appear in the registry for any other reason). The `details.notation` field carries the offending notation verbatim.

- **Rationale**: A mistyped notation routes through `.plan/execute-script.py` to a missing entry; the executor errors out at the caller's site, but no static check has caught the drift earlier. The cluster moves the failure forward to plugin-doctor time so reviewers see the issue before merge.
- **Fix**: Update the prose to use a registered notation. Run `/marshall-steward` after bundle changes to regenerate the executor with updated mappings.
- **Exemptions**: None — every executor invocation in marketplace prose is expected to resolve.

**ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN** (severity: error): Flags `python3 .plan/execute-script.py {notation} {sub}` tokens where `{sub}` is not a registered subcommand on the resolved script. The cluster AST-walks the referenced script's argparse tree (`add_subparsers` → `add_parser('name', ...)`) and reports any `{sub}` that is not in the resulting set. The `details.known_subcommands` field lists the registered subcommands, and `details.subcommand` carries the offending token.

- **Rationale**: Prose drift lets workflow instructions reference subcommands the script never exposed (e.g., the historical `manage-references list` and `manage-status get-plan-dir` patterns). A reader who copies the command hits an argparse error at runtime; the cluster catches the drift statically.
- **Fix**: Update the prose to use a registered subcommand, or add the missing subcommand to the script's argparse tree.
- **Exemptions**: Scripts that declare no subparsers are skipped — any token following the notation is a positional argument, not a subcommand. Scripts whose argparse declarations cannot be parsed (syntax error, missing file) are skipped silently; the notation rule reports the missing script when applicable.

**ARGUMENT_NAMING_FLAG_UNKNOWN** (severity: error): Flags `--{flag}` tokens following a notation+sub pair when `{flag}` is not declared via `add_argument(...)` on the matching subparser (or on the root parser when no subcommand is present). The `details.known_flags` field lists the declared long flags, and `details.flag` carries the offending name.

- **Rationale**: Renaming or retiring a flag while leaving prose unchanged silently breaks instructions. Concrete drift incidents: `--content-stdin`, `--field`, `--limit`, and `--json` references in prose where the script declared none of them. The cluster moves these failures from runtime to review time.
- **Fix**: Update the prose to use a declared flag, or add the missing flag to the script's `add_argument` declarations.
- **Exemptions**: Short flags (`-f`) are not subject to canonical-forms convention and are excluded from the scan. Flags whose script has no resolvable AST entry (missing file, parse error) are skipped silently — the notation rule reports the missing script.

**ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT** (severity: error): Cross-checks every row of the Canonical Forms table at `marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/argument-naming.md` against the argparse declarations of the script the row prescribes. The cluster parses each row's `{script} {sub} --{flag1} {value1} --{flag2} ...` shape, resolves the `{script}` shorthand to a registered notation (matching on either the third segment of the notation or the second when the script shares its skill name), and confirms that `{sub}` is a declared subcommand and every `--{flag}` is declared on that subparser. Failure modes carried in `details.reason`: `shorthand_unresolved`, `subcommand_drift`, `flag_drift`.

- **Rationale**: The Canonical Forms table is the documented contract for argument naming across `manage-*` scripts. If the table prescribes a spelling the argparse declarations no longer honor, every author who consults the table for guidance writes broken prose. The cross-check guarantees the table stays in sync with the implementations it governs.
- **Fix**: Update either the Canonical Forms row or the argparse declaration so the two agree. When the table is correct and the script lags, rename the argparse flag; when the script is correct and the table lags, update the row.
- **Exemptions**: None within the table's scope. Rows whose `{script}` shorthand resolves to multiple registered notations are reported with `reason: shorthand_unresolved` so the table can be tightened to use the full bundle:skill:script form when ambiguity arises.

**manage-findings-invocation-invalid** (severity: error): Catches three canonical invalid spellings of the `plan-marshall:manage-findings:manage-findings` notation and its argparse tree that have surfaced as LLM hallucinations at runtime: (1) **script-position underscore** — `plan-marshall:manage-findings:manage_findings` (snake_case where the executor registry uses kebab-case); (2) **invalid top-level subcommand** — any token other than the registered `add, list, get, resolve, promote, qgate, assessment`; the historically recurring invented form is `list-qgate`; (3) **invalid `qgate` sub-verb** — any sub-verb other than the registered `add, list, resolve, clear`; the recurring legacy form is `qgate query` (the canonical verb is `list`). The rule also catches invalid `assessment` sub-verbs as defence in depth. Findings carry `details.canonical_hint` with the closest correct spelling.

- **Discovery approach**: Pure static analysis — line-anchored regex extraction of `plan-marshall:manage-findings:*` notation tokens from skill markdown bodies (`SKILL.md`, `standards/*.md`, `references/*.md`, `workflow/*.md`, `recipes/*.md`). The registered argparse tree (`add, list, get, resolve, promote, qgate, assessment` top-level; `add, list, resolve, clear` under `qgate`; `add, list, get, clear` under `assessment`) is baked into the analyzer as the source-of-truth constant; the rule does not import `manage-findings.py` or subprocess-execute the script. Mirrors `_analyze_argument_naming.py` and `_analyze_verb_chains.py` patterns. No `did-you-mean` runtime changes to `manage-findings.py`.
- **Fix**: Update the prose to use the canonical-form hint emitted in the finding payload. For `list-qgate`, use `qgate list --plan-id {plan_id} --phase {phase}`. For `qgate query`, use `qgate list --plan-id {plan_id} --phase {phase}`. For snake_case script position, replace `manage_findings` with `manage-findings` in the third notation segment.
- **Rationale**: Three invalid `manage-findings` invocation shapes surfaced as LLM hallucinations at runtime, producing silent argparse rejections that the calling workflow swallowed. Grepping `marketplace/bundles/` for these shapes returns zero matches at source time — the failure mode is recurrence-prone LLM drift, not source drift. Catching the shapes at edit time via plugin-doctor moves the structural guard from runtime to review time, in the same spirit as the `ARGUMENT_NAMING_*` cluster.
- **Exemptions**: None — every `plan-marshall:manage-findings:*` invocation in skill markdown is expected to resolve to a registered notation, subcommand, and sub-verb. The rule is gated on the `manage-findings-invocation-invalid` opt-in token in `active_rules` (mirroring the `verb_chain` opt-in semantics), so it only runs when the caller explicitly requests it.

**manage-invocation-invalid** (severity: error): Generalization of the `manage-findings-invocation-invalid` rule across every script-bearing skill in the marketplace. The in-scope set is derived at scan time by walking the bundle tree — each skill that registers an argparse CLI entry-point invoked via 3-part `bundle:skill:script` executor notation is covered, keyed off the on-disk path (`{bundle}:{skill}:{script_stem}`) rather than any filename==skill assumption (e.g. `plan-marshall:plan-doctor:plan_doctor`, `plan-marshall:extension-api:extension_discovery`). The derivation excludes `_`-prefixed helper modules, shared-only helper skills (`script-shared`, `tools-file-ops`, `tools-input-validation`), non-entry-point reference skills (`ref-toon-format`, `platform-runtime`), and `manage-findings` (covered by its own dedicated analyzer). For each invocation found in skill markdown, the analyzer extracts the `(subcommand, sub_verb, flags)` tuple and validates it against the script's canonical argparse tree built at scan time. Four failure modes are reported independently, each with `details.canonical_hint` carrying the closest correct form: (1) unknown top-level subcommand (`details.reason: subcommand_unknown`); (2) unknown sub-verb under a subcommand that declares its own subparser (`details.reason: sub_verb_unknown`); (3) unknown long flag `--{flag}` under the resolved leaf parser (`details.reason: flag_unknown`); (4) missing required flag declared by the resolved leaf parser (`details.reason: required_flag_missing`).

- **Discovery approach**: Pure static analysis — the in-scope set is auto-derived by `discover_in_scope_scripts`, which walks `bundles/{bundle}/skills/{skill}/scripts/*.py`, drops `_`-prefixed and excluded-skill scripts, and AST-confirms each candidate declares an `ArgumentParser`. Each in-scope script is then `ast.parse`-walked into a canonical tree `{subcommand: {sub_verb_or_none: {flags, required_flags}}}`. The markdown scan is line-anchored regex extraction of `python3 .plan/execute-script.py {bundle}:{skill}:{script}` invocations from `SKILL.md`, `standards/*.md`, `references/*.md`, `workflow/*.md`, and `recipes/*.md`. Each occurrence is tokenized into positional + flag args and cross-checked against the canonical tree. No subprocess execution, no import of the target scripts. Mirrors the `_analyze_argument_naming.py` and `_analyze_manage_findings_invocation.py` precedents. The implementation lives in `_analyze_manage_invocation.py` (analyzer module) — see the canonical-block convention published in each in-scope SKILL.md's `## Canonical invocations` section for the authoritative spelling reference. The cluster runs unconditionally under `cmd_quality_gate` (build-failing) and `cmd_analyze`.
- **Fix**: Update the markdown invocation to match the script's canonical argparse surface. The finding's `details.canonical_hint` names the closest correct subcommand / sub-verb / flag spelling; the corresponding `## Canonical invocations` section in the script's owning SKILL.md is the full reference.
- **Rationale**: Argparse-surface drift in LLM-authored prose is a recurring failure mode that produces silent `exit_code: 2` rejections at runtime. The `manage-findings-invocation-invalid` rule covers one script; this rule generalizes the same structural guard across every script-bearing skill in the marketplace and runs as a build-failing `quality-gate` regression net. Catching token-tree mismatches at edit time moves a class of runtime argparse rejections to review time.
- **Exemptions**: The in-scope set auto-derives from the bundle tree — new script-bearing skills are covered automatically as they land, with no whitelist edit required. Excluded from derivation: `_`-prefixed helper modules, shared-only helper skills (`script-shared`, `tools-file-ops`, `tools-input-validation`), non-entry-point reference skills (`ref-toon-format`, `platform-runtime`), and `manage-findings` (covered by its own dedicated analyzer). Scripts whose AST cannot be parsed (syntax error, missing file) are dropped from the index silently; the notation-validity rule (`ARGUMENT_NAMING_*` cluster) reports the missing-script case independently.

**missing-canonical-block** (severity: warning, build-failing under quality-gate): Emitted when a script-bearing SKILL.md lacks a `## Canonical invocations` section. The in-scope set is auto-derived from the bundle tree (every skill that registers an argparse CLI entry-point invoked via 3-part notation). The section is the documented source-of-truth authoring contract: it carries one `### {subcommand}` heading per registered top-level subcommand with a fenced bash block showing the canonical invocation shape (positional sub-verbs + required flags + optional flags). Authors consult the block when writing prose that invokes the script, and Rule-2 xrefs resolve against it; missing it leaves authors with no in-skill reference and leaves xrefs unresolvable. Findings carry `details.notation` (the in-scope notation triple owned by the skill) and `details.canonical_hint` (the relative path to repair).

- **Discovery approach**: Pure regex scan — search each in-scope SKILL.md for `^##\s+Canonical\s+invocations\s*$` (case-insensitive). Absence emits one finding per skill directory (deduplicated when multiple notation triples share the same owning skill). The finding payload carries severity `warning`, but the rule runs inside `cmd_quality_gate`, so any finding fails the build — a script-bearing skill that ships without its Canonical-invocations section breaks the gate.
- **Fix**: Add a `## Canonical invocations` section to the named SKILL.md, with one `### {subcommand}` subsection per registered top-level subcommand. Each subsection contains a fenced bash block showing the canonical invocation shape. See `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` for the reference layout.
- **Rationale**: The canonical-block convention is the in-skill mirror of the `manage-invocation-invalid` rule above. The rule machine-validates markdown invocations against the argparse AST; the canonical block gives human authors the same view in the spelling they will write, and is the source-of-truth a Rule-2 xref points at. Together they close the drift surface from both ends. Wiring the rule into the build gate enforces that every script-bearing skill publishes the section.
- **Exemptions**: The in-scope set auto-derives from the bundle tree — new script-bearing skills are checked automatically as they land, with no whitelist edit required. Excluded from derivation: `_`-prefixed helper modules, shared-only helper skills (`script-shared`, `tools-file-ops`, `tools-input-validation`), non-entry-point reference skills (`ref-toon-format`, `platform-runtime`), and `manage-findings` (covered by its own dedicated analyzer).

## Content Rules

**checklist-pattern**: Checkbox patterns (`- [ ]`, `- [x]`) in LLM-consumed files. These are human UI elements with zero value for LLMs. Exception: files in `/templates/` directories (rendered by GitHub).

## Phase-6 Finalize Step Termination

Three rules guard against defective `mark-step-done` invocations inside marketplace skill/agent markdown. They fire on any bash code fence that references `mark-step-done` and inspect the single logical invocation (including backslash-continued continuation lines). Each defect code is emitted independently, so a single malformed invocation may produce multiple findings.

**Rationale**: Phase-6 finalize step termination is a silent-failure surface. A mistyped notation resolves to a non-existent script and is swallowed by the executor; a missing `--phase` routes the termination to the wrong phase record; a missing `--outcome` leaves the step in an ambiguous `in_progress` state even though the workflow believes it completed. Static detection in plugin-doctor is the cheapest way to catch these errors before they ship.

**MARK_STEP_DONE_STALE_NOTATION** (severity: error): The invocation line contains the stale underscored notation `manage-status:manage_status` instead of the canonical kebab-case form `manage-status:manage-status`. The executor uses notation segments as literal keys — the underscored form no longer resolves after the entrypoint-rename cutover. Detection is a substring check on every line of the invocation (including continuation lines, since the notation often lives on the command line itself).

**MARK_STEP_DONE_MISSING_PHASE** (severity: error): The full `mark-step-done` invocation (single line or backslash-continued multi-line) does not contain `--phase`. Without it, the status manager cannot route the step termination to the correct phase record, and finalize-phase orchestration reads stale status.

**MARK_STEP_DONE_MISSING_OUTCOME** (severity: error): The full invocation does not contain `--outcome`. Without an explicit outcome (e.g. `done`, `skipped`, `deferred`), the step cannot be definitively terminated and the phase status entry remains ambiguous.

Canonical form — kebab-case notation with every required flag present:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase phase-6-finalize --step {step} --outcome done
```

A violation is any deviation from this shape: the underscored `manage_status` notation (STALE_NOTATION), a dropped `--phase` (MISSING_PHASE), or a dropped `--outcome` (MISSING_OUTCOME).

Detection lives in `_analyze_markdown.py::check_mark_step_done_violations`; findings are surfaced through the standard markdown reporting channel in `_doctor_analysis.py::extract_issues_from_markdown_analysis` with the defect code as the issue `type`.

**finalize-step-token-mismatch** (severity: error, fixable: false): Flags a finalize-step skill whose documented `mark-step-done --step {token}` argument under `--phase 6-finalize` does not match the skill's fully-qualified manifest step_id. The documented token is the key the dispatched finalize step records its terminal outcome under; the manifest declares the SAME step under its canonical step_id. When the documented token drifts away from the manifest step_id, the recording side keys `phase_steps` under the wrong name, the `phase_steps_complete` handshake reports the canonical step missing, and the halt-and-retry recovery loop runs forever. Findings carry `details.documented_token` (the parsed `--step` value) and `details.expected_step_id` (the canonical manifest step_id).

- **Scope**: Two roots are walked. (1) **Bundle finalize-step skills** — `marketplace/bundles/{bundle}/skills/{skill}/SKILL.md` for every `{bundle}:{skill}` reference in the authoritative `OPTIONAL_BUNDLE_FINALIZE_STEPS` registry in `manage-config/_config_defaults.py` (the single source of truth); the expected step_id is that registry reference, i.e. `{bundle}:{skill}`. (2) **Project-local finalize-step skills** — `<repo>/.claude/skills/finalize-step-*/SKILL.md` discovered by glob; the expected step_id is `project:{name}` where `{name}` is the skill directory basename.
- **Discovery approach**: Pure static analysis, mirroring `_analyze_historical_prose_in_skills.py` and `_analyze_lesson_id_in_skill_prose.py` — regex-driven extraction from markdown source, stdlib-only, no subprocess execution, no imports of target scripts, no file mutation. The `--step` token is parsed from the first `mark-step-done` block that carries both `--phase 6-finalize` and `--step {token}` (order-independent; both `--flag value` space and `--flag=value` equals forms), reusing the PR #629 parsing contract verbatim. Skills emitting no `mark-step-done --phase 6-finalize` invocation are silently skipped (no false positive). A finding is emitted only when the parsed token differs from the expected step_id. Implemented in `_analyze_finalize_step_token.py::scan_finalize_step_token`.
- **Activation**: Runs unconditionally inside `cmd_quality_gate` (build-failing). Findings carry absolute file paths, so `--paths` scoping applies uniformly.
- **Fix**: Align the documented `mark-step-done --step` token with the skill's manifest step_id named in `details.expected_step_id` — for a bundle finalize-step that is the `{bundle}:{skill}` registry reference, for a project-local step it is `project:{name}`.
- **Exemptions**: None — every finalize-step skill that documents a `mark-step-done --phase 6-finalize` invocation is expected to record under its canonical manifest step_id. Skills with no such invocation are out of scope by construction.

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
| `shell-substitution-in-skills` | Forbid `$(` command substitution in plan-marshall skill markdown — violates the dev-agent-behavior-rules "Bash: no shell constructs" hard rule | Two structural exemptions: any occurrence inside a markdown inline-code span (`` `…` ``), or any occurrence inside a fenced block with `markdown`/`text` info-string. Subagents do not execute either context | None — convert to the documented two-call + text-substitution pattern |

### shell-substitution-in-skills

**Rule ID**: `shell-substitution-in-skills`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shell_substitution_in_skills.py`

**Scope**: All `*.md` files under `marketplace/bundles/plan-marshall/skills/`.

**Intent**: Enforce the dev-agent-behavior-rules "Bash: no shell constructs" hard rule (`dev-agent-behavior-rules/SKILL.md` § "Bash: One command per call", `tool-usage-patterns.md` § "Bash safety rules") at the skill-documentation layer. A `$(` in a workflow doc gets interpreted by subagents that copy the snippet into a Bash call literally — the host platform's permission UI then either pops a security prompt or rejects the dispatch outright. The rule prevents regressions of the sweep that removed all such patterns.

**Detection logic**: Scans every line of every markdown file under `marketplace/bundles/plan-marshall/skills/`. Each `$(` two-character occurrence is a candidate finding unless it falls into one of the two exempt documentary contexts below.

**Permitted contexts**:
1. **Inline-code span** — A `$(` inside a markdown inline-code span (`` `…` ``). Subagents do not execute inline-code tokens; these are structural token references (e.g., when a standards doc says "the `$(...)` form is forbidden"), not runnable commands.
2. **Verbatim-source fenced block** — A `$(` inside a fenced block whose info-string is `markdown` or `text`. These fences hold verbatim source examples (before/after illustrations) that subagents do not interpret as instructions.

**Rationale**: The two-call + text-substitution pattern (run the script as a bare command, then use a `{placeholder}` slot in the next command's narrative substitution) is the documented safe alternative — see `dev-agent-behavior-rules/SKILL.md` § "Bash: One command per call". The exemption logic is purely structural (inline-code span or `markdown`/`text` fence) so the rule does not depend on a fragile keyword heuristic in the surrounding prose.

**Recommended fix**: Replace `target=$(python3 .plan/execute-script.py …)` with the bare `python3 .plan/execute-script.py …` invocation followed by a one-sentence narrative ("Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below."). Replace `$var` references in subsequent bash blocks with `{var}` placeholders.

**Suppression mechanism**: None — convert the substitution to the documented safe alternative. If the occurrence is genuinely documentary (a standards doc that names the forbidden pattern), wrap it in an inline-code span (`` `…` ``) so the structural exemption applies.

---

## Rule Pack: Bash chain-shape invariant

**Activation**: Unconditionally active in `doctor-marketplace.py analyze` mode. NOT included in `quality-gate` — the existing marketplace tree pre-dates these rules and contains documented examples of the forbidden patterns inside bash fences; a cleanup sweep is required before these rules can be promoted to quality-gate level. Invoke via `analyze` for explicit drift sweeps; new code written after this plan is checked by the analyze path.

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `bash-chain-shapes-in-skills` | Detect compound Bash command sequences (`&&`, `;`, trailing `&`) inside fenced `bash`/`sh` blocks in plan-marshall skill/agent/command markdown — violates the dev-agent-behavior-rules "Bash: one command per call" hard rule | Comment lines (`#`) and inline-code spans are exempt; only `bash`/`sh`-fenced blocks are scanned | None — split the compound command into separate Bash tool calls |
| `tmp-redirect-in-skills` | Detect `>` / `>>` redirect targets pointing at `/tmp/` or `/var/tmp/` inside fenced `bash`/`sh` blocks in plan-marshall skill/agent/command markdown — violates the project policy that temporary files must live under `.plan/temp/` | Comment lines (`#`) and inline-code spans are exempt; only `bash`/`sh`-fenced blocks are scanned | None — replace with a `Write` tool call targeting `.plan/temp/{plan_id}-<name>` or pass the value through a TOON field |
| `bash-fence-inline-code-exemption` | Detect analyzer modules that scan inside a bash/sh fence (define `_BASH_FENCE_INFO_STRINGS`) while also carrying a markdown inline-code exemption (`_INLINE_CODE_RE` / `_inline_code_spans`) — the two are mutually exclusive because inside a bash fence backticks are command substitution, not markdown inline-code | This analyzer's own source names both marker families and is whitelisted by self-reference; files with only one marker family are compliant | None — remove the inline-code exemption helper from the bash-fence analyzer |

### bash-chain-shapes-in-skills

**Rule ID**: `bash-chain-shapes-in-skills`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_bash_chain_shapes_in_skills.py`

**Scope**: All `*.md` files under `marketplace/bundles/plan-marshall/{skills,agents,commands}/`.

**Intent**: Enforce the dev-agent-behavior-rules "Bash: one command per call" hard rule at the skill-documentation layer. A `&&`, `;`, or trailing `&` in a workflow doc gets interpreted by subagents that copy the snippet into a Bash call literally — the host platform's permission UI then either pops a security prompt or rejects the dispatch outright. The rule prevents regressions of the class of violation documented by the originating source (compound-Bash + tmp-redirect pattern that triggered a 25-minute permission-prompt pause).

**Detection logic**: Scans every line of fenced `bash` or `sh` blocks in every in-scope markdown file. Each occurrence of `&&`, `;`, or a trailing `&` (not preceded by `\`) on a non-comment line is a candidate finding, unless it falls into one of the exempt contexts below.

**Permitted contexts**:
1. **Comment lines** — Lines whose first non-whitespace character is `#` are treated as shell comments and skipped.
2. **Inline-code span** — A compound operator inside a backtick span (`` `…` ``). Token references are not runnable commands.
3. **Lines outside bash/sh fenced blocks** — Only lines inside fenced blocks whose info-string is `bash` or `sh` are scanned. Prose, Python fences, and so on are not checked.

**Recommended fix**: Split the compound command into two or more separate Bash tool calls. Each Bash call must contain exactly one command.

**Suppression mechanism**: None — convert to separate Bash calls. If the occurrence is genuinely documentary (a standards doc naming the forbidden pattern), wrap it in an inline-code span (`` `…` ``) or a `markdown`/`text` fence so the structural exemption applies.

---

### tmp-redirect-in-skills

**Rule ID**: `tmp-redirect-in-skills`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_tmp_redirect_in_skills.py`

**Scope**: All `*.md` files under `marketplace/bundles/plan-marshall/{skills,agents,commands}/`.

**Intent**: Enforce the project policy that all temporary files must live under `.plan/temp/` (covered by `Write(.plan/**)` permission, which avoids permission prompts and ensures the file tree is self-consistent). A `> /tmp/` redirect in a workflow doc signals that the subagent will write a temp file outside the pre-approved `.plan/temp/` tree, which either triggers a permission prompt or leaves an unreachable artefact. The rule also catches the compound-violation pattern (redirect + chain) documented by the originating source, where the `/tmp/` write was paired with a `; grep` chain on the same line.

**Detection logic**: Scans every line of fenced `bash` or `sh` blocks in every in-scope markdown file. Each occurrence of `>` or `>>` followed (optionally with whitespace) by `/tmp/` or `/var/tmp/` on a non-comment line is a candidate finding, unless it falls into one of the exempt contexts below.

**Permitted contexts**:
1. **Comment lines** — Lines whose first non-whitespace character is `#` are treated as shell comments and skipped.
2. **Inline-code span** — A redirect inside a backtick span (`` `…` ``). Token references are not runnable commands.
3. **Lines outside bash/sh fenced blocks** — Only lines inside fenced blocks whose info-string is `bash` or `sh` are scanned.

**Recommended fix**: Replace the `/tmp/` write with a `Write` tool call targeting `.plan/temp/{plan_id}-<descriptive-name>` (the `.plan/temp/` prefix is covered by the `Write(.plan/**)` pre-approved permission). Alternatively, if the value is small, pass it through a TOON field in the previous command's stdout instead of writing it to a file.

**Suppression mechanism**: None — fix the redirect target. If the occurrence is genuinely documentary (a standards doc naming the forbidden pattern), wrap it in an inline-code span or a `markdown`/`text` fence.

---

### bash-fence-inline-code-exemption

**Rule ID**: `bash-fence-inline-code-exemption`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_bash_fence_inline_code_exemption.py`

**Scope**: All `*.py` files under `marketplace/bundles/**/scripts/`.

**Intent**: Reintroduction guard. A plugin-doctor analyzer that scopes its scan to `bash`/`sh` fenced blocks (it defines a `_BASH_FENCE_INFO_STRINGS` marker) must NOT also carry the markdown-prose inline-code exemption (an `_INLINE_CODE_RE` or `_inline_code_spans` helper). Inside a bash fence a backtick span denotes command substitution, not a markdown inline-code span, so exempting "inline-code" inside a bash-fence scanner silently skips real command-substitution shapes — the exact mismatch that PR #474 removed from the bash-fence analyzers. This rule prevents the exemption from creeping back in.

**Detection logic**: For every `*.py` under `marketplace/bundles/**/scripts/`, the analyzer checks literal-token co-presence: `_BASH_FENCE_INFO_STRINGS` AND (`_INLINE_CODE_RE` OR `_inline_code_spans`). When both are present the file is flagged with the 1-based line of the first inline-code marker. Files with only one of the two marker families are compliant — prose scanners define only the inline-code helper (exemption is correct there); bash-fence scanners define only the fence-info-strings marker.

**Permitted contexts**:
1. **Self-reference** — This analyzer's own source names both marker families in its docstring and detection constants; it is whitelisted by a path-component-anchored match on its own filename.
2. **Single-marker files** — Files defining only one marker family are correct by construction and produce no finding.

**Recommended fix**: Remove the inline-code exemption helper (`_INLINE_CODE_RE` / `_inline_code_spans`) from the bash-fence analyzer. The bash-fence analyzer's only structural filters are "skip non-bash/sh fences" and "skip `#`-comment lines".

**Suppression mechanism**: None — remove the inline-code exemption helper from the bash-fence analyzer.

---

## Rule Pack: Workflow-doc TOON error-field invariant

**Activation**: Unconditionally active in `doctor-marketplace.py analyze` mode AND included in `quality-gate`. Unlike the bash chain-shape pack, the marketplace tree carries zero residual findings (the normalization sweep that established the canonical `error:` discriminator eliminated every fenced-TOON `error_type` key), so the rule enforces at quality-gate level on day one.

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `WORKFLOW_DOC_TOON_ERROR_FIELD` | Detect the non-canonical `error_type` key inside fenced ` ```toon ` workflow/agent error blocks in plan-marshall skill/agent/command markdown — the canonical error-envelope discriminator field is `error` | Detection scope is fenced ` ```toon ` blocks only; the key must be at the start of a TOON line (after leading whitespace). Inline `{status: error, error_type: ...}` brace shorthands, prose `error_type:` references outside any fence, and `error_type` keys inside non-`toon` fences are out of scope by design | None — rename the key to `error`; for a two-key block carrying both a category and a human-readable message, demote the message to `display_detail` |

### WORKFLOW_DOC_TOON_ERROR_FIELD

**Rule ID**: `WORKFLOW_DOC_TOON_ERROR_FIELD`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_workflow_doc_toon_error_field.py`

**Scope**: All `*.md` files under `marketplace/bundles/plan-marshall/{skills,agents,commands}/`.

**Intent**: Enforce the canonical error-envelope contract established at `plan-marshall/skills/plan-marshall/workflow/planning.md`, where an agent/workflow error TOON block uses `error:` as the category discriminator (with the human-readable message carried by `display_detail:`). Some workflow and agent docs drifted to `error_type:` for the discriminator. Because the orchestrator and the execution-context dispatcher branch on the field name they read out of the TOON block, the drifted key silently desynchronises the read-side match. This rule prevents the drift class from recurring after the normalization sweep.

**Detection logic**: Builds a fence map of every fenced block whose info-string is `toon`. Within each fenced TOON block, flags any line whose TOON key is `error_type` — both the colon-style (`error_type:`) and the tab-style (`error_type\t`) forms, since TOON blocks may use either key/value separator. The key must appear at the start of a TOON line (after leading whitespace); anchoring at the line start is what excludes inline brace shorthands.

**Permitted contexts**:
1. **Inline brace shorthands** — `{status: error, error_type: ...}` table shorthands are not flagged; the key is embedded mid-line in a brace expression, not at the start of a TOON line.
2. **Prose references** — `error_type:` mentions in narrative or log-message text live outside any `toon` fence and are not scanned.
3. **Non-`toon` fences** — `error_type` keys inside a `python`, `json`, or other non-`toon` fence are not workflow/agent error TOON blocks and are not flagged.

**Recommended fix**: Rename the `error_type` key to `error`. For a two-key block carrying BOTH a category discriminator AND a human-readable message, rename the discriminator to `error` and demote the message line to `display_detail` (matching the canonical `error:` + `display_detail:` envelope shape).

**Suppression mechanism**: None — rename the key. If the occurrence is genuinely documentary (a doc naming the forbidden pattern), move it outside the `toon` fence (e.g. into prose or a `text` fence) so the structural exemption applies.

---

## Rule Pack: Script-call drift

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `script-call-drift` | Detect drift between documented `python3 .plan/execute-script.py {notation} {verb}` invocations in skill markdown and the live argparse interface published by the target script's `--help` output | The analyzer probes `--help` per process and caches results. Single-action scripts (no subparsers) skip verb checking. Placeholder tokens (`{value}`, `{plan_id}`) are skipped. Universal flags (`--help`, `--audit-plan-id`) are exempt | None — fix the skill prose to match the script's published `--help` interface, or correct the script's argparse declaration |

### script-call-drift

**Rule ID**: `script-call-drift`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_script_call_drift.py`

**Scope**: All `*.md` files under `marketplace/bundles/**/skills/**`.

**Intent**: Replace the deleted runtime SUBCOMMANDS pre-flight validator with a dev-time drift detector. The runtime executor is now a dumb dispatcher; drift between documented invocations and the script's actual argparse interface is caught here, before the prose ships. The rule consumes argparse's published interface (`--help` text) rather than parsing the script source via AST — `--help` is the canonical interface, and AST walking proved fragile against argparse's dynamic shapes.

**Detection logic**:
1. Regex-match `python3 .plan/execute-script.py {notation} [verb] [flags...]` invocations in skill markdown.
2. For each unique `notation`, invoke `python3 .plan/execute-script.py {notation} --help` (subprocess) and parse the `{choice1, choice2, ...}` subcommand-choices block from the usage line.
3. For each `(notation, verb)` referenced in prose, invoke `python3 .plan/execute-script.py {notation} {verb} --help` and parse declared `--flag` names from argparse's options block.
4. Emit `verb_not_in_subcommand_list` when a documented verb is absent from the choices set. Emit `flag_not_in_options` when a documented `--flag` is absent from the options set.

**Caching**: `--help` text is cached per process — one subprocess per unique notation, one per unique `(notation, verb)` pair.

**Activation**: Opt-in via `--rules script_call_drift` on the `analyze` subcommand. NOT included in the unconditional `quality-gate` set — the subprocess overhead is too high for an unattended build gate. Invoke explicitly for drift sweeps after large skill-prose changes.

**Rationale**: The pre-flight runtime validator (removed in plan `fix-generate-executor-ast-subcommands`) embedded a stale SUBCOMMANDS allowlist at executor-generation time and rejected valid calls when the allowlist drifted. The new architecture moves drift detection to dev time: the doctor consumes the same argparse interface the runtime would, but it runs against the latest source on every invocation rather than against a snapshot embedded in the executor. The post-hoc complement (plan-retrospective `script-failure-analysis` pass) mines `script-execution.log` for argparse rejections to catch any drift the doctor missed at edit time.

**Suppression mechanism**: None — fix the prose or the argparse declaration to converge.

---

## Rule Pack: Lesson-ID prose hygiene

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `no-lesson-id-in-skill-prose` | Forbid narrative lesson-ID citations in skill prose — strip the ID and trivia, keep the rule content. Scans `*.md` AND `*.py` (comments, docstrings, string literals) | Allowlisted skill paths apply to both file classes. For markdown only: YAML frontmatter, fenced code blocks, `Source:` provenance lines, and bare inline-code spans (without a prose "lesson" prefix). For Python these markdown-only exemptions do NOT apply | Inline marker `<!-- doctor-ignore: lesson-id-prose -->` (same line or immediately preceding line) suppresses the finding on the marked line only |
| `no-historical-prose-in-skills` | Forbid historical/transitional narrative in skill prose — driving-lesson prefixes, back-references, earlier-proposal descriptions, seed-failure citations, plan-authorship annotations, guard-introduction prose | Seven allowlisted file paths; YAML frontmatter, fenced code blocks, `Source:` provenance lines, and inline-code spans are exempt per-line | Inline marker `<!-- doctor-ignore: historical-prose -->` (same line or immediately preceding line) suppresses the finding on the marked line only |

### no-lesson-id-in-skill-prose

**Rule ID**: `no-lesson-id-in-skill-prose`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_lesson_id_in_skill_prose.py`

**Scope**: Three trees, two file classes:

- `*.md` and `*.py` under `marketplace/bundles/*/{skills,agents,commands}/**`.
- `*.md` and `*.py` under the project-local `.claude/skills/**` tree (resolved relative to the marketplace bundles root). This tree has no allowlisted members — it is scanned in full.

For `.py` sources the rule scans comments, docstrings, and string literals — the contexts where narrative lesson-ID citations accumulate in scripts.

**Intent**: Strip narrative lesson-ID citations and recurrence trivia from skill prose so the surface documents present-tense rules rather than the historical incidents that motivated them. The rule recognises two lesson-ID format families — `YYYY-MM-DD-NNN` and `YYYY-MM-DD-HH-NNN` — and the prose-prefixed forms `lesson XXX` and `lesson-XXX`. In markdown it also catches the backtick-wrapped form `` lesson `YYYY-...` `` where "lesson" is prose context outside the backtick — this is a narrative citation regardless of the backtick, since the word "lesson" establishes the reader-navigation intent.

**Detection logic**: Two-pass scan per line. Pass 1 detects non-backtick prose forms using the main regex; in markdown it skips bare IDs inside inline-code spans, while in Python backticks carry no inline-code meaning so the ID is flagged. Pass 2 detects the `` lesson `YYYY-...` `` backtick-prefixed form using a dedicated regex — this Pass runs for markdown only (in Python the bare ID was already caught by Pass 1, so Pass 2 would double-count). In markdown this form is never exempt, because "lesson" outside the backtick is always prose context.

**Allowlist** (file-level skip — the entire file is exempt because it operates ON lessons as domain content; applies to both `*.md` and `*.py` under `marketplace/bundles/`):

- `marketplace/bundles/plan-marshall/skills/manage-lessons/**`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-*.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/lessons-*.md`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**`
- `marketplace/bundles/plan-marshall/skills/plan-doctor/**`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md` — the canonical citation home for plugin-doctor rules.
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md` — cites lesson IDs as authoritative design references.

The allowlist is unchanged by the widened scope — the same exempt prefixes apply across both file classes and both trees. (The project-local `.claude/skills/**` tree has no allowlisted members.)

**Per-line structural exemptions** — **markdown only** (skip the match, not the file). These do NOT apply to `.py` sources, where comments, docstrings, and string literals are deliberately in scope:

1. **YAML frontmatter** — between the leading `---` fences at the start of a markdown file.
2. **Fenced code block** — any line inside a ``` ``` ``` fence regardless of info-string.
3. **`Source:` line** — provenance citation marker (e.g., `Source: lesson-XXX`).
4. **Bare inline-code span** — a lesson-ID inside backticks WITHOUT a prose `lesson` prefix immediately before the span. Token references in code spans are not narrative prose. The `` lesson `YYYY-...` `` form is NOT exempt: "lesson" is prose context and signals a narrative citation.

**Suppression mechanism**: Place `<!-- doctor-ignore: lesson-id-prose -->` on the same line as the match, or on the immediately preceding line, to suppress the finding on the marked line only. Use sparingly — the marker is for genuinely structural citations whose context the analyzer cannot detect (extremely rare; nearly every legitimate citation already qualifies as `Source:` or inline-code).

**Recommended fix**: Locate the line cited by the finding. If the lesson-ID + trivia is parenthetical or sits in its own sentence whose only payload is the citation, remove the entire sentence/parenthetical. Otherwise, strip the lesson-ID, the bracketed citation form (`(lesson XXX)`, `lesson-XXX`, `see lesson XXX`), and the recurrence-trivia phrases while preserving the surrounding rule/decision content. The rule remains; the citation goes.

---

## Rule Pack: Allowed-tools-body drift

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `allowed-tools-body-drift` | Flag a component whose body invokes a tool absent from its declared, non-empty `allowed-tools`/`tools` frontmatter list — a consistency check, NOT a schema prohibition | Components that omit `allowed-tools`/`tools` entirely are NOT flagged (the "inherit all tools" default; the retired `unsupported-skill-tools-field` rule stays deleted). Only directive-shaped invocations (`Read:`, `- Skill:`, `Tool: Bash`) count; fenced code blocks are exempt; declared-but-unused tools are NOT flagged | Inline marker `<!-- doctor-ignore: allowed-tools-drift -->` (same line or immediately preceding line) suppresses the finding on the marked line only |

### allowed-tools-body-drift

**Rule ID**: `allowed-tools-body-drift`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_allowed_tools_drift.py`

**Scope**: All `*.md` under two trees:

- `marketplace/bundles/*/{skills,agents,commands}/**`.
- the project-local `.claude/skills/**` tree (resolved relative to the marketplace bundles root).

**Intent**: Detect a one-directional *drift* between a component's declared tool surface and the tools its workflow body actually invokes — a tool the body invokes that the frontmatter omits. This is a self-consistency check, not a schema rule. Skills MAY declare `allowed-tools` per the Claude Code skills schema but are not required to; a missing declaration is the "inherit all tools" default and is never flagged. The rule fires only where a tool is BOTH invoked in the body AND the frontmatter declares a non-empty list that omits it.

**Detection logic**: Parse the declared tool set from the `allowed-tools` (or `tools`) frontmatter using the shared `parse_declared_tools` parser (reused from `_analyze_coverage.py` so the two analyzers stay consistent). When the declared list is empty/absent, emit nothing. Otherwise scan the body for tool invocations — a known tool name (`Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`, `AskUserQuestion`, `Skill`, `Task`, `WebFetch`) appearing as a directive at a line start (`Read:`, `- Skill:`) or in a `Tool: {ToolName}` directive. Emit one finding per invoked tool absent from the declared set.

**Per-line structural exemptions**:

1. **Fenced code block** — body lines inside ``` ``` ``` fences (any info-string) are exempt: a tool name inside an example command block is not a live invocation.
2. **No-frontmatter / empty declaration** — a component without an `allowed-tools`/`tools` declaration, or with an empty one, is exempt entirely (the "inherit all tools" default).

**Suppression mechanism**: Place `<!-- doctor-ignore: allowed-tools-drift -->` on the same line as the match, or on the immediately preceding line, to suppress the finding on the marked line only.

**Recommended fix**: Reconcile the declaration with usage — either add the invoked tool to the `allowed-tools`/`tools` frontmatter list, or remove the body invocation if the tool genuinely should not be used. The rule never prescribes which direction; it flags the inconsistency.

---

## Rule Pack: Skill self-declared-rule self-compliance

| Rule ID | Intent | False-positive policy | Suppression |
|---------|--------|-----------------------|-------------|
| `skill-self-declared-rule-violation` | Flag a `SKILL.md` that declares a flat-numbering / no-sub-numbering rule in its own body yet uses sub-numbered (`1a`/`3a`/`5a`-style) step headings in that same body — a self-consistency check, NOT a global numbering ban | Self-referential: a `SKILL.md` that uses sub-numbering WITHOUT declaring such a rule is NOT flagged. Only `SKILL.md` is scanned. Heading-shaped lines inside YAML frontmatter and fenced code blocks are exempt. Scoped narrowly to the one self-rule class that is regex-checkable (numbering discipline); non-regex-checkable self-rule classes are out of scope by design | Inline marker `<!-- doctor-ignore: self-declared-rule -->` (same line or immediately preceding line) suppresses the finding on the marked line only |

### skill-self-declared-rule-violation

**Rule ID**: `skill-self-declared-rule-violation`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_self_declared_rule_compliance.py`

**Scope**: All `SKILL.md` under two trees:

- `marketplace/bundles/*/{skills,agents,commands}/**`.
- the project-local `.claude/skills/**` tree (resolved relative to the marketplace bundles root).

Only `SKILL.md` is scanned — the numbering-discipline rule is a property of a skill's workflow document, not of every markdown file.

**Intent**: Detect a self-referential defect: a `SKILL.md` that *authors* a numbering-discipline rule (a body passage prohibiting sub-numbering / mandating flat step numbering) must obey that rule in its own step headings. The check is self-referential, not a global numbering ban — sub-numbering is permitted in the general case, and a file that uses it without declaring a flat-numbering rule is never flagged. Scope is deliberately narrowed to the numbering-discipline class — the one self-rule class that is regex-checkable; non-regex-checkable self-rule classes (tone, structure, naming) have no deterministic surfacer and are out of scope.

**Detection logic**: First test whether the file declares a numbering-discipline rule — a body passage (outside YAML frontmatter and fenced code blocks) matching any of the declaration phrases (`flat-numbering`, `flat numbering`, `no sub-numbering`, `no-sub-numbering`, `prohibit sub-numbering`, `without sub-numbering`, etc.). When such a declaration is present, scan the file's own step headings for the banned sub-numbered shape: a markdown heading (`##` .. `####`) whose leading label is `Step Nx` or a bare `Nx`, where `N` is a digit immediately followed by a lowercase letter (e.g. `### Step 1a`, `#### 3b`). Emit one finding per self-violating heading, naming both the declared rule and the offending heading.

**Per-line structural exemptions**:

1. **YAML frontmatter** — heading-shaped lines inside the leading `---` fences are not body content and are skipped for both declaration and violation detection.
2. **Fenced code block** — lines inside ``` ``` ``` fences are exempt: a heading-shaped line inside an example block is not a live heading, and a declaration phrase inside an example block is not an authored rule.

**Suppression mechanism**: Place `<!-- doctor-ignore: self-declared-rule -->` on the same line as the violating heading, or on the immediately preceding line, to suppress the finding on the marked line only.

**Recommended fix**: Renumber the offending headings to a flat sequence so the document obeys the numbering rule it declares — or, if the declared rule no longer reflects intent, revise the declaration. The rule flags the inconsistency between the authored rule and the document's own headings.

---

### no-historical-prose-in-skills

**Rule ID**: `no-historical-prose-in-skills`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_historical_prose_in_skills.py`

**Scope**: All `*.md` files under `marketplace/bundles/*/{skills,agents,commands}/**`.

**Intent**: Strip historical and transitional narrative from skill prose so skill documents describe current requirements rather than the events that motivated them. Seven pattern families are detected:

1. **driving_lesson_prefix** — `Driving lesson:` used as a bullet or inline annotation.
2. **back_reference_prefix** — `Back-reference:` or `Back-reference—` citing the originating plan/lesson/PR.
3. **earlier_proposal** — "An earlier proposal", "the earlier approach", "earlier version", etc.
4. **historical_activation** — "activated end-to-end by lesson", "introduced by plan", etc.
5. **seed_failure_observation** — "seed failure", "seed observation", "seed defect", "seed gap".
6. **plan_task_authorship** — "added in TASK-NNN of plan", "added by deliverable N of this plan", etc.
7. **guard_introduction** — "guard introduced in", "rule introduced in", "validator introduced in", etc.

**Allowlist** (file-level skip — historical context is intrinsic to the file's purpose):

- `marketplace/bundles/plan-marshall/skills/manage-lessons/**`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-*.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/lessons-*.md`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md`
- `marketplace/bundles/plan-marshall/skills/plan-doctor/standards/**`

**Per-line structural exemptions**: YAML frontmatter, fenced code blocks, `Source:` provenance lines, inline-code spans.

**Suppression mechanism**: Place `<!-- doctor-ignore: historical-prose -->` on the same line as the match, or on the immediately preceding line.

**Recommended fix**: Rewrite the sentence as a present-tense rule without the historical context. If the entire sentence's value is "this is why the rule exists", remove it — the rule statement itself is the durable artifact. If a brief rationale is genuinely needed, state the principle rather than citing the incident: replace "Driving lesson: `2026-04-30-23-001` (TASK-9 scope expanded silently)" with "Check sibling directories when scope changes touch a shared symbol."

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

**Intent**: Production Python scripts must not embed the `.plan/plans/` literal path. The canonical plan-directory helper is `get_plan_dir(plan_id)` from `tools-file-ops:file_ops`, which resolves to `<repo>/.plan/local/plans/{plan_id}`. Any script that joins `plans/{plan_id}` against `cwd/.plan` directly resolves to the wrong path and produces a "ghost" `.plan/plans/{plan_id}/` tree at the repo root on every invocation. The originating failure mode is documented under the ghost-plan-dir bug, where two CI-completion scripts (`ci_complete_precondition.py` and `manage-ci-artifacts.py`) shipped hand-rolled `_resolve_plan_base_dir()` helpers that drifted from the canonical layout.

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

### notation-staleness

**Rule ID**: `notation-staleness`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_notation_staleness.py`

**Scope**: Per-skill — `SKILL.md` plus every `*.md` under `standards/`, `references/`, `workflow/`, `recipes/`, plus every `*.py` under `scripts/`. Wired into `_doctor_analysis.py` unconditionally active (not gated on `active_rules`), mirroring the `refine-contract-violation` integration.

**Intent**: Flag three-part executor notations (`{bundle}:{skill}:{script}`) whose third segment has no matching `{script}.py` file under the resolved `bundles/{bundle}/skills/{skill}/scripts/` directory. `generate_executor` derives a script's public notation from its filename, so renaming an entrypoint script silently changes the notation — callers that still use the old third segment resolve to `Unknown notation`.

**Detection**: Pure static analysis — regex extraction of three-segment notations from each line, then a filesystem check that `{script}.py` exists under the resolved scripts directory. Notations whose target `scripts/` directory does not exist are skipped (they are not executor notations).

**Canonical hint**: When the literal third segment has no matching file but the hyphen/underscore-flipped form does, the finding carries `details.canonical_hint` naming the corrected notation so the fix can be applied mechanically.

**False-positive policy**: Conservative — the analyzer only evaluates notations whose `bundles/{bundle}/skills/{skill}/scripts/` directory exists, filtering out incidental colon-separated tokens (URLs, timestamps, prose).

**Recommended fix**: Update the notation's third segment to match the actual script filename (typically the hyphen/underscore-flipped form named in `details.canonical_hint`).

**Suppression mechanism**: None — a non-resolving notation is a hard breakage and must be fixed.

---

## Rule Pack: Reference-resolution

Five rules that catch gaps between what the marketplace *declares* and what is *discoverable on disk*. Each gap resolves to a dead reference at runtime: a missing component, an unresolvable `Skill:` directive, a drifted notation segment, an undeclared component, or an undiscoverable recipe. **Activation**: unconditionally active under `doctor-marketplace.py analyze` (each analyzer is a cheap json / regex / filesystem pass over the bundle tree). NOT included in `quality-gate`. `notation-bundle-skill-drift` rides the existing per-skill `notation-staleness` integration in `_doctor_analysis.py`; the other four are marketplace-wide passes wired into `cmd_analyze`.

### declared-component-vs-disk

**Rule ID**: `declared-component-vs-disk`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_declared_vs_disk.py`

**Scope**: every bundle's `.claude-plugin/plugin.json` under the marketplace tree.

**Intent**: Forward manifest-integrity check. For each component declared in a bundle's `plugin.json` (`agents` / `commands` / `skills` arrays), the corresponding file must exist on disk — `./skills/{skill}` resolves to `{bundle}/skills/{skill}/SKILL.md`, `./agents/{agent}.md` and `./commands/{command}.md` resolve to the named markdown file. A declared entry whose target file is missing is a dead manifest reference: the plugin loader fails to load the component.

**Detection**: Pure static analysis — `json.loads` each `plugin.json`, resolve each entry to its on-disk anchor, and `is_file()`-check it. Malformed manifests are skipped silently (the `invalid-yaml` / structural rules cover them).

**Recommended fix**: Either restore the missing file or remove the stale entry from `plugin.json`. Run `/marshall-steward` after bundle changes.

**Suppression mechanism**: None — a declared-but-missing component is a hard breakage.

---

### plugin-json-orphan-component

**Rule ID**: `plugin-json-orphan-component`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_plugin_json.py`

**Scope**: every bundle's `skills/*/SKILL.md`, `agents/*.md`, and `commands/*.md` under the marketplace tree.

**Intent**: Reverse manifest-integrity check (the bidirectional complement of `declared-component-vs-disk`). An on-disk component that ships but is NOT declared in its bundle's `plugin.json` is invisible to the plugin loader. The check honours the marketplace registration convention: user-invocable skills (`user-invocable: true`) MUST register, so an undeclared one is a real orphan; script-only / context-loaded / extension-implementor skills (`user-invocable: false`) are legitimately unregistered and therefore exempt. Agents and commands always register, so any undeclared `agents/*.md` / `commands/*.md` is an orphan with no frontmatter exemption.

**Detection**: Pure static analysis — `json.loads` each `plugin.json` into the declared set (normalising the leading `./`), enumerate on-disk components, and report each one absent from the declared set. SKILL.md orphans are filtered to `user-invocable: true` via a frontmatter scan.

**Severity**: `warning` (advisory) — a missing registration degrades discoverability rather than breaking a resolving reference.

**Recommended fix**: Add the on-disk component's `./skills/{skill}` / `./agents/{file}.md` / `./commands/{file}.md` entry to its bundle's `plugin.json`. If a skill is deliberately script-only, set `user-invocable: false` in its frontmatter so the rule exempts it.

**Suppression mechanism**: Set `user-invocable: false` on a deliberately-unregistered skill (no exemption channel for agents / commands).

---

### skill-notation-unresolved

**Rule ID**: `skill-notation-unresolved`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_skill_notation.py`

**Scope**: every `*.md` under `marketplace/bundles/*/{skills,agents,commands}/`.

**Intent**: A `Skill: {bundle}:{skill}` directive whose target skill directory `bundles/{bundle}/skills/{skill}/` does not exist is a dead reference — the dispatcher cannot load it, and the workflow that depends on it silently misfires. The rule validates the two-segment bundle-prefixed directive form; the bare single-segment form and project-local `.claude/skills` references are out of scope.

**Detection**: Pure static analysis — line-anchored regex extraction of `Skill: {bundle}:{skill}` tokens, then a filesystem check that the skill directory resolves. To avoid false positives on incidental colon-joined tokens, the rule only evaluates a directive whose `{bundle}` is a real bundle on disk (carries a `.claude-plugin/plugin.json`).

**Recommended fix**: Correct the directive's bundle / skill segment to a skill directory that exists.

**Suppression mechanism**: None — an unresolvable `Skill:` directive is a hard breakage.

---

### notation-bundle-skill-drift

**Rule ID**: `notation-bundle-skill-drift`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_notation_staleness.py` (emitted alongside `notation-staleness` from the same scan).

**Scope**: per-skill — `SKILL.md` plus every `*.md` under `standards/`, `references/`, `workflow/`, `recipes/`, plus every `*.py` under `scripts/` (same surface as `notation-staleness`).

**Intent**: Where `notation-staleness` validates only the third (script) segment of a `{bundle}:{skill}:{script}` notation, this rule validates the FIRST and SECOND segments — the `{bundle}` directory and the `{skill}` directory must resolve on disk. The drift is only evaluated for notations anchored to the executor invocation prefix (`python3 .plan/execute-script.py {notation}`), because a bare three-segment token whose bundle / skill is unknown is indistinguishable from an incidental colon-joined token (URL, timestamp, prose). Anchoring on the executor prefix removes that ambiguity.

**Detection**: Pure static analysis — a second regex (`execute-script\.py\s+{notation}`) extracts executor-anchored notations; the bundle segment is checked for a real `bundles/{bundle}/.claude-plugin/plugin.json`, then the skill segment for a real `bundles/{bundle}/skills/{skill}/` directory. The first failing segment is reported.

**Canonical hint**: `details.canonical_hint` names which segment (bundle or skill) failed to resolve so the fix can be applied mechanically.

**Recommended fix**: Correct the failing notation segment (`details.reason` distinguishes `bundle_dir_missing` from `skill_dir_missing`) to a real bundle / skill name.

**Suppression mechanism**: None — a non-resolving notation is a hard breakage.

---

### recipe-missing-implements

**Rule ID**: `recipe-missing-implements`

**Analyzer**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_frontmatter.py`

**Scope**: every `recipe-*` skill `SKILL.md` under BOTH `marketplace/bundles/*/skills/recipe-*` AND the project-local `.claude/skills/recipe-*` tree.

**Intent**: Recipe skills are recipe-extension-point implementors; the `extension-api` discovery layer resolves them via the `implements:` frontmatter field. A `recipe-*` skill whose `SKILL.md` omits `implements:` (or declares a divergent value) is invisible to recipe discovery and cannot be offered via `/plan-marshall action=recipe`. The canonical value is `implements: plan-marshall:extension-api/standards/ext-point-recipe` (see `plan-marshall:extension-api/standards/ext-point-recipe.md` § Implementor Frontmatter).

**Detection**: Pure static analysis — enumerate every `recipe-*` skill directory across both trees, parse the leading frontmatter, and compare the `implements:` value to the required notation. `details.reason` distinguishes `implements_missing` from `implements_divergent`.

**Recommended fix**: Add (or correct) `implements: plan-marshall:extension-api/standards/ext-point-recipe` in the recipe skill's `SKILL.md` frontmatter.

**Suppression mechanism**: None — declare the canonical `implements:` value.

---

## Zero-match coverage (test-layer, not a runtime rule)

The zero-match invariant is enforced at the **test layer**, not by a runtime analyzer. There is no `zero-match-rule` finding emitted by any `_analyze_*.py` module, and the invariant is not part of the `analyze` / `quality-gate` registered rule set. The check is the meta-test `test_zero_match_suite_coverage.py`.

**Invariant**: every audit-tracked rule ID the analyzers emit must fire at least once during the plugin-doctor analyzer test suite:

```
registered_rule_ids(real_tree) − fired_in_suite − EXEMPT_RULE_IDS == ∅
```

**Where the pieces live**: `registered_rule_ids(root)` and the `fired_in_suite` derivation (each registered rule run against its positive fixture, plus the cross-file rules) are in the plugin-doctor tests' `_fixtures.py`; `EXEMPT_RULE_IDS` — the shrunken, per-entry-justified frozenset of rules that structurally cannot fire on a static positive fixture — is in `test_zero_match_suite_coverage.py`. A companion test (`test_exempt_rule_ids_are_all_registered`) asserts `EXEMPT_RULE_IDS` is a subset of the real-tree registered IDs, so a stale or misspelled exemption fails the build.

**Detection logic**: The meta-test statically derives the registered rule-ID population from the in-tree `_analyze_*.py` modules (the same extractor `test_rule_provenance_table.py` uses — `'type'`/`'rule_id'` literals plus `RULE_*`/`FINDING_TYPE` constants filtered through the audit-tracked-rule-ID heuristic), unions the rule IDs each positive fixture emits when run over its own scratch tree, subtracts the exempt set, and asserts the residual is empty. The assertion message names every uncovered rule so the gap is unambiguous. Stdlib-only, fixtures written under the system temp root.

**Recommended fix for a coverage gap**: write a GENUINE positive unit test for the uncovered rule — materialize a minimal known-defect fixture and assert the analyzer emits the rule (real coverage, not a parallel corpus stub). Only when a rule structurally cannot fire on a static positive fixture, add it to `EXEMPT_RULE_IDS` with a per-entry justification comment. Coverage is proven from the test suite itself, over the full registered population minus the exempt set.

**Suppression mechanism**: None — a non-empty gap is a self-test failure resolved by writing the missing positive test or adding a justified exemption.

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
