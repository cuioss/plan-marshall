# Extension Point: Self-Review Surfacing

> **Type**: Domain-Aware Script | **Hook Method**: standalone implementor skill | **Implementations**: 1 | **Status**: Active

## Overview

Self-review surfacing extensions provide the deterministic candidate-surface phase of the `default:pre-submission-self-review` finalize step. Each implementor inspects the worktree's staged diff in a domain-appropriate way (regex literals in `.py`/`.md`, Java imports + JavaDoc strings, JSX template literals, AsciiDoc include directives, etc.) and emits a TOON envelope carrying seven candidate sub-lists for the LLM cognitive review pass to consume.

The plan-marshall-domain implementor is the in-repo skill `ext-self-review-plan-marshall`; its script notation is `plan-marshall:ext-self-review-plan-marshall:self_review`. Consumer projects (Java, frontend, application code) MAY contribute their own implementor by following the contract below.

This document is a unifying reference; the consumer-side dispatch lives in [`../../phase-6-finalize/workflow/pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) Step 1.

## Implementor Requirements

### Implementation Pattern

To create a new self-review surfacing implementor:

1. Create `skills/ext-self-review-{domain}/` under your bundle.
2. Implement a `self_review.py` script exposing the `surface` subcommand (see CLI Contract below).
3. Add `implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing` to the skill's `SKILL.md` frontmatter.
4. Register the script via the standard executor mapping (`{bundle}:ext-self-review-{domain}:self_review`).
5. Declare the implementor under the domain's `skill_domains[domain].workflow_skill_extensions.self-review` field so `manage-config skill-domains get-extensions --domain {plan_domain}` returns it under the `self-review` key. (The `set-extensions` subcommand's `--type` choices include `self-review` alongside `outline` and `triage`.)

### Implementor Frontmatter

```yaml
implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing
```

### CLI Contract

| Subcommand | Description |
|------------|-------------|
| `surface` | Emit the seven candidate sub-lists from the worktree diff as TOON. |

## Runtime Invocation Contract

### Parameters

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--plan-id` | string | Yes | Plan identifier (kebab-case). Drives both the on-demand footprint derivation (`{base}...HEAD` ∪ porcelain, computed live from the worktree) and worktree resolution via `manage-status get-worktree-path`. |
| `--project-dir` | path | No | Absolute path to the active git worktree (escape hatch). When omitted, the path is auto-resolved from `--plan-id`. |
| `--base-branch` | string | No | Base branch for diff computation (default: `main`). |

### Pre-Conditions

- `--plan-id` resolves to an active plan whose `references.json` carries `base_branch` (used as the footprint diff anchor).
- The resolved worktree is a valid git working tree.
- The base branch ref resolves inside the worktree.

### Post-Conditions

- TOON to stdout carrying the seven candidate sub-lists below (some MAY be empty).
- Non-zero exit on git-unavailable, base-branch-missing, or plan-not-found.

### Output Schema

```toon
status: success
plan_id: {plan_id}
project_dir: {project_dir}
base_branch: {base_branch}
counts:
  regexes: N1
  user_facing_strings: N2
  markdown_sections: N3
  symmetric_pairs: N4
  contract_sources: N5
  schema_bearing_files: N6
  keep_markers: N7
  total: N1+N2+N3+N4+N7

regexes[N1]{file,line,pattern}:
  ...

user_facing_strings[N2]{file,line,context,text}:
  ...

markdown_sections[N3]{file,line,heading,siblings}:
  ...

symmetric_pairs[N4]{file,line,name,partner}:
  ...

contract_sources[N5]{file,sources}:
  ...

schema_bearing_files[N6]{file,format}:
  ...

keep_markers[N7]{file,line,identifier,kind}:
  ...

protected_identifiers[M]:
  - <identifier>
  - ...
```

### Required Candidate Sub-Lists

All seven keys MUST appear in the output (possibly with empty payloads). The five LLM cognitive checks consume:

| Sub-list | Purpose | Consumed By |
|----------|---------|-------------|
| `regexes` | Regex/glob over-fit boundary check | Check 2 (regex over-fit) |
| `user_facing_strings` | Wording disambiguation | Check 3 (ambiguous wording) |
| `markdown_sections` | Duplicate prose scan | Check 4 (duplication) |
| `symmetric_pairs` | Symmetric pair test coverage | Check 1 (symmetric pair) |
| `contract_sources` | Contract cross-reference anchor | Step 2a (cross-reference setup) and Check 5 (contract drift) |
| `schema_bearing_files` | Contract drift detection anchor | Step 2a (cross-reference setup) and Check 5 (contract drift) |
| `keep_markers` | Identifiers flagged as load-bearing by `<!-- self-review: keep <id> -->` markers in the post-image; their values are mirrored into the top-level `protected_identifiers` set so the cognitive review can refuse consolidations that drop the token. | Check 4 (duplication) refuses to drop any protected identifier |

Each entry MUST carry `file` (repo-relative path) AND `line` (1-based line number in the post-diff file content) — these are the only fields the LLM cognitive review consumes for navigation. Additional per-domain sub-lists beyond the seven canonical keys are allowed and ignored by the five canonical checks.

### Detection Rules (Plan-Marshall Domain Reference)

The `ext-self-review-plan-marshall` implementor's detection heuristics are documented in [`../../ext-self-review-plan-marshall/SKILL.md`](../../ext-self-review-plan-marshall/SKILL.md) (seven numbered detection rules covering regex literals, user-facing strings, markdown headings, symmetric-pair function names, contract-source skills, schema-bearing markdown files, and `<!-- self-review: keep <id> -->` markers). Consumer-domain implementors MAY adapt these rules for their language/format but MUST keep the output schema identical so the LLM cognitive review remains domain-agnostic.

## Failure Mode Contract

| Condition | Output |
|-----------|--------|
| Live footprint empty (no `{base}...HEAD` ∪ porcelain changes) | `status: success` with empty candidate lists (no diff scope) |
| Git unavailable or wrong cwd | `status: error\nerror: git_unavailable\nmessage: ...` (exit 1) |
| Base branch not found | `status: error\nerror: base_branch_not_found\nbase_branch: {base}` (exit 1) |
| Plan not found | `status: error\nerror: plan_not_found` (exit 1) |

The consumer dispatcher (`phase-6-finalize/workflow/pre-submission-self-review.md` Step 1) translates non-zero exits into `outcome=failed` on the manifest step without dispatching the LLM cognitive phase.

## Related

- [`../../phase-6-finalize/workflow/pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) — sole consumer of this ext-point's output
- [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md) — `pre_submission_self_review_inactive` pre-filter that gates dispatch of the consumer step
- [`../../tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) — Bucket B cwd contract every implementor obeys
- [`ext-point-triage.md`](ext-point-triage.md) — sibling ext-point pattern (domain-aware finding triage)
