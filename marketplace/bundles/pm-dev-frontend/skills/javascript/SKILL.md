---
name: javascript
description: Core JavaScript development standards covering ES modules, modern patterns, web component patterns (Lit), DOM trust boundaries / XSS prevention, code quality, async programming, JSDoc documentation, and tooling
user-invocable: false
mode: knowledge
---

# JavaScript Development Standards

Core JavaScript development standards covering modern JavaScript features (ES2022+), code quality practices, async programming patterns, and JSDoc documentation.

## Enforcement

- **Prohibited actions**: Do not invent script arguments not documented below; do not skip analysis before fixing
- **Constraints**: All script calls use Rule 9 explicit notation (`python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc {subcommand} {args}`)

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `jsdoc` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Prerequisites

- ES2015+ and ES modules
- npm and JavaScript build tools

## Workflow

### Step 1: Load Core Patterns

Load this standard for any JavaScript implementation work.

```text
Read: standards/javascript-fundamentals.md
```

Covers ES modules, variables, functions, and vanilla JS preference.

### Step 2: Load Additional Standards (As Needed)

**Code Quality** (load for refactoring or reviews):
```text
Read: standards/code-quality.md
```

Use when: Reviewing code complexity, applying refactoring patterns, or enforcing quality limits.

**Modern Patterns** (load for new code):
```text
Read: standards/modern-patterns.md
```

Use when: Writing new code using destructuring, template literals, spread/rest, array methods, or class patterns.

**Security** (DOM trust boundaries / XSS prevention):

The JavaScript security surface — DOM trust boundaries, XSS sinks, sanitization, and Trusted Types — is owned by `Skill: pm-dev-frontend:javascript-security`. Load that skill for any security-sensitive review or hardening task; it resolves through the `security` profile and references the DOM-trust/XSS content under this skill's `standards/modern-patterns.md`.

**Async Programming** (load for async code):
```text
Read: standards/async-programming.md
```

Use when: Working with Promises, async/await, error handling, or concurrency patterns.

**JSDoc Essentials** (load for documentation work):
```text
Read: standards/jsdoc-essentials.md
```

Use when: Documenting JavaScript code, setting up JSDoc and ESLint integration, or reviewing documentation quality. Covers required tags, type annotations, writing style, and build integration.

**JSDoc Patterns** (load for documentation patterns):
```text
Read: standards/jsdoc-patterns.md
```

Use when: Documenting functions, classes, modules, types, or web components (Lit). Provides patterns with examples for each code element type.

### Workflow: Analyze JSDoc Violations

Use when: Identifying missing or incomplete JSDoc documentation across files or directories.

#### 1. Run violation analysis script

```bash
# Analyze entire directory
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --directory src/

# Analyze single file
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --file src/utils/formatter.js

# Analyze only for missing JSDoc (skip syntax checks)
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --directory src/ --scope missing

# Analyze only JSDoc syntax issues
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze --directory src/ --scope syntax
```

#### 2. Process violation results

Review violations categorized by severity:
- **CRITICAL**: Exported/public API without JSDoc
- **WARNING**: Internal function without JSDoc, missing @param/@returns
- **SUGGESTION**: Missing optional tags (@example, @fileoverview)

Fix CRITICAL violations first (exported functions/classes), then WARNING, then SUGGESTION (optional).

#### Violation Types

- `missing_jsdoc` - Function/class entirely missing JSDoc
- `missing_class_doc` - Class without documentation
- `missing_constructor_doc` - Constructor with parameters undocumented
- `missing_param` - @param tag missing for parameter
- `missing_param_type` - Type annotation missing in @param
- `missing_returns` - @returns tag missing for return value
- `missing_fileoverview` - No @fileoverview at file level

#### Scope Options

- `all` - Check for missing JSDoc and syntax issues (default)
- `missing` - Only check for missing JSDoc documentation
- `syntax` - Only check JSDoc syntax and completeness

## Canonical invocations

The canonical argparse surface for `jsdoc.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### analyze

```bash
python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc analyze \
  (--directory DIRECTORY | --file FILE) [--scope {all,missing,syntax}]
```

`--directory` and `--file` are mutually exclusive; exactly one must be supplied.

## Related Skills

- `plan-marshall:ref-code-quality` - Language-agnostic code quality and documentation principles
- `pm-dev-frontend:css` - CSS standards
- `pm-dev-frontend:lint-config` - ESLint, Prettier, Stylelint configuration
- Anthropic `frontend-design` skill - Visual-aesthetic guidance (distinctive, production-grade UI; avoiding generic "AI slop" design). Complementary to this skill: `javascript` governs code standards, `frontend-design` governs visual aesthetics. Pointer only — no content duplicated here.
