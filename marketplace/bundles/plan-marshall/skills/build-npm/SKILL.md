---
name: build-npm
description: npm/npx build operations — TypeScript, Jest, ESLint, TAP parsing with workspace discovery, per-file JS coverage analysis, and automatic npm/npx routing
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-build
---

# Build npm

npm/npx build execution with multi-parser output analysis and JavaScript coverage reporting.

## Enforcement

See `build-api-reference.md` § Enforcement for shared rules.
All commands use `python3 .plan/execute-script.py plan-marshall:build-npm:npm {command} {args}`.
npm vs npx routing is automatic; do not force one over the other.

## Scripts

| Script | Purpose |
|--------|---------|
| `npm.py` | CLI dispatcher |
| `js_coverage.py` | Deep per-file coverage analysis (standalone CLI) |
| `_npm_execute.py` | Execution config with npm/npx auto-detection (uses shared `default_command_key_fn`) |
| `_npm_cmd_parse.py` | Single-match parser registry dispatcher |
| `_npm_cmd_discover.py` | Module discovery via package.json workspaces |
| `_npm_parse_typescript.py` | TypeScript error parsing |
| `_npm_parse_jest.py` | Jest/Vitest test output parsing |
| `_npm_parse_eslint.py` | ESLint output parsing |
| `_npm_parse_tap.py` | TAP format test output parsing |
| `_npm_parse_errors.py` | Generic npm error parsing |

## Subcommands

Supports: **run**, **parse**, **coverage-report**, **check-warnings**, **discover**.
See `build-api-reference.md` for the full subcommand API and availability matrix.

### npm-Specific Behavior

- **run**: Additional `--working-dir` (monorepo nested frontends) and `--env` (e.g., `"NODE_ENV=test CI=true"`) parameters. Result includes `command_type` field (`npm`/`npx`)
- **coverage-report**: Searches `coverage/coverage-summary.json` (Jest/Istanbul), `coverage/lcov.info` (LCOV), `dist/coverage/coverage-summary.json`. Reports `function`/`statement` metrics instead of JaCoCo's `instruction`/`method`
- **discover**: Detects workspaces from `package.json` `workspaces` field (npm/yarn) and `pnpm-workspace.yaml` `packages` field (pnpm). Commands are conditional on available scripts

### Producer-Side Finding Storage (`run --plan-id`)

When `run` is invoked with `--plan-id <P>`, every parsed issue from a failed build is auto-stored via the producer path (always-on). Without `--plan-id`, the build parses and formats only (no finding storage). The npm-specific issue→finding-type routing is:

| Parsed `category` (Issue) | Finding type |
|---------------------------|--------------|
| `test_failure`, `test_*` (Jest, Vitest, TAP) | `test-failure` |
| ESLint, `lint_*`, `style_*` | `lint-issue` |
| everything else (TypeScript errors, npm execution failures) | `build-error` |

The finding's `module` carries `npm`, `rule` carries the parser category.

> For the producer→store→consumer→gate flow including the producer-mismatch fidelity contract, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md). This SKILL.md owns the per-tool issue→finding-type routing only.

### js_coverage.py — Deep Coverage Analysis

Per-file coverage breakdown with CRITICAL/WARNING/OK classification, separate from the summary-level `coverage-report` subcommand:

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:js_coverage analyze \
    --report <path> --format json|lcov --threshold <percent>
```

## Parser Architecture

Uses a single-match parser registry: log content is analyzed to detect the tool type (TypeScript, Jest, ESLint, TAP, or npm errors), then routed to the matching parser. This differs from Python's multi-parser combination which runs all matching parsers.

## Module Discovery

Reads `package.json` to detect workspaces and available scripts.

## Canonical invocations

The canonical argparse surface for `npm.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### run

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm run \
  --command-args COMMAND_ARGS \
  [--timeout SECONDS] [--mode {actionable,structured,errors}] [--format {toon,json}] \
  [--working-dir WORKING_DIR] [--env ENV] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

`--project-dir` and `--plan-id` are mutually exclusive.

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm parse \
  --log LOG \
  [--mode {default,errors,structured}] [--format {toon,json}] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### coverage-report

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm coverage-report \
  [--project-path PROJECT_PATH] [--report-path REPORT_PATH] [--threshold PERCENT] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm check-warnings \
  [--warnings WARNINGS] [--acceptable-warnings ACCEPTABLE_WARNINGS] \
  (--project-dir PROJECT_DIR | --plan-id PLAN_ID)
```

### discover

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm discover \
  [--root ROOT] [--format {toon,json}]
```

### run-config-key

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm run-config-key \
  --command-args COMMAND_ARGS [--format {toon,json}]
```

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/npm-impl.md` — npm-specific execution details
