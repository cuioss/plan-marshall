---
name: javascript
description: Core JavaScript development standards covering ES modules, modern patterns, code quality, async programming, JSDoc documentation, and tooling
user-invocable: false
---

# JavaScript Development Standards

Core JavaScript development standards covering modern JavaScript features (ES2022+), code quality practices, async programming patterns, and JSDoc documentation.

## Enforcement

- **Execution mode**: Select workflow and execute immediately
- **Prohibited actions**: Do not invent script arguments not documented below; do not skip analysis before fixing
- **Constraints**: All script calls use Rule 9 explicit notation (`python3 .plan/execute-script.py pm-dev-frontend:javascript:jsdoc {subcommand} {args}`)

## Prerequisites

- ES2015+ and ES modules
- npm and JavaScript build tools

## Workflow

### Step 1: Load Core Patterns

Load this standard for any JavaScript implementation work.

```
Read: standards/javascript-fundamentals.md
```

Covers ES modules, variables, functions, and vanilla JS preference.

### Step 2: Load Additional Standards (As Needed)

**Code Quality** (load for refactoring or reviews):
```
Read: standards/code-quality.md
```

Use when: Reviewing code complexity, applying refactoring patterns, or enforcing quality limits.

**Modern Patterns** (load for new code):
```
Read: standards/modern-patterns.md
```

Use when: Writing new code using destructuring, template literals, spread/rest, array methods, or class patterns.

**Async Programming** (load for async code):
```
Read: standards/async-programming.md
```

Use when: Working with Promises, async/await, error handling, or concurrency patterns.

**JSDoc Essentials** (load for documentation work):
```
Read: standards/jsdoc-essentials.md
```

Use when: Documenting JavaScript code, setting up JSDoc and ESLint integration, or reviewing documentation quality. Covers required tags, type annotations, writing style, and build integration.

**JSDoc Patterns** (load for documentation patterns):
```
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

## Related Skills

- `plan-marshall:dev-general-code-quality` - Language-agnostic code quality principles
- `plan-marshall:dev-general-code-quality` - Language-agnostic code quality and documentation principles
- `pm-dev-frontend:css` - CSS standards
- `pm-dev-frontend:lint-config` - ESLint, Prettier, Stylelint configuration
