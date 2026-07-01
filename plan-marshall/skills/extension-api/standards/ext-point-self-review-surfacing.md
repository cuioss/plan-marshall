# Extension Point: Self-Review Surfacing

> **Type**: Domain-Aware Script | **Hook Method**: standalone implementor skill | **Implementations**: 1 | **Status**: Active

## Overview

Self-review surfacing extensions provide the deterministic candidate-surface phase of the `default:pre-submission-self-review` finalize step. Each implementor inspects the worktree's staged diff in a domain-appropriate way (regex literals in `.py`/`.md`, Java imports + JavaDoc strings, JSX template literals, AsciiDoc include directives, etc.) and emits a TOON envelope carrying eighteen candidate sub-lists for the LLM cognitive review pass to consume.

The plan-marshall-domain implementor is the `ext-self-review-plan-marshall` skill, homed in the `pm-plugin-development` bundle; its script notation is `pm-plugin-development:ext-self-review-plan-marshall:self_review`. Consumer projects (Java, frontend, application code) MAY contribute their own implementor by following the contract below.

This document is a unifying reference; the consumer-side dispatch lives in [`../../phase-6-finalize/workflow/pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) Step 1.

## Implementor Requirements

### Implementation Pattern

To create a new self-review surfacing implementor:

1. Create `skills/ext-self-review-{domain}/` under your bundle.
2. Implement a `self_review.py` script exposing the `surface` subcommand (see CLI Contract below).
3. Add `implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing` to the skill's `SKILL.md` frontmatter.
4. Register the script via the standard executor mapping (`{bundle}:ext-self-review-{domain}:self_review`).

The consumer dispatch ([`pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) Step 1) calls the implementor's `surface` subcommand by its fixed notation directly — there is no registration step. For the plan-marshall domain the canonical implementor notation is `pm-plugin-development:ext-self-review-plan-marshall:self_review`; a consumer-domain implementor is wired in by the consumer's own dispatch using the implementor's executor notation.

### Implementor Frontmatter

```yaml
implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing
```

### CLI Contract

| Subcommand | Description |
|------------|-------------|
| `surface` | Emit the eighteen candidate sub-lists from the worktree diff as TOON. |

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

- TOON to stdout carrying the eighteen candidate sub-lists below (some MAY be empty).
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
  flag_guard_pairs: N5
  contract_sources: N6
  schema_bearing_files: N7
  keep_markers: N8
  protected_identifiers: N9
  producer_consumer: N10
  source_of_truth: N11
  same_document_consistency: N12
  description_vs_body: N13
  unguarded_boundaries: N14
  count_prose: N15
  touched_claims: N16
  advertised_form_help_strings: N17
  ordinal_references: N18
  total: N1+N2+N3+N4+N5+N8+N10+N11+N12+N13+N14+N16+N18

regexes[N1]{file,line,pattern}:
  ...

user_facing_strings[N2]{file,line,context,text}:
  ...

markdown_sections[N3]{file,line,heading,siblings}:
  ...

symmetric_pairs[N4]{file,line,name,partner,test_present}:
  ...

flag_guard_pairs[N5]{file,line,flag,forms_covered}:
  ...

contract_sources[N6]{file,sources}:
  ...

schema_bearing_files[N7]{file,format}:
  ...

keep_markers[N8]{file,line,identifier,kind}:
  ...

protected_identifiers[N9]:
  - <identifier>
  - ...

producer_consumer[N10]{file,line,key,consumed}:
  ...

source_of_truth[N11]{name,files,values}:
  ...

same_document_consistency[N12]{file,line,keyword,text}:
  ...

description_vs_body[N13]{file,line,key,description}:
  ...

unguarded_boundaries[N14]{file,line,boundary,guarded}:
  ...

count_prose[N15]{file,line,text}:
  ...

touched_claims[N16]{file,line,text}:
  ...

advertised_form_help_strings[N17]{file,line,arg,help_text,raw_pass_line}:
  ...

ordinal_references[N18]{file,line,text,list_line}:
  ...
```

The `total` count covers the thirteen line-level heuristics (`regexes`, `user_facing_strings`, `markdown_sections`, `symmetric_pairs`, `flag_guard_pairs`, `keep_markers`, `producer_consumer`, `source_of_truth`, `same_document_consistency`, `description_vs_body`, `unguarded_boundaries`, `touched_claims`, `ordinal_references`) only. `contract_sources`, `schema_bearing_files`, `count_prose`, and `advertised_form_help_strings` are review-anchor categories not summed into `total`; `protected_identifiers` is a derived index over `keep_markers` entries with `kind: keep_protected` and likewise does not contribute.

### Required Candidate Sub-Lists

All eighteen keys MUST appear in the output (possibly with empty payloads). The thirteen LLM cognitive checks consume:

| Sub-list | Purpose | Consumed By |
|----------|---------|-------------|
| `regexes` | Regex/glob over-fit boundary check | Check 2 (regex over-fit) |
| `user_facing_strings` | Wording disambiguation | Check 3 (ambiguous wording) |
| `markdown_sections` | Duplicate prose scan | Check 4 (duplication) |
| `symmetric_pairs` | Symmetric pair test coverage | Check 1 (symmetric pair) |
| `flag_guard_pairs` | Flag-form-coverage comparison across symmetric guards | Check 1 (symmetric pair / flag-form coverage) |
| `contract_sources` | Contract cross-reference anchor | Step 2a (cross-reference setup) and Check 5 (contract drift) |
| `schema_bearing_files` | Contract drift detection anchor | Step 2a (cross-reference setup) and Check 5 (contract drift) |
| `keep_markers` | Identifiers flagged as load-bearing by `self-review: keep <id>` HTML-comment markers (the literal `keep`-marker syntax is specified verbatim in the implementor's § Keep-Identifier Markers) in the post-image; their values are mirrored into the top-level `protected_identifiers` set so the cognitive review can refuse consolidations that drop the token. | Check 4 (duplication) refuses to drop any protected identifier |
| `producer_consumer` | Dangling producers (a value emitted into an output slot with no consumer anywhere in the diff) | Check 6 (producer-without-consumer) |
| `source_of_truth` | The same UPPER_SNAKE_CASE constant bound to divergent literals across two declared SoT files | Check 7 (source-of-truth drift) |
| `same_document_consistency` | Added RFC-2119 normative directives, surfaced for sibling-contradiction review (Mode-2: an added normative line MUST surface a candidate, never an empty surface) | Check 8 (same-document contradiction) |
| `description_vs_body` | A modified `.md` whose frontmatter `description`/`summary` may describe a model the changed body no longer implements | Check 9 (description-vs-body drift) |
| `unguarded_boundaries` | Added `subprocess.*` / file-I/O calls with no `check=True` and no enclosing `try/except` in the same function | Check 10 (lone unguarded boundary) |
| `count_prose` | Count-prose (a digit or number word adjacent to a cardinality noun) in every `SKILL.md` of a modified file's skill directory, for count-correctness re-check | Check 11 (stale count-prose) |
| `touched_claims` | The `+` line of a `-`/`+` hunk pair differing by exactly one token, surfaced for whole-line claim re-verification | Check 12 (touched-claim re-check) |
| `advertised_form_help_strings` | A multi-form argparse `help=` string paired with a raw `args.<dest>` pass-through that does no normalization — advertised-input-form normalization cross-check | Check 5 (contract drift) |
| `ordinal_references` | Added same-document ordinal references (`item N` / `step N` / bare `(N)`) pointing into an ordered-list block the same diff touched, surfaced so the reviewer confirms each ordinal still resolves to its intended item after the renumber | Check 13 (same-document ordinal-reference re-check) |

Each entry MUST carry `file` (repo-relative path) AND `line` (1-based line number in the post-diff file content) — these are the primary navigation fields the LLM cognitive review consumes. Two entry shapes extend or replace this pair: the `source_of_truth` entry carries `name`/`files`/`values` rather than a single `file`/`line`, and the `advertised_form_help_strings` entry carries a second navigational coordinate `raw_pass_line` (the line of the raw `args.<dest>` pass-through) alongside its `file`/`line`, which Check 5's advertised-form sub-check consumes to navigate to the unnormalized-use site. The `count_prose`, `unguarded_boundaries`, and `touched_claims` entries all carry `file`+`line`. Additional per-domain sub-lists beyond the eighteen canonical keys are allowed and ignored by the thirteen canonical checks.

### Detection Rules (Plan-Marshall Domain Reference)

The `ext-self-review-plan-marshall` implementor's detection heuristics are documented in [`../../../../pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md`](../../../../pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md) (eighteen numbered detection rules covering regex literals, user-facing strings, markdown headings, symmetric-pair function names, flag-guard pairs, contract-source skills, schema-bearing markdown files, `self-review: keep <id>` HTML-comment markers (the literal `keep`-marker syntax is specified verbatim in the implementor's § Keep-Identifier Markers), producer-consumer pairs, source-of-truth duplicates, same-document normative directives, description-vs-body frontmatter, lone unguarded boundaries, stale count-prose, near-identical-hunk touched claims, advertised-form help strings, and same-document ordinal references). Consumer-domain implementors MAY adapt these rules for their language/format but MUST keep the output schema identical so the LLM cognitive review remains domain-agnostic.

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
