# Extension Point: Self-Review Surfacing

> **Type**: Domain-Aware Script | **Hook Method**: standalone implementor skill | **Implementations**: 1 | **Status**: Active

## Overview

Self-review surfacing extensions provide the deterministic candidate-surface phase of the `default:pre-submission-self-review` finalize step. Each implementor inspects the worktree's staged diff in a domain-appropriate way (regex literals in `.py`/`.md`, Java imports + JavaDoc strings, JSX template literals, AsciiDoc include directives, etc.) and emits a TOON envelope carrying twenty candidate sub-lists for the LLM cognitive review pass to consume.

The plan-marshall-domain implementor is the `ext-self-review-plan-marshall` skill, homed in the `pm-plugin-development` bundle; its script notation is `pm-plugin-development:ext-self-review-plan-marshall:self_review`. Consumer projects (Java, frontend, application code) MAY contribute their own implementor by following the contract below.

This document is a unifying reference; the consumer-side dispatch lives in [`../../phase-6-finalize/workflow/pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) Step 1.

## Implementor Requirements

### Implementation Pattern

To create a new self-review surfacing implementor:

1. Create `skills/ext-self-review-{domain}/` under your bundle.
2. Implement a `self_review.py` script exposing the `surface` subcommand (see CLI Contract below).
3. Add `implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing` to the skill's `SKILL.md` frontmatter.
4. Register the script via the standard executor mapping (`{bundle}:ext-self-review-{domain}:self_review`).

The consumer dispatch ([`pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) Step 1) discovers surfacing implementors via `find_implementors(ext-point-self-review-surfacing)` (`extension_discovery implementors --ext-point plan-marshall:extension-api/standards/ext-point-self-review-surfacing`) and invokes the first implementor whose `self_review` script notation resolves in the current executor. For the plan-marshall domain the resolvable implementor notation is `pm-plugin-development:ext-self-review-plan-marshall:self_review`, preserving current behavior bit-for-bit. When NO implementor resolves — a consumer project shipping no domain self-review surfacer — the consumer takes the **zero-generator fallback**: an empty candidate envelope, no LLM cognitive dispatch, and a clean `done` outcome. This discovery-routing + zero-generator fallback is what lets the promoted `default_on: true` step ship safely to consumers without a domain surfacer.

### Implementor Frontmatter

```yaml
implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing
```

### CLI Contract

| Subcommand | Required | Description |
|------------|:--------:|-------------|
| `surface` | Yes | Emit the twenty candidate sub-lists from the worktree diff as TOON. |
| `scan-worked-examples` | No | Run the `worked_example_pairs` adjudication over a supplied file population (`--paths-glob`) instead of the diff, reporting the population size the verdict was drawn against. Implemented by the plan-marshall-domain implementor; a consumer-domain implementor MAY omit it, and no consumer of this ext-point dispatches it. |

## Runtime Invocation Contract

### Parameters

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--plan-id` | string | Yes | Plan identifier (kebab-case). Drives both the on-demand footprint derivation (`{base}...HEAD` ∪ porcelain, computed live from the worktree) and worktree resolution via `manage-status get-worktree-path`. |
| `--project-dir` | path | No | Absolute path to the active git worktree (escape hatch). When omitted, the path is auto-resolved from `--plan-id`. |
| `--base-branch` | string | No | Base branch for diff computation (default: `main`). |
| `--since-ref` | string | No | The previous review round's recorded `head_at_completion` SHA. When supplied, the surfaced FILE SET is the footprint intersected with the paths changed since that ref, so a follow-up round re-examines only what the preceding loop-back actually changed. Omitted on round 1 and on the closing full-surface confirmation pass. |

**`--since-ref` narrows the file set, never the examination of a file.** Hunks stay anchored on `--base-branch`, so every file that survives the intersection is still reviewed against its FULL plan diff rather than against only its incremental hunks. An implementor that narrowed the hunk basis instead would be cutting review depth, which this argument does not authorize.

**A delta-scoped round cannot close the step.** The narrowed round is a cheap filter whose clean verdict covers only the files it looked at. The consumer re-runs the surface call once WITHOUT `--since-ref` before recording a terminal `done`, so the step can still only close on a full-surface clean pass — see [`../../phase-6-finalize/workflow/pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) Step 1 and Step 4 Branch A. An implementor supplies the narrowing; it does not decide termination.

### Pre-Conditions

- `--plan-id` resolves to an active plan whose `references.json` carries `base_branch` (used as the footprint diff anchor).
- The resolved worktree is a valid git working tree.
- The base branch ref resolves inside the worktree.
- When `--since-ref` is supplied, it resolves to a commit inside the worktree. An unresolvable value is a diagnosable error — an implementor MUST NOT fall through to the full sweep, because a silent widening would report a full-surface verdict a caller would read as delta-scoped, and vice versa.

### Post-Conditions

- TOON to stdout carrying the twenty candidate sub-lists below (some MAY be empty).
- The echo fields `since_ref`, `surface_scope`, and `files_in_scope` state which round variant produced the payload, so a consumer never has to reconstruct it.
- An empty intersection surfaces NOTHING. A delta round whose intersection is empty genuinely has no files to review, so the implementor MUST emit empty candidate lists rather than falling back to the unfiltered diff.
- Non-zero exit on git-unavailable, base-branch-missing, worktree-resolution, or since-ref-resolution failure.

### Output Schema

```toon
status: success
plan_id: {plan_id}
project_dir: {project_dir}
base_branch: {base_branch}
since_ref: {sha or empty when the round was not delta-scoped}
surface_scope: delta | full
files_in_scope: N
counts:
  by_family:
    structural: {sum of the in_total structural lists}
    prose_contract: {sum of the in_total prose_contract lists}
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
  scan_derived_keys: N19
  worked_example_pairs: N20
  total: N1+N2+N3+N4+N5+N8+N10+N11+N12+N13+N14+N16+N18+N19+N20

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

scan_derived_keys[N19]{file,line,name,sequence,key_consumed}:
  ...

worked_example_pairs[N20]{file,line,clause,required_predicate,example_predicate,agrees}:
  ...
```

The `total` count covers the line-level heuristic lists only. `contract_sources`, `schema_bearing_files`, `count_prose`, and `advertised_form_help_strings` are review-anchor categories not summed into `total`; `protected_identifiers` is a derived index over `keep_markers` entries with `kind: keep_protected` and likewise does not contribute. The authoritative membership is the implementor's `CANDIDATE_LISTS` registry `in_total` field, from which both the emitted key set and the `total` formula are derived — a consumer reads the emitted `counts` block rather than re-deriving the sum from a hand-maintained name list.

### `counts.by_family` — the per-round detector mix

`counts.by_family` partitions the SAME `in_total` population that `total` sums, by each registry entry's `family`, over a closed two-member vocabulary:

| Family | Reads |
|--------|-------|
| `structural` | Code SHAPE — a pattern, a pair of names, a guard, a call site |
| `prose_contract` | PROSE or contract consistency — a heading, a description, a count claim, a documented schema |

Contract obligations on an implementor:

- **The two family counts MUST sum exactly to `counts.total`.** Both are derived from one traversal of the same `in_total` population, so the mix cannot drift from the total it decomposes.
- **BOTH families are always reported, including a zero.** A round that surfaced only prose candidates is a detector-mix signal about the change under review; an omitted key would read as "not measured" rather than "none found", which is the distinction the block exists to preserve.
- **Every registry entry carries exactly one family.** The field is required with no default, so the partition is total by construction rather than by convention.

The mix is reported HERE, in the return TOON, rather than in `display_detail`: this block is the authoritative contract surface and is unbudgeted, while `display_detail` is capped at 80 characters and its no-check-matched verdict (`"self-review clean: {N} candidates examined, no check matched"`) already renders to 61 characters at `{N}=9999` — 19 characters of headroom, too narrow to carry a two-family mix in any readable form. Consumers read `counts.by_family` for the mix.

### Required Candidate Sub-Lists

All twenty keys MUST appear in the output (possibly with empty payloads) — a consumer-domain implementor whose language or format carries no equivalent signal for a given key MUST still emit that key with an empty payload rather than omitting it. This applies to `scan_derived_keys` exactly as it does to every other key: a domain with no scan-versus-anchor derivation shape emits `scan_derived_keys` empty, and the consumer's `total` formula stays well-defined. It applies equally to `worked_example_pairs`: a domain whose documentation carries no BAD/GOOD worked-example convention emits that key empty. The fifteen LLM cognitive checks consume:

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
| `scan_derived_keys` | A key derived by first-match of a compiled pattern over a decomposed sequence rather than by indexing that decomposition at a position anchored on a known root — the scan-versus-anchor shape that collapses distinct inputs to one key and leaves a downstream guard unreachable | Check 14 (unreachable guard behind a scan-derived key) |
| `worked_example_pairs` | A clause section's GOOD worked example whose branch predicate disagrees with the predicate the clause's own normative prose requires — the contrast silently demonstrates the shape its clause forbids, one field over. Only the disagreeing case is surfaced and no denominator is published (agreeing and unadjudicable pairs are both dropped, uncounted), so an empty list states only that no adjudicable disagreement was surfaced in the diff scope — not that every pair agrees, and not a population-level clean verdict; the implementor's `scan-worked-examples` verb publishes the denominator that claim requires | Check 15 (worked-example clause mismatch) |

Each entry MUST carry `file` (repo-relative path) AND `line` (1-based line number in the post-diff file content) — these are the primary navigation fields the LLM cognitive review consumes. Two entry shapes extend or replace this pair: the `source_of_truth` entry carries `name`/`files`/`values` rather than a single `file`/`line`, and the `advertised_form_help_strings` entry carries a second navigational coordinate `raw_pass_line` (the line of the raw `args.<dest>` pass-through) alongside its `file`/`line`, which Check 5's advertised-form sub-check consumes to navigate to the unnormalized-use site. The `count_prose`, `unguarded_boundaries`, and `touched_claims` entries all carry `file`+`line`. Additional per-domain sub-lists beyond the twenty canonical keys are allowed and ignored by the fifteen canonical checks.

### Detection Rules (Plan-Marshall Domain Reference)

The `ext-self-review-plan-marshall` implementor's detection heuristics are documented in [`../../../../pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md`](../../../../pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md) (nineteen numbered detection rules covering regex literals, user-facing strings, markdown headings, symmetric-pair function names, flag-guard pairs, contract-source skills, schema-bearing markdown files, `self-review: keep <id>` HTML-comment markers (the literal `keep`-marker syntax is specified verbatim in the implementor's § Keep-Identifier Markers), producer-consumer pairs, source-of-truth duplicates, same-document normative directives, description-vs-body frontmatter, lone unguarded boundaries, stale count-prose, near-identical-hunk touched claims, advertised-form help strings, same-document ordinal references, scan-derived keys, and worked-example clause pairs). Consumer-domain implementors MAY adapt these rules for their language/format but MUST keep the output schema identical so the LLM cognitive review remains domain-agnostic.

## Failure Mode Contract

| Condition | Output |
|-----------|--------|
| No domain implementor resolved (consumer dispatch, no surfacer in the executor) | Zero-candidate clean run — the consumer step succeeds without dispatching the LLM cognitive phase (`outcome=done`, empty candidate envelope) |
| Live footprint empty (no `{base}...HEAD` ∪ porcelain changes) | `status: success` with empty candidate lists (no diff scope) |
| `--since-ref` supplied and the intersection is empty | `status: success` with empty candidate lists (`surface_scope: delta`) — nothing changed since the previous round, which is a real answer, NOT a signal to widen |
| Git unavailable or wrong cwd | `status: error\nerror: git_unavailable\nmessage: ...` (exit 1) |
| Base branch not found | `status: error\nerror: base_branch_not_found\nbase_branch: {base}` (exit 1) |
| `--since-ref` does not resolve to a commit | `status: error\nerror: since_ref_unresolvable\nmessage: ...` (exit 1) — the round is refused, never silently widened to a full sweep |
| `--plan-id` worktree resolution fails | `status: error\nerror: worktree_resolution_failed\nmessage: ...` (exit 2) |

The consumer dispatcher (`phase-6-finalize/workflow/pre-submission-self-review.md` Step 1) translates non-zero exits into `outcome=failed` on the manifest step without dispatching the LLM cognitive phase.

## Related

- [`../../phase-6-finalize/workflow/pre-submission-self-review.md`](../../phase-6-finalize/workflow/pre-submission-self-review.md) — sole consumer of this ext-point's output
- [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md) — the `commit_push_disabled` and `scope_gated_finalize` pre-filters, among the compose-time subtractions that can drop the consumer step — see that document for the authoritative set, and do not treat the two named here as exhaustive
- [`../../tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md) — Bucket B cwd contract every implementor obeys
- [`ext-point-triage.md`](ext-point-triage.md) — sibling ext-point pattern (domain-aware finding triage)
