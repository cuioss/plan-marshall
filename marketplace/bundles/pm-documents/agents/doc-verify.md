---
name: doc-verify
description: |
  Verify documentation quality and synchronization (read-only).

  Examples:
  - Input: --plan-id my-plan
  - Output: {status: passed, message: "All checks passed"}
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Skill
---

# Documentation Verify Agent

Documentation verification for plan execution (read-only, no modifications).

## Step 0: Load Development Rules

```
Skill: plan-marshall:dev-general-practices
```

This ensures proper tool usage (Write instead of cat heredoc, Glob instead of find, etc.).

## Parameters

- **--plan-id** (required): Plan identifier passed by phase-5-execute

## Workflow

### Step 1: Load Documentation Standards

```
Skill: pm-documents:ref-asciidoc
```

### Step 2: AsciiDoc Format Validation

Discover all `.adoc` files in the project (excluding `target/`, `.plan/`, `node_modules/`):

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path {project_root}
```

Parse output for format violations. Map each violation to a finding with `severity: warning`.

### Step 3: Link Integrity Check

Verify cross-references and links in documentation directories:

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory doc/
```

Also verify the root README:

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --file README.adoc
```

Map broken links to findings with `severity: error`, deprecated syntax to `severity: warning`.

### Step 4: Documentation Drift Check

Detect drift between documentation and actual project structure:

1. **Discover actual bundles**: Use Glob to find `marketplace/bundles/*/` directories that contain `.claude-plugin/plugin.json`
2. **Read README.adoc**: Extract bundle names from the "Available Bundles" table
3. **Read CLAUDE.md**: Extract bundle count and listed bundles from "Production Bundles" section
4. **Compare**: Report any bundles that exist on disk but are not listed in README or CLAUDE.md

Each missing or extra bundle becomes a finding:
- `file`: The documentation file with the stale listing
- `line`: Line number of the bundle table or section
- `message`: Description of the drift (e.g., "Bundle pm-dev-oci exists on disk but not listed")
- `severity`: warning

### Step 5: Return Verification Result

Aggregate all findings from Steps 2-4 and return the TOON result.

**If zero findings:**

```toon
status: passed
message: "Documentation verification passed: {files_checked} files, {links_checked} links, {bundles_checked} bundles"
```

**If findings exist:**

```toon
status: failed
message: "Documentation verification found {count} issues"

findings[N]{file,line,message,severity}:
doc/example.adoc,12,Missing blank line before list,warning
README.adoc,125,Bundle pm-dev-python not listed in Available Bundles table,warning
```

## Error Handling

- If script not found (executor missing) -> Report with `error_type: script_failure`
- If standards cannot be loaded -> Report with `error_type: resolution_failure`
- This is a read-only agent -> Never modify files

### Error Output (TOON format)

When errors occur, output using this standardized TOON format for hook detection:

```toon
status: error
error_type: {resolution_failure|script_failure|validation_failure}
component: "pm-documents:doc-verify"
message: "{human readable error}"
context:
  operation: "{what was being attempted}"
  plan_id: "{plan_id if known}"
```

