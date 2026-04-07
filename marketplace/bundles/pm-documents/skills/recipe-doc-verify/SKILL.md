---
name: recipe-doc-verify
description: Recipe for verifying documentation quality across project — validates AsciiDoc format, links, and documentation drift
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Verify Documentation Quality

Recipe for verifying documentation quality across the project. Discovers documentation modules, creates one deliverable per verification area. The task executor loads documentation standards and runs validation scripts.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `recipe_domain` | string | Yes | Domain key (auto-assigned: `documentation`) |
| `recipe_profile` | string | No | Not used — verification is read-only |
| `recipe_package_source` | string | No | Not used — scope is module-level |

---

## Step 1: Resolve Skills

The verification requires documentation formatting and content quality skills:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain documentation --profile core
```

Store all resolved skill names. The deliverables use profile `verification` since no files are modified.

---

## Step 2: Discover Documentation

Query the project architecture for documentation modules:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

Also discover documentation files directly:
- Use Glob: `doc/**/*.adoc`, `docs/**/*.adoc`
- Check for `README.adoc` at project root
- Check for `CLAUDE.md` at project root (for drift checking)

Present discovered documentation scope to user for confirmation. Skip if no documentation files found.

---

## Step 3: Collect Deliverable Data

Create deliverables for each verification area:

### 3a. AsciiDoc Format Validation

One deliverable per documentation directory discovered:

- **Title**: `Verify AsciiDoc format: {directory}`
- **Metadata**:
  - `change_type`: `verification`
  - `execution_mode`: `automated`
  - `domain`: `documentation`
  - `module`: `documentation`
  - `depends`: `none`
- **Profiles**: `verification`
- **Affected files**: All `.adoc` files in the directory (explicit paths)
- **Change per file**: Read-only format validation — no files modified
- **Verification**: `python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path {directory}`
- **Success Criteria**:
  - Zero format errors (blank lines before lists, valid xref syntax, proper headers)
  - All code blocks have language specification

### 3b. Link Verification

One deliverable covering all documentation:

- **Title**: `Verify documentation links and cross-references`
- **Metadata**:
  - `change_type`: `verification`
  - `execution_mode`: `automated`
  - `domain`: `documentation`
  - `module`: `documentation`
  - `depends`: `none`
- **Profiles**: `verification`
- **Affected files**: All `.adoc` files discovered in Step 2
- **Change per file**: Read-only link verification — no files modified
- **Verification**:
  - `python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory {doc_directory}`
  - `python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --file README.adoc`
- **Success Criteria**:
  - All internal xref links resolve to existing files
  - All anchor references resolve to existing sections
  - No deprecated `<<>>` syntax used

### 3c. Documentation Drift Check

One deliverable for project-wide drift detection:

- **Title**: `Check documentation drift against project structure`
- **Metadata**:
  - `change_type`: `verification`
  - `execution_mode`: `automated`
  - `domain`: `documentation`
  - `module`: `documentation`
  - `depends`: `none`
- **Profiles**: `verification`
- **Affected files**: `README.adoc`, `CLAUDE.md` (or equivalent project docs)
- **Change per file**: Read-only drift analysis — no files modified
- **Verification**: Compare documented bundles/modules against actual directory structure using Glob
- **Success Criteria**:
  - All bundles/modules on disk are listed in README and CLAUDE.md
  - No documentation references non-existent bundles/modules
  - Bundle counts match actual directory contents

---

## Step 4: Outline Writing

**4a. Read the deliverable template** to understand the required structure:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**4b. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**4c. Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include these sections in order:
- `# Solution: Verify Documentation Quality` header with `plan_id`, `created`, `compatibility` metadata
- `## Summary` — scope description ({N} documentation files across {M} directories)
- `## Overview` — resolved skills list and documentation scope
- `## Deliverables` — all deliverables from Step 3, using the template structure from 4a

**4d. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Verification Workflow

This section defines how the task executor verifies documentation within each deliverable. The `ref-asciidoc` and `ref-documentation` skills provide the underlying standards.

### Constraints

**Read-only execution:**
- Do NOT modify any documentation files
- Report findings only — fixes are a separate workflow
- Verify script outputs manually before treating links as broken

### Format Validation

Run the AsciiDoc validator and parse output:

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path {target}
```

Map each violation to a finding with `severity: warning`.

### Link Verification

Run link verification with manual confirmation:

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory {directory}
```

For each reported broken link:
1. Extract target path
2. Resolve absolute path
3. Verify with Read tool — if file exists, report as false positive
4. Only confirmed broken links become findings with `severity: error`

### Drift Detection

Compare documentation against actual project structure:
1. Discover actual bundles/modules using Glob on `marketplace/bundles/*/` or equivalent
2. Read README.adoc and extract documented bundle names
3. Read CLAUDE.md and extract documented bundle names
4. Report any discrepancies as findings with `severity: warning`

---

## Related

- `pm-documents:ref-asciidoc` — AsciiDoc formatting, validation, and link verification
- `pm-documents:ref-documentation` — Content quality, tone analysis, and review orchestration
- `plan-marshall:recipe-refactor-to-profile-standards` — Built-in recipe (same 4-step pattern)
- `plan-marshall:phase-3-outline` Step 3 — Loads this skill with input parameters
