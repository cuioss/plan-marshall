# Identifier Validation Audit

This document is the single source of truth for the canonical identifier-validator sweep across the marketplace. The validator foundation (regex constants, raising validators, `add_<id>_arg(parser)` builders, and the `parse_args_with_toon_errors()` helper) shipped via lesson-2026-04-28-12-001. The cross-bundle sweep that consumed those validators across 32 scripts in `plan-marshall`, `pm-dev-java`, and `pm-documents` landed via lesson-2026-04-29-08-003. Every entry below reflects the post-sweep state: which scripts were migrated, which were excluded and why, and the breaking-compat decisions that fell out of the audit. New scripts and new identifier-shaped flags MUST be reflected in both this document and the SKILL.md adoption table.

## Migrated Scripts (32)

Grouped by sweep wave. Each row records the script under sweep, its bundle, the in-scope identifier flags adopted via `add_<id>_arg(parser)` builders, the identifier-handling families covered (argparse-only / parse-then-rebuild / post-parse-normalize), and the corresponding test directory.

### Wave A — plan-marshall manage-* (16)

| Script | Bundle | In-scope flags adopted | Families covered | Test directory |
|--------|--------|------------------------|------------------|----------------|
| `manage-architecture/scripts/architecture.py` | plan-marshall | `--module`, `--name`, `--package`, `--domain` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-architecture/` |
| `manage-config/scripts/manage-config.py` | plan-marshall | `--plan-id`, `--field`, `--domain` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-config/` |
| `manage-execution-manifest/scripts/manage-execution-manifest.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/manage-execution-manifest/` |
| `manage-files/scripts/manage-files.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/manage-files/` |
| `manage-findings/scripts/manage-findings.py` | plan-marshall | `--plan-id`, `--component`, `--module`, `--hash-id` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-findings/` |
| `manage-lessons/scripts/manage-lessons.py` | plan-marshall | `--lesson-id` (action=append), `--component`, `--plan-id` | argparse-only, post-parse-normalize | `test/plan-marshall/manage-lessons/` |
| `manage-logging/scripts/manage-logging.py` | plan-marshall | `--plan-id`, `--phase` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-logging/` |
| `manage-memories/scripts/manage-memory.py` | plan-marshall | `--plan-id`, `--session-id` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-memories/` |
| `manage-metrics/scripts/manage_metrics.py` | plan-marshall | `--plan-id`, `--phase`, `--session-id` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-metrics/` |
| `manage-plan-documents/scripts/manage-plan-documents.py` | plan-marshall | `--plan-id` (+ dynamically-named identifier flags) | parse-then-rebuild, post-parse-normalize | `test/plan-marshall/manage-plan-documents/` |
| `manage-references/scripts/manage-references.py` | plan-marshall | `--plan-id`, `--field` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-references/` |
| `manage-run-config/scripts/run_config.py` | plan-marshall | `--plan-id`, `--field` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-run-config/` (skipped — no rejection-path tests added; flags exercised via shared validator suite) |
| `manage-solution-outline/scripts/manage-solution-outline.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/manage-solution-outline/` |
| `manage-status/scripts/manage_status.py` | plan-marshall | `--plan-id`, `--phase`, `--field` | argparse-only, parse-then-rebuild | `test/plan-marshall/manage-status/` |
| `manage-tasks/scripts/manage-tasks.py` | plan-marshall | `--plan-id`, `--task-number` (int-coerced post-validation), `--domain` | argparse-only, post-parse-normalize | `test/plan-marshall/manage-tasks/` |
| `manage-worktree/scripts/manage-worktree.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/manage-worktree/` |

### Wave B — plan-marshall workflow / tools / skill-namespaced (14)

| Script | Bundle | In-scope flags adopted | Families covered | Test directory |
|--------|--------|------------------------|------------------|----------------|
| `extension-api/scripts/extension_discovery.py` | plan-marshall | (audit-only — no in-scope flags after re-classification; uses `--bundle`/`--path`/`--refresh`) | n/a | `test/plan-marshall/extension-api/` |
| `plan-marshall/scripts/manage_session.py` | plan-marshall | `--session-id` (canonical `SESSION_ID_RE` replaces inline regex) | argparse-only | `test/plan-marshall/plan-marshall/` |
| `plan-marshall/scripts/phase_handshake.py` | plan-marshall | `--phase` (3 subcommands) | argparse-only, parse-then-rebuild | `test/plan-marshall/plan-marshall/` |
| `plan-retrospective/scripts/analyze-logs.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `plan-retrospective/scripts/check-artifact-consistency.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `plan-retrospective/scripts/check-manifest-consistency.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `plan-retrospective/scripts/collect-fragments.py` | plan-marshall | `--plan-id` (init/add/finalize) | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `plan-retrospective/scripts/collect-plan-artifacts.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `plan-retrospective/scripts/compile-report.py` | plan-marshall | `--plan-id`, `--session-id` | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `plan-retrospective/scripts/direct-gh-glab-usage.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `plan-retrospective/scripts/summarize-invariants.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/plan-retrospective/` |
| `tools-integration-ci/scripts/ci.py` | plan-marshall | `--plan-id` (issue / pr-prepare-body / pr-prepare-comment) — propagates through `ci_base` to `github_ops` and `gitlab_ops` routers | argparse-only, parse-then-rebuild | `test/plan-marshall/tools-integration-ci/` |
| `tools-self-review/scripts/self_review.py` | plan-marshall | `--plan-id` | parse-then-rebuild | `test/plan-marshall/tools-self-review/` |
| `workflow-integration-sonar/scripts/sonar_rest.py` | plan-marshall | `--component` (canonical `COMPONENT_RE`) | argparse-only | `test/plan-marshall/workflow-integration-sonar/` |

### Wave C — pm-dev-java + pm-documents (2)

| Script | Bundle | In-scope flags adopted | Families covered | Test directory |
|--------|--------|------------------------|------------------|----------------|
| `manage-maven-profiles/scripts/profiles.py` | pm-dev-java | `--module`, `--name` | argparse-only | `test/pm-dev-java/maven-profile-management/` |
| `manage-interface/scripts/manage-interface.py` | pm-documents | `--field` | argparse-only | `test/pm-documents/manage-interface/` |

## Excluded Scripts (47)

The classification certainty `CERTAIN_EXCLUDE` was assigned during phase-3 component discovery. Each script declares no in-scope identifier flag from the canonical scope list (`--plan-id`, `--lesson-id`, `--session-id`, `--task-number`, `--task-id`, `--component`, `--hash-id`, `--phase`, `--memory-id`, `--field`, `--module`, `--package`, `--domain`, `--name`). Compact form, grouped by directory.

| Directory | Scripts | Rationale |
|-----------|---------|-----------|
| `plan-marshall/skills/build-gradle/scripts/` | `gradle.py` | Build runner — only `--project-name`/`--project-path`/`--root` |
| `plan-marshall/skills/build-maven/scripts/` | `maven.py` | Build runner — uses `register_standard_subparsers`, no in-scope flags |
| `plan-marshall/skills/build-npm/scripts/` | `js_coverage.py`, `npm.py` | Coverage parser / build runner — no in-scope flags |
| `plan-marshall/skills/build-python/scripts/` | `python_build.py` | Build runner — uses `register_standard_subparsers`, no in-scope flags |
| `plan-marshall/skills/execute-task/scripts/` | `assert_test_identifiers.py`, `inject_project_dir.py` | Helper utilities — no in-scope identifier flags |
| `plan-marshall/skills/manage-logging/scripts/` | `plan_logging.py` | Shared logging library — imports `is_valid_plan_id`, no argparse main |
| `plan-marshall/skills/manage-providers/scripts/` | `credentials.py` | Provider credentials handler — only `--skill`/`--scope`/`--auth-type`/`--extra` |
| `plan-marshall/skills/marshall-steward/scripts/` | `bootstrap_plugin.py`, `determine_mode.py`, `gitignore_setup.py` | Interactive setup wizards — no in-scope flags |
| `plan-marshall/skills/plan-marshall/scripts/` | `set_terminal_title.py` | Status-line helper — only `--statusline`/`--plan-label` |
| `plan-marshall/skills/ref-toon-format/scripts/` | `toon_parser.py` | Pure parser library — no main entry |
| `plan-marshall/skills/script-shared/scripts/` | `extension_base.py`, `marketplace_bundles.py`, `marketplace_paths.py`, `triage_helpers.py` | Shared utilities — no main entry |
| `plan-marshall/skills/script-shared/scripts/query/` | `query-architecture.py`, `query-config.py` | Query utilities — only `--bundle`/`--path`/`--refresh`/`--project-dir` |
| `plan-marshall/skills/tools-file-ops/scripts/` | `constants.py`, `file_ops.py`, `jsonl_store.py` | Pure utilities — no main entry |
| `plan-marshall/skills/tools-input-validation/scripts/` | `input_validation.py`, `schema_validation.py` | Validator provider library / schema helpers — no consumer-side argparse |
| `plan-marshall/skills/tools-integration-ci/scripts/` | `ci_base.py`, `ci_health.py` | Helper module / health verifier — no in-scope flags |
| `plan-marshall/skills/tools-permission-doctor/scripts/` | `permission_common.py`, `permission_doctor.py` | Permission tools — only `--settings`/`--scope`/`--marshal` |
| `plan-marshall/skills/tools-permission-fix/scripts/` | `permission_fix.py` | Permission tool — only `--settings`/`--scope`/`--permission(s)` |
| `plan-marshall/skills/tools-script-executor/scripts/` | `await_until.py`, `generate_executor.py` | Polling helper / executor generator — no in-scope flags |
| `plan-marshall/skills/workflow-integration-git/scripts/` | `git_provider.py`, `git_workflow.py` | Provider declaration / git workflow — no in-scope flags |
| `plan-marshall/skills/workflow-integration-github/scripts/` | `github_ops.py`, `github_pr.py`, `github_provider.py` | Router/provider modules — no top-level argparse (dispatched via `ci.py`) |
| `plan-marshall/skills/workflow-integration-gitlab/scripts/` | `gitlab_ops.py`, `gitlab_pr.py`, `gitlab_provider.py` | Router/provider modules — no top-level argparse (dispatched via `ci.py`) |
| `plan-marshall/skills/workflow-integration-sonar/scripts/` | `sonar.py`, `sonar_provider.py` | Triage CLI / provider declaration — `--issue(s)` are JSON payloads, not identifiers |
| `plan-marshall/skills/workflow-permission-web/scripts/` | `permission_web.py` | Webhook tool — only `--domains` (plural JSON list, not the `--domain` identifier) |
| `plan-marshall/skills/workflow-pr-doctor/scripts/` | `pr_doctor.py` | PR doctor — `--pr` is a PR override int, not an in-scope identifier |
| `pm-documents/skills/manage-adr/scripts/` | `manage-adr.py` | ADR management — `--number` is an integer ADR id, not in scope |
| `pm-documents/skills/ref-asciidoc/scripts/` | `asciidoc.py` | AsciiDoc utility — only `--file`/`--path`/`--directory` |
| `pm-documents/skills/ref-documentation/scripts/` | `docs.py` | Documentation review — only `--file`/`--directory`/`--output` |

## Edge cases

These breaking-compat decisions fell out of the sweep and deviate from the strict pre-sweep lesson-2026-04-28-12-001 contract. Each is intentional and documented here as the source of truth.

- **`manage_session.py` — `SESSION_ID_RE` relaxed**: The inline `_SESSION_ID_RE` constant enforced the strict 8-4-4-4-12 UUID grouping. The canonical `SESSION_ID_RE` in `input_validation.py` is the permissive `^[A-Za-z0-9_-]{1,128}$` form, accepting any identifier shape produced by upstream session-id sources. Any caller previously emitting non-UUID session ids (e.g., test fixtures, IDE-supplied tokens) is now accepted.
- **`sonar_rest.py` — canonical `COMPONENT_RE` rejects uppercase / path-shaped keys**: SonarQube allows component keys with uppercase letters and embedded path-like delimiters (e.g., `org:src/Main.java`). The canonical `COMPONENT_RE` `^[a-z0-9-]+(:[a-z0-9-]+)*$` is stricter and now rejects such keys at the CLI boundary. SonarCloud projects with non-canonical keys will receive `status: error / error: invalid_component`. This is the intended behaviour per the canonical-form contract.
- **`manage-tasks.py` — `--task-number` int coercion after validation**: The canonical `TASK_NUMBER_RE` is `^[0-9]+$`. The script previously declared `type=int` directly and relied on argparse to reject non-integers. The migration validates the raw string against `TASK_NUMBER_RE` first, then coerces to int, preserving the int-typed `args.task_number` downstream while gaining the canonical rejection-path semantics.
- **`manage-lessons.py` — `--lesson-id` with `action='append'` validates each element**: The flag is repeatable (`--lesson-id A --lesson-id B`). The validator is wired so each appended element passes through `validate_lesson_id` independently. A single malformed value in the list causes the entire invocation to fail with `error: invalid_lesson_id`.
- **`input_validation.py` foundation extensions during the sweep**: The sweep itself extended the foundation in three ways. (1) A new `parse_args_with_toon_errors()` helper centralises the argparse-to-TOON error path so consumer scripts get `status: error / error: invalid_<field>` output without per-script try/except boilerplate. (2) A bug fix to recursive subparser patching plus prefix-anchored matching ensures `add_<id>_arg(parser)` correctly wires `type=` even when called against deeply-nested subparser trees (e.g., `ci.py`'s issue/pr/pr-prepare-body chain). (3) `add_plan_id_arg(parser)` now wires `type=validate_plan_id` directly so the validator runs at parse time rather than via a deferred `require_valid_plan_id` call — older scripts using the deferred form continue to work, but new adopters get fail-fast behaviour.

## Migration pattern

Per-script approach (5 numbered steps from solution_outline.md):

1. Replace every raw `add_argument('--<id>')` for an in-scope identifier with the matching `add_<id>_arg(parser)` builder.
2. Remove inline regex constants for these identifiers in favour of importing the canonical regex from `plan-marshall:tools-input-validation:input_validation`.
3. Wrap the argparse parse / `main()` entry with a single `try/except ValueError` (or use `parse_args_with_toon_errors()`) that emits `status: error / error: invalid_<field>` TOON before any filesystem, subprocess, or output-construction side-effect.
4. Sweep all three identifier-handling families per file: argparse-only, parse-then-rebuild, post-parse-normalize. Even partially-migrated scripts must be audited end-to-end.
5. Extend pytest with the 6-axis rejection-path coverage (empty / path-separator / glob-meta / traversal / overlong / happy-path) for every newly-validated argument, exercised at the script-level CLI entry point — not at inner resolvers.

## How to use this audit

When adding a new script that accepts identifier-shaped flags, register it in the `SKILL.md` adoption table under the relevant builder, then add an entry to the appropriate wave table (or open a new wave) in this audit. When migrating new flags on an existing script, update the script's row here (in-scope flags column and families covered column) and bump the SKILL.md table to reflect the broader builder coverage. The audit document is the single source of truth for sweep traceability; the SKILL.md table provides a quick-glance status indicator. Both must be kept in sync.
