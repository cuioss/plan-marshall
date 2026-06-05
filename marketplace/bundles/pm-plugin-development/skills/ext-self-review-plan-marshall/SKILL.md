---
name: ext-self-review-plan-marshall
description: Plan-marshall-domain implementor of the ext-self-review-{domain} extension point. Surfaces deterministic candidates (regexes, user-facing strings, markdown sections, symmetric-pair functions, flag-guard pairs, contract sources, schema-bearing files) for pre-submission structural self-review.
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing
---

# Self-Review Candidate Surfacing — plan-marshall domain

**Role**: Plan-marshall-domain implementor of the `ext-self-review-{domain}` extension point (see [`../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`](../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md)). Surfaces concrete candidates from the worktree's staged diff so the LLM cognitive review pass in [`../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md) can apply the five structural-defect checks (symmetric pair, regex over-fit, wording disambiguation, duplication, contract drift) against a bounded surface, not an unbounded read of the whole diff.

## Enforcement

**Execution mode**: Library script; invoked via the standard 3-part executor notation by `plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md` Step 1.

**Prohibited actions:**
- Do not modify any source files; the helper is read-only against the worktree
- Do not invoke `git` without `git -C {project_dir}` (per dev-agent-behavior-rules)
- Do not write to `/tmp/` or any path outside `.plan/temp/` when staging intermediate state

**Constraints:**
- stdlib-only (no third-party Python dependencies)
- Output is TOON to stdout; errors are TOON with `status: error` and a non-zero exit code
- Every candidate entry MUST carry `file` (repo-relative path) and `line` (1-based line number in the post-diff file content) — these are the only fields the LLM cognitive review consumes for navigation

## When to Use

Invoked exclusively by `default:pre-submission-self-review` (see `plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md` Step 1). No other caller is supported. The script is registered as `pm-plugin-development:ext-self-review-plan-marshall:self_review` and is NOT user-invocable from a slash command — `user-invocable: false` per the script-only registration convention; this skill is intentionally absent from `pm-plugin-development/.claude-plugin/plugin.json`.

## Keep-Identifier Markers

Authors can flag identifiers that are load-bearing for grep-based external tests, downstream parsers, or any other consumer that asserts a token's literal presence in the source. The marker tells the LLM cognitive review pass that the identifier MUST remain grep-able in the post-image — prose consolidation, rename, or refactor MUST NOT remove it.

**Syntax**: `<!-- self-review: keep <identifier> -->`

- `<identifier>` is a single whitespace-free token (e.g. `phase_breakdown_override_content`, `--body`, `triage_helpers`). Whitespace inside the identifier is not supported — use one marker per identifier.
- Whitespace around `self-review:`, around `keep`, and between `keep` and the identifier is tolerant.
- The marker is an HTML comment, so it is invisible in rendered Markdown but visible to the deterministic surface scan.

**Placement**: any line within the file or section that authoritatively owns the identifier. The detector scans the diff's added/post-image lines for marker matches — placing the marker on or near the line that defines or references the protected token gives the LLM review the strongest navigational anchor. Multiple markers on the same file are allowed and each emit an independent candidate.

**Semantics**: for each recognized marker in an added hunk, the surface scan checks whether the protected identifier still appears anywhere in the file's post-image OUTSIDE the marker line itself (the marker comment's own copy of the identifier is excluded from the grep so it cannot mask a removal):

- **Identifier still grep-able** → candidate kind `keep_protected`. The identifier joins the surface's `protected_identifiers` set so the LLM review knows to refuse any consolidation that would drop the token in a subsequent revision.
- **Identifier no longer grep-able** → candidate kind `keep_violation`. The marker is orphaned — the consolidation under review has already removed the protected token. The LLM review surfaces this as a refusal-grade defect.

The marker is a pure structural signal — no LLM call is added to the surface scan; the detector emits a `keep_markers` candidate list and a `protected_identifiers` set alongside the other heuristic lists. See the `keep_markers[]` and `protected_identifiers[]` shapes under § Output below.

## Subcommand: `surface`

Surfaces eight candidate lists from the worktree's staged diff against the base branch.

### Inputs

| Argument | Required | Description |
|----------|----------|-------------|
| `--plan-id PLAN_ID` | Yes | Plan identifier (kebab-case). Used to derive the plan footprint on demand from the worktree (`{base}...HEAD` ∪ porcelain) and (when `--project-dir` is omitted) to auto-resolve the worktree path via `manage-status get-worktree-path`. |
| `--project-dir PROJECT_DIR` | No | Absolute path to the active git worktree (escape hatch). When omitted, the path is auto-resolved from `--plan-id`. All `git` calls run as `git -C {project_dir} ...`. |
| `--base-branch BRANCH` | No | Base branch for diff computation. Defaults to `main`. |
| `--contract-radius N` | No | Directory levels to walk up when collecting schema-bearing markdown files (default: 3). |

### Output

TOON to stdout. The candidate-list keys are always present (possibly empty):

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
  total: N1+N2+N3+N4+N5+N8

regexes[N1]{file,line,pattern}:
  {repo-relative-path},{line},{regex-pattern-string}

user_facing_strings[N2]{file,line,context,text}:
  {repo-relative-path},{line},{context-tag},{string-text}

markdown_sections[N3]{file,line,heading,siblings}:
  {repo-relative-path},{line},{heading},{semicolon-joined-sibling-headings}

symmetric_pairs[N4]{file,line,name,partner,test_present}:
  {repo-relative-path},{line},{function-name},{inferred-partner-name},{true|false}

flag_guard_pairs[N5]{file,line,flag,forms_covered}:
  {repo-relative-path},{line},{--flag},{space|equals|both}

contract_sources[N6]{file,sources}:
  {repo-relative-path},{semicolon-joined-contract-source-paths}

schema_bearing_files[N7]{file,format}:
  {repo-relative-path},{json|toon}

keep_markers[N8]{file,line,identifier,kind}:
  {repo-relative-path},{line},{identifier},{keep_protected|keep_violation}

protected_identifiers[N9]:
  {identifier}
```

> The `total` count covers the six line-level heuristics (`regexes`, `user_facing_strings`, `markdown_sections`, `symmetric_pairs`, `flag_guard_pairs`, `keep_markers`) only. `contract_sources` and `schema_bearing_files` are review-anchor categories with their own counts; they are not summed into `total` because each modified file contributes at most one `contract_sources` entry whose payload is references rather than candidates. `protected_identifiers` is a derived index over `keep_markers` entries with `kind: keep_protected` — it does not contribute to `total` either.

### Detection Rules

1. **Regexes** — added lines (`+` hunks) in `.py` and `.md` files containing one of:
   - `re.compile(...)`, `re.match(...)`, `re.search(...)`, `re.findall(...)`, `re.sub(...)`, `re.fullmatch(...)`
   - `fnmatch.fnmatch(...)`, `fnmatch.filter(...)`
   - Raw-string regex literals: `r"..."` or `r'...'` containing regex metacharacters (`^$.*+?[](){}|\`)
   - Glob patterns embedded in argparse `choices=[...]` or `--*-globs` config arrays
   The `pattern` field captures the literal string between the function call's first quote pair (or the raw-string body), truncated to 120 characters.

2. **User-facing strings** — added lines containing one of:
   - Docstring opening: triple-quoted strings on a line by themselves following `def `/`class `
   - `print(...)` first positional argument
   - argparse `description=`, `help=`, `epilog=` (any string literal directly assigned)
   - `raise XxxError("...")`, `raise XxxError(f"...")` first argument
   - Markdown heading (`^#+\s+`)
   - Markdown bullet (`^[-*]\s+`)
   The `context` field is one of `docstring`, `print`, `argparse_description`, `argparse_help`, `argparse_epilog`, `raise_message`, `markdown_heading`, `markdown_bullet`. The `text` field is the captured string, truncated to 200 characters.

3. **Markdown sections** — for each `.md` file appearing in the diff:
   - Parse all `^#+\s+` headings in the post-diff file content
   - Group siblings: headings with the same depth AND the same nearest-ancestor heading at depth-1
   - Emit one entry per heading whose line falls within an added/edited diff hunk
   - The `siblings` field is a semicolon-joined list of sibling heading texts (peer headings under the same parent), excluding the entry's own heading

4. **Symmetric-pair candidates** — added lines in `.py` files matching `^def\s+(\w+)`. The captured function name is split on `_` and inspected for any of the 6 pair tokens: `save/load`, `init/restore`, `push/pop`, `acquire/release`, `open/close`, `start/stop`. When a match is found, the `partner` field is the same function name with the matched token swapped to its pair (e.g., `save_state` → `load_state`). Each entry also carries a deterministic `test_present` flag (Tier-2 missing-test heuristic): the `test/` tree under `--project-dir` is searched for a word-boundary occurrence of the function name (same `(?<![a-zA-Z0-9_-])` / `(?![a-zA-Z0-9_-])` lookaround discipline used for keep-identifier markers). `test_present=false` is the Tier-2 missing-test signal — a newly added symmetric function with no test surface. The LLM half of the check (deciding whether the missing coverage is a real defect) lives in the consumer's Step 3 check 1; see [`../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md).

5. **Flag-guard pairs** — added lines in `.py` files containing an argument-presence guard over a `--flag` token. Two guard shapes are recognized: membership/substring tests where a quoted `--flag` literal is the left operand of an `in` test (e.g., `'--project-dir' in args`, `'--plan-id=' in argv`) and `startswith` checks over a quoted `--flag` literal (e.g., `arg.startswith('--project-dir')`). For each guarded flag the detector classifies which flag *forms* the guard covers: the bare `--flag` token guards the **space-separated** form (`--flag value`), and the `--flag=` prefix guards the **equals** form (`--flag=value`). Coverage is aggregated per `(file, flag)` across all guards in the file — `space` when only the bare token appears, `equals` when only the `--flag=` prefix appears, and `both` when both appear. The `line` field records the first guard occurrence for the flag in the file. The list anchors the cognitive review's flag-form-coverage comparison: when one guard in a symmetric pair covers `both` forms while its sibling covers only one, the uncovered form is a defect (e.g., a `--project-dir` guard covering only the space form risks double-injection that violates the mutually-exclusive-arguments contract).

6. **Contract sources** — each modified file's `sources` field is the **union** of two origins:
   - **Directory-structural**: walk up the directory tree (bounded by `--project-dir`) looking for the nearest ancestor containing `SKILL.md`. When found, that `SKILL.md` plus every `*.md` under the same skill's `standards/` subdirectory are sources.
   - **Doc-prose script reference** (`.md` files only): when a modified workflow/standards `.md` doc's added lines contain BOTH an `execute-script.py` invocation via `{bundle}:{skill}:{script}` notation AND a TOON-field reference (a `{field}` interpolation token, e.g. `{status}` or `{error}`), the referenced script's `SKILL.md` — resolved to `marketplace/bundles/{bundle}/skills/{skill}/SKILL.md` — is added as a source. The two signals need not share a line; the doc's added hunk content as a whole must satisfy both. A notation whose `SKILL.md` does not exist on disk surfaces nothing. This surfaces a sibling script's output-contract document on the doc that interpolates its TOON fields, even when the doc lives outside that script's skill directory.

   The `sources` field is a `; `-joined, sorted, deduplicated list of the unioned repo-relative paths. A modified file with neither origin contributes no entry. The list anchors the LLM cognitive review on the contract documents that govern the changed code.

7. **Schema-bearing files** — `*.md` files within `--contract-radius` directory levels of any modified file (default 3 levels up, bounded by `--project-dir`) whose content contains a fenced JSON or TOON block (`` ``` ``json` or `` ``` ``toon`). The list is deduplicated; the `format` field reports the first fence type found. Schema-bearing files surface schema/contract documents the LLM pass must cross-reference against hunks that touch the same schema (e.g., a helper output schema declared in a markdown reference).

8. **Keep-identifier markers** — added lines containing `<!-- self-review: keep <identifier> -->` (see § Keep-Identifier Markers above for the marker contract). For each match the detector emits an entry with `identifier`, `file`, `line`, and `kind`. The `kind` is `keep_protected` when the identifier is still present elsewhere in the file's post-image (the marker line itself is excluded from the grep) and `keep_violation` when the identifier is no longer present — the second case is an orphaned marker that signals the consolidation removed a protected token. The deduplicated, sorted set of every identifier whose marker resolved to `keep_protected` is emitted as `protected_identifiers` so the LLM cognitive review can refuse a consolidation that would drop one of them.

### Errors

| Condition | Output |
|-----------|--------|
| Live footprint empty (no `{base}...HEAD` ∪ porcelain changes) | `status: success` with empty candidate lists (no diff scope) |
| `git -C {project_dir}` fails | `status: error\nerror: git_unavailable\nmessage: ...` (exit 1) |
| Base branch not found | `status: error\nerror: base_branch_not_found\nbase_branch: {base}` (exit 1) |
| Plan not found | `status: error\nerror: plan_not_found` (exit 1) |

## Cwd Policy

This script is a **worktree-scoped (Bucket B)** script (per `tools-script-executor/standards/cwd-policy.md`): callers MAY identify the working tree via either `--plan-id {plan_id}` (auto-resolved through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (explicit override / escape hatch). The script does NOT reintroduce a sideways main-anchored resolver to discover its own root — the resolved path from those flags, or the uniform cwd walk-up (ADR-002), is the only authoritative source.

`manage-references` and `manage-status` reads inside this script do NOT receive `--project-dir`; they discover `.plan/` via the uniform cwd walk-up (ADR-002) from the script's own cwd — main in phases 1-4, the pinned worktree in phase-5+.

## Tests

`test/plan-marshall/ext-self-review-plan-marshall/test_self_review.py` covers:

- Regex detection across `.py` and `.md` hunks (positive + negative)
- User-facing string detection in docstrings, `print()`, and argparse `help=`
- Markdown section enumeration with sibling-list correctness
- Symmetric-pair detection across all 6 pairings
- Symmetric-pair test-presence (`test_present`): `true` when the `test/` tree references the function name, `false` (Tier-2 missing-test signal) when it does not, and word-boundary discipline (no substring false positives, missing `test/` directory → `false`)
- Flag-guard-pair detection: a guard covering both forms (`both`), a guard covering only the space form (`space`), a guard covering only the equals form (`equals`), the asymmetric-pair case (one `both` guard + one single-form sibling), and the negative case (no flag guard → empty list)
- Contract-source doc-prose augmentation: an `.md` doc whose added lines reference a sibling script (`execute-script.py {bundle}:{skill}:{script}`) AND a TOON field (`{status}`) surfaces that script's `SKILL.md`; the doc-referenced source is unioned with any directory-structural sources; a dangling notation (no `SKILL.md` on disk) surfaces nothing; a notation without a TOON-field token surfaces nothing; a TOON-field token without a notation surfaces nothing
- Empty-diff edge case (empty live footprint → empty candidate lists)
- `--project-dir` honoring (script does not discover root from cwd)
- Keep-identifier marker detection: `keep_protected` when the identifier is still grep-able in the post-image; `keep_violation` when the consolidation removed the token; marker syntax variations (whitespace tolerance, multiple markers per file) all recognized

## Canonical invocations

The canonical argparse surface for `self_review.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### surface

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-self-review-plan-marshall:self_review surface \
  --plan-id PLAN_ID [--project-dir PROJECT_DIR] [--base-branch BASE_BRANCH] [--contract-radius CONTRACT_RADIUS]
```

`--project-dir` is optional: when omitted, the worktree path is auto-resolved from `--plan-id`. Supplying both is allowed because `--plan-id` also drives modified-files lookup.

## Related

- [`../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`](../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md) — extension-point contract this skill implements
- [`../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md) — sole consumer of this script's output
- [`../../../plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md`](../../../plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md) — `pre_submission_self_review_inactive` pre-filter that gates dispatch of the consumer step
- [`../../../plan-marshall/skills/tools-script-executor/standards/cwd-policy.md`](../../../plan-marshall/skills/tools-script-executor/standards/cwd-policy.md) — Bucket B cwd contract this script obeys
