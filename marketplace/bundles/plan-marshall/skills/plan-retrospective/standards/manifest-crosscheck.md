# Manifest Cross-Check Rules

Cross-check rules that compare the per-plan execution manifest (`execution.toon` written by `plan-marshall:manage-execution-manifest`) against the actual end-of-execute git diff. Each rule maps one-to-one to a row in the seven-rule manifest decision matrix and emits one finding per violation.

## Sources

- **Manifest** (`execution.toon`): produced by `manage-execution-manifest compose` during phase-3-outline. Captures `phase_5.early_terminate`, `phase_5.verification_steps`, `phase_6.steps`, plus the `rule_fired` field that names which decision matrix row applied (logged in `decision.log` rather than the manifest body itself).
- **Decision log** (`decision.log`): captures the rule that fired, with the `(plan-marshall:manage-execution-manifest:compose)` caller tag — load these alongside the manifest to present the WHY behind each WHAT.
- **End-of-execute diff** (`git diff {base}...HEAD --name-only`): the authoritative list of files touched between the plan's base commit and the head of the execute branch. Used to compare against manifest assumptions.

## Cross-Check Matrix

Each row is one rule. The script emits exactly one finding when the rule's expected outcome is contradicted by the actual diff.

### Rule M1: docs-only manifest implies docs-only diff

**Manifest signal**: `phase_5.verification_steps == []` AND `phase_5.early_terminate == false` (the docs-only and verification-no-files rules from the matrix produce this shape).

**Expected diff**: All file paths must match one of the docs-only patterns:
- `*.md`
- `*.adoc`
- Path contains `/references/` segment
- Path contains `/templates/` segment

**Finding (when violated)**: `severity=warning`, `code=docs_only_diff_violation`, `message="phase_5.verification_steps is empty but diff includes non-docs files: {culprits[:5]}"`, with full culprit list under `details.culprits`.

### Rule M2: early-terminate manifest implies empty implementation diff

**Manifest signal**: `phase_5.early_terminate == true`.

**Expected diff**: Empty (no source files touched). Lessons-learned and `.plan/` artifact updates are filtered out before evaluation because they are produced post-implementation by phase-6-finalize, not by the analysis itself.

**Finding (when violated)**: `severity=warning`, `code=early_terminate_diff_nonempty`, `message="phase_5.early_terminate=true but diff includes implementation files: {culprits[:5]}"`.

### Rule M3: tests-only verification implies tests-only diff

**Manifest signal**: `phase_5.verification_steps` denotes module-tests and nothing else (the `tests_only` rule from the matrix).

The comparison is made on NORMALIZED step names, not on the raw list. The composer emits every built-in verify step as a canonical-verify id — `default:verify:{canonical}`, boundary-normalized to the bare `verify:{canonical}` form — so `verification_steps` reads `['verify:module-tests']`, never `['module-tests']`. Normalization strips the optional `default:` prefix and then the `verify:` prefix, so `default:verify:module-tests`, `verify:module-tests`, and a bare `module-tests` (the form archived manifests carry) all denote `module-tests`. A rule comparing the raw list against an unprefixed name cannot fire on any manifest the composer produces.

**Expected diff**: All non-docs file paths must look like test files — path contains `/test/`, `/tests/`, or filename matches `test_*.py`, `*_test.py`, `*Test.java`, `*Spec.java`, `*.test.js`, `*.spec.js`.

**Finding (when violated)**: `severity=warning`, `code=tests_only_diff_violation`, `message="phase_5 manifest is tests-only but diff includes non-test source files: {culprits[:5]}"`.

### Rule M4: Phase 6 includes branch-cleanup implies branch present at base

This is a soft consistency check — the script does not query git for branch state. Instead it asserts that `phase_6.steps` containing `branch-cleanup` is paired with at least one source-shaped diff entry (so there is something to clean up). When `branch-cleanup` is present but the diff is empty, emit:

**Finding**: `severity=info`, `code=branch_cleanup_without_changes`, `message="phase_6.steps includes branch-cleanup but diff is empty — nothing to push/clean"`.

### Rule M5: Manifest version recognized

**Manifest signal**: `manifest_version` field present and equals the version known to this script.

**Finding (when violated)**: `severity=error`, `code=manifest_version_unknown`, `message="manifest_version={value} not recognized by check-manifest-consistency"`.

## Rules That Are Intentionally NOT Checked

- The two surgical-bug_fix / surgical-tech_debt rule rows from the matrix produce the same Phase 5 verification step set as the default row (`['verify:quality-gate', 'verify:module-tests']`). Cross-checking them against the diff would produce no actionable finding because both rule outcomes accept any non-empty source-code diff. The `rule_fired` value carried in the decision log is the only artifact that tells them apart, and that asymmetry is by design.
- The recipe rule produces a Phase 5 step list that is a subset of the default. Same reasoning applies.

## Diff Path Filtering Rules

Before evaluating any rule, the script drops the diff entries that are bookkeeping side-effects produced by phase-6-finalize rather than implementation work. **The classification is the build map's, not the script's** — `build.map` in marshal.json is the declared file-to-build oracle, and every `{glob, role, build_class}` entry says which kind of file a path is. The script consults it through the shared `_footprint_classification` module that `check-routing-decisions.py` also uses, so the two cannot disagree about the same path.

A path is dropped when it falls in one of exactly three categories:

- `runtime_state` — a path beginning with `.plan/` (plan state, lessons drafts, archive moves). This is the one prefix still decided in code, because `.plan/` is git-ignored and therefore appears in no build map: there is no oracle answer to defer to.
- `report` — the plan's own `quality-verification-report*.md` files.
- `config` — a path the **oracle** routes with role `config`.

Everything else is kept: `production` and `test` (the oracle's implementation roles), `documentation` (recognised by the generic `.md` / `.adoc` / `references/` / `templates/` file-suffix fact, whose declared owner is the change-footprint classifier — the build_map role vocabulary deliberately has no documentation role), and `unclassified`.

**`unclassified` is kept, and that is deliberate.** A path no declared route covers is one the oracle has no opinion about — a could-not-classify, not a classified-as-unimportant. Dropping it would put a private guess back in charge of the question, so it is retained and counted instead, which can only widen what a rule examines.

This replaces a private `('.plan/', '.claude/')` prefix tuple that contradicted the project's own build map: `build.map` routes the project-local skill tree (`.claude/skills/*.py` on the Claude target) as `production`, so the filter was discarding production source as bookkeeping and every downstream rule then evaluated the remainder.

Pure-deletion diff entries (e.g., a removed file) are kept because deletion is still implementation activity.

## Reporting a Reduced Input Set

Filtering happens before any rule sees the diff, so a rule can be evaluated against a small fraction of the supplied footprint and still emit a clean pass. That pass reads in every downstream summary exactly like a substantiated one. Two obligations close it, both applied after every evaluator so no rule can forget one:

- Every diff-fed check (`docs_only_diff`, `early_terminate_diff`, `tests_only_diff`, `branch_cleanup_changes`) that ran against a reduced input set carries the reduction in its message. `manifest_version_recognized` is exempt: it reads the manifest body alone, so no amount of filtering affects it.
- A check that would otherwise emit a bare clean `pass` while the **majority** of the supplied footprint was discarded (`files_filtered > files_kept`) takes the status `indeterminate` instead, and its message names the withheld verdict.

A `fail` is never downgraded — a violation found in the surviving fraction is still a violation, and a reduced input can only have hidden more. A `skip` is never downgraded either: the rule did not apply, which the filtering did not decide.

The `diff` block publishes the evidence: `filtered_by_category` (one count per category, always present even at zero), `oracle_available` (whether the build map answered at all), and `majority_discarded`.

## TOON Fragment Shape

The script emits this fragment for `compile-report` to render under the "Manifest Decisions" section:

```toon
aspect: manifest-decisions
status: success | skipped
plan_id: {plan_id}
manifest_present: true | false
manifest:
  manifest_version: 1
  phase_5:
    early_terminate: false
    verification_steps[*]: ['verify:quality-gate', 'verify:module-tests']
  phase_6:
    steps[*]: ['push', ...]
decision_log_entries[*]: ['(plan-marshall:manage-execution-manifest:compose) Rule default fired — ...']
diff:
  base: {base_ref or 'unknown'}
  files_total: N
  files_filtered: M
  files_kept: K
  filtered_by_category:
    runtime_state: N
    report: N
    production: N
    test: N
    config: N
    documentation: N
    unclassified: N
  oracle_available: true | false
  majority_discarded: true | false
checks[*]{name,status,message}:
  - manifest_version_recognized,pass,'manifest_version=1 recognized'
  - docs_only_diff,skip,'rule M1 not applicable — verification_steps non-empty or early_terminate=true'
  - early_terminate_diff,skip,'rule M2 not applicable — early_terminate=false'
  - tests_only_diff,skip,'rule M3 not applicable — verification_steps does not denote module-tests only'
  - branch_cleanup_changes,indeterminate,'... — VERDICT WITHHELD: M of N supplied paths were filtered as bookkeeping before evaluation'
findings[*]{severity,code,message,culprits}:
  - warning,docs_only_diff_violation,'...',['src/a.py']
summary:
  passed: N
  failed: N
  skipped: N
  indeterminate: N
  findings: N
```

`indeterminate` is a status distinct from both `skip` (the rule did not apply) and `pass` (the rule applied and was satisfied): it says the rule applied but saw too little of the supplied input for its verdict to mean anything. See [Reporting a Reduced Input Set](#reporting-a-reduced-input-set).

When `manifest_present == false`, the script emits `status: skipped` with an empty `checks` and `findings` list — the orchestrator should skip the aspect entirely in this case.

## LLM Interpretation Rules

- All findings emitted by this script MUST surface in the report under the "Manifest Decisions" section.
- The decision log entries pair WHAT (manifest) with WHY (rule that fired). Always render both.
- `manifest_version_unknown` is a hard error — it implies the manifest schema has drifted ahead of the cross-check engine. Surface as `error` and recommend updating the script.
- A clean run (all checks `pass` or `skip`, zero findings) is the expected outcome. The aspect's value comes from catching drift.
- An `indeterminate` check is **not** a clean result and MUST NOT be rendered as one. It reports that the rule saw only a minority of the supplied footprint, so it is surfaced with the reduction its message names — a withheld verdict, not a satisfied one.

## Cross-References

- `references/artifact-consistency.md` — peer aspect; `affected_files_exact_match` forwards to this matrix when a manifest exists.
- `plan-marshall:manage-execution-manifest` — the API that produces the manifest; see its `standards/decision-rules.md` for the authoritative rule definitions.
