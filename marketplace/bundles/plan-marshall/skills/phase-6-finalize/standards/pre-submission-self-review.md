---
name: default:pre-submission-self-review
description: Pre-submission structural self-review (symmetric pairs, regex over-fit, wording, duplication) before commit-push
order: 7
---

# Pre-Submission Self-Review

Pure executor for the `pre-submission-self-review` finalize step. Catches the class of structural defects that PR-review bots (gemini-code-assist, Copilot, Sonar) reliably surface but local quality gates (pytest, ruff, mypy, plugin-doctor) systematically miss: missing initialization in symmetric save/restore pairs, regex/glob over-fit, ambiguous user-facing wording, and duplicate prose sections covering the same contract.

The step combines a deterministic helper that surfaces concrete candidates from the staged diff with an LLM cognitive review applied only to those candidates. On any finding the LLM returns, the step hard-fails and halts the phase, mirroring the gating-step convention established by `pre-push-quality-gate`.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` via the `pre_submission_self_review_inactive` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`). The composer drops the step when `commit_strategy == none` (transitively, via `commit_strategy_none`) OR `references.modified_files` is empty. When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a non-empty findings list records `outcome=failed` and halts the phase.

## Inputs

- `references.modified_files` — list[string] of repo-relative paths recorded by Phase 5. Defines the change footprint the deterministic helper inspects.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The deterministic helper invocation MUST pass `--project-dir {worktree_path}`; the staged diff is computed against the worktree's base branch.

## Execution

### Deterministic phase: surface candidates

Invoke the deterministic helper to surface concrete candidates from the staged diff. The helper reads `references.modified_files` for the active plan, computes the staged diff against the worktree's base branch, and emits four candidate lists in a single TOON document on stdout.

```bash
python3 .plan/execute-script.py plan-marshall:tools-self-review:self_review \
  surface --plan-id {plan_id} --project-dir {worktree_path}
```

Parse the TOON output. The candidate lists are:

| List | Schema | Purpose |
|------|--------|---------|
| `regexes[N]{file,line,pattern}` | Added regex literals and fnmatch globs in `.py`/`.md` hunks | Boundary check for regex over-fit |
| `user_facing_strings[N]{file,line,context,text}` | Added strings in skill prose, error messages, CLI help (docstrings, `print(` arguments, `description=`, `help=`, markdown bullet/heading text) | Wording disambiguation |
| `markdown_sections[N]{file,line,heading,siblings}` | Added/edited markdown sections per file with sibling-section list scoped to the same file | Duplication scanning |
| `symmetric_pairs[N]{file,line,name,partner}` | Functions whose names match save/load, init/restore, push/pop, acquire/release, open/close, start/stop pairings | Symmetric pair test-coverage check |
| `contract_sources[N]{file,sources}` | Per modified file: nearby `SKILL.md` and `standards/*.md` (semicolon-joined repo-relative paths) | Contract cross-reference anchor |
| `schema_bearing_files[N]{file,format}` | Markdown files within the configured contract radius whose content contains a fenced JSON or TOON block | Contract drift detection |

If the helper exits non-zero, halt and proceed to **Mark Step Complete (Failure)** below — surface the helper error in the `display_detail` payload.

### LLM cognitive phase: load contracts, then apply five checks

#### Step 0 — Cross-reference setup (MUST run before any check)

Before scanning the line-level candidate lists, load the contract sources surfaced by the deterministic phase. This step is the workflow-shape fix for the failure mode where the LLM reviews each surfaced hunk in isolation and overlooks contract drift.

1. For every entry in `contract_sources`, read every path listed in the `sources` field. These are the `SKILL.md` and `standards/*.md` files governing the changed code. Read them in full — not excerpts.
2. For every entry in `schema_bearing_files`, read the file. These are nearby markdown documents that declare a fenced JSON or TOON schema; they govern the post-image of any hunk that touches the same schema.
3. Hold the loaded contract content in working memory for the rest of the cognitive phase. The five checks below cross-reference hunks against this content; do not re-discover contracts on demand.

#### Checks

For each non-empty candidate list, apply the corresponding cognitive check to the surfaced items only — never expand the review to candidates the helper did not surface.

1. **Symmetric pair test-coverage check** — for each `symmetric_pairs` entry, search the test directory for a test that exercises BOTH `name` and `partner` and asserts the post-state of the partner without first invoking `name` in the same test. A symmetric pair where one half is silently skipped (e.g., `_original_plan_dir_name` was never re-initialized on restore) is the canonical defect class. Defect → record finding `{file, line, defect_class: symmetric_pair_uncovered, rationale: <which half is unexercised and why it matters>}`.

2. **Regex over-fit boundary check** — for each `regexes` entry, construct one synthetic example that SHOULD match (positive) and one that SHOULD NOT match (negative), and verify the regex/glob's behavior on each. If the boundary is wrong (matches a path it should not, or fails to match a path it should), record finding `{file, line, defect_class: regex_overfit, rationale: <example that fails the intended boundary>}`.

3. **Wording disambiguation check** — for each `user_facing_strings` entry, read the string out of the surrounding context and ask "could this mean two things?". If the answer is yes (an operator could plausibly take the wrong action based on the wording alone), record finding `{file, line, defect_class: ambiguous_wording, rationale: <the two readings, and which one was intended>}`.

4. **Duplication scan** — for each `markdown_sections` entry, compare the new/edited section's contract against its sibling sections (provided in the `siblings` field) within the same file. Two sections that describe the same check, table, or rule with subtly different wording are a defect — operators do not know which to follow. Record finding `{file, heading, defect_class: duplicate_prose, rationale: <which sibling overlaps and where they diverge>}`.

5. **Contract drift cross-check** — for every modified file that appears in `contract_sources`, AND every hunk in the diff that touches a schema declared in any `schema_bearing_files` entry, verify the post-image of the change against the documented contract. Specifically:
    - For every `markdown_sections` entry whose `file` equals (or shares a parent skill with) a `contract_sources` entry, verify that the new/edited section's documented schema, table fields, or detection heuristic agrees with what the code under that skill actually emits or enforces.
    - For every code hunk that adds or modifies a function emitting a schema (e.g., `output_toon({...})`, `print(json.dumps({...}))`), verify that the emitted field set matches the schema declared in the corresponding `schema_bearing_files` entry. Missing fields, renamed fields, or extra undocumented fields are all drift.
    - For every detection heuristic added or modified (e.g., regex over a project marker, glob over a path category), verify that the heuristic agrees with the contract section that documents the same detection rule. A loosened heuristic (substring where the contract specifies a structured marker) is drift.

    Defect → record finding `{file, line, defect_class: contract_drift, rationale: <which contract source disagrees with the hunk, and what the drift is — missing field, loosened heuristic, divergent schema, etc.>}`.

Concatenate all findings into a single `findings[N]{file,line,defect_class,rationale}` list. Empty list → success path. Non-empty list → failure path.

#### Worked example: the lesson that drove this step

The defects this cross-reference step exists to catch:

- **Missing schema field**: a helper emitted `markdown_sections[N]{file,heading,siblings}` while the consumer's documented schema declared `markdown_sections[N]{file,line,heading,siblings}` (the `line` field anchors findings). The hunk modifying the helper would surface as both a `markdown_sections` entry (in the helper SKILL or standards) AND in the corresponding code hunk; cross-checking the emitted dict against the schema declared in the same change set catches the omission. Without this step, the reviewer treats each hunk as locally correct and ships the contract drift.
- **Loosened detection heuristic**: a CI-provider detection routine matched on a substring (`'github' in url`) where the contract section documented a structured project marker (`.github/workflows/*.yml`). The hunk surfaces as a `regexes`/`user_facing_strings` entry and the contract section surfaces in `markdown_sections`; cross-checking the new heuristic against the documented marker catches the over-broad match before it produces false positives in production.

Both defect classes were missed in the dogfood PR that drove this step's introduction (lesson `2026-04-28-09-001`); the LLM pass was reviewing surfaced hunks one at a time without consulting the contracts that lived in the same diff. The Step 0 cross-reference setup plus check 5 close that gap.

## Mark Step Complete

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — findings list is empty**: `{N}` is the total count of candidates examined across all four lists (sum of the four list lengths from the deterministic phase):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-submission-self-review --outcome done \
  --display-detail "self-review clean: {N} candidates examined"
```

**Branch B — findings list is non-empty**: `{K}` is `len(findings)`. Surface the findings in the finalize TOON output (consumed by `output-template.md`) so the operator sees `file:line` and `defect_class` per finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-submission-self-review --outcome failed \
  --display-detail "self-review found {K} issues"
```

The dispatcher's existing failure handling halts the phase on `outcome=failed`, matching the gating-step contract used by `pre-push-quality-gate`. The operator must address every finding (amend the diff: rename, tighten regex, rewrite wording, delete duplicate section), re-run the step, and only then advance to `commit-push`.
