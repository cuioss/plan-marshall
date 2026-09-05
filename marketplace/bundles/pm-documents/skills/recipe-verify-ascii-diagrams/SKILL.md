---
name: recipe-verify-ascii-diagrams
description: Recipe for verifying and fixing alignment of ASCII box diagrams across .md skill source and .adoc documentation, one deliverable per offending file
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
---

# Recipe: Verify and Fix ASCII Box Diagrams

Recipe for sweeping ASCII box diagrams repo-wide, validating their alignment via
the `pm-documents:ref-ascii-diagrams` validator, and creating one fix deliverable
per offending file. Discovers candidate `.md` (marketplace) and `.adoc` (doc)
files, classifies which contain misaligned boxes via the validator's `check`
mode, and outlines a fix per offending file via the validator's `fix` mode.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `ascii_diagrams` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `recipe_domain` | string | Yes | Domain key (auto-assigned: `documentation`) |
| `recipe_profile` | string | No | Not used |
| `recipe_package_source` | string | No | Not used |

---

## Step 1: Resolve Skills

Documentation skills provide formatting and content standards:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain documentation --profile core
```

Store all resolved skill names. Deliverables use profile `implementation` since
`.md` / `.adoc` files are modified by the validator's `fix` mode.

---

## Step 2: Discover Diagrams

### 2a. Locate Candidate Files

Run the canonical `manage-files discover` resolver twice to enumerate candidate
files in both surfaces, capturing each returned `paths` array:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover \
  --root marketplace/bundles \
  --glob "**/*.md" \
  --include-files
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover \
  --root doc \
  --glob "**/*.adoc" \
  --include-files
```

Concatenate the two `paths` arrays into the candidate file list. If both are
empty, report empty scope and return.

### 2b. Classify Each File

For each candidate file, run the `ref-ascii-diagrams` validator's `check` mode to
classify whether it contains a misaligned box:

```bash
python3 .plan/execute-script.py pm-documents:ref-ascii-diagrams:ascii_diagrams check \
  --path {file}
```

Parse the returned TOON. Classify each file as:

- **Offending**: `misaligned_count >= 1` — include in deliverables.
- **Clean**: `misaligned_count == 0` — skip.

### 2c. Present Discovery to User

Show the offending files with their misaligned-line findings (`file` / `line`
pairs from each `check` result). Report the clean-file count for context. No
user decision is required — every offending file becomes a fix deliverable — but
surface the inventory so the user sees the sweep's scope before the outline is
written.

---

## Step 3: Collect Deliverable Data

One deliverable per offending file:

- **Title**: `Fix ASCII box alignment: {file}`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `documentation`
  - `module`: `documentation`
  - `depends`: `none`
- **Profiles**: `implementation`
- **Affected files**: `{file}`
- **Change per file**: Run the validator's `fix` mode over the file to re-pad
  interior lines and rebuild top/bottom rules to a consistent width:
  `python3 .plan/execute-script.py pm-documents:ref-ascii-diagrams:ascii_diagrams fix --path {file}`
- **Verification**: Re-run `ascii_diagrams check --path {file}` and confirm
  `misaligned_count == 0`.
- **Success Criteria**:
  - All boxes in the file are aligned (`check` reports zero misalignment).
  - The fix is idempotent (a second `fix` pass changes nothing).
  - No non-box content (legends, flow-lines, nested boxes) was altered.

---

## Step 4: Outline Writing

**4a. Read the deliverable template**:

```text
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**4b. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**4c. Prepare the solution outline** to be written to `{resolved_path}`:

- `# Solution: Verify ASCII Diagrams` header with `plan_id`, `created`,
  `compatibility` metadata.
- `## Summary` — scope description ({N} offending files of {M} candidates).
- `## Overview` — resolved skills, discovery surfaces (`marketplace/bundles/**/*.md`,
  `doc/**/*.adoc`), offending-file inventory.
- `## Deliverables` — one deliverable per offending file from Step 3, using the
  template structure from 4a.

**4d. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Related

- `pm-documents:ref-ascii-diagrams` — the authoring standard and `check` / `fix`
  validator this recipe drives.
- `pm-documents:recipe-verify-architecture-diagrams` — sibling diagram recipe
  (PlantUML / SVG surface; same 4-step recipe pattern).
- `pm-documents:recipe-doc-verify` — documentation quality verification recipe.
- `plan-marshall:phase-3-outline` Step 3 — Loads this skill with input parameters.
