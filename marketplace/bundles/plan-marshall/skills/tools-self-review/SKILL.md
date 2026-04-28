---
name: tools-self-review
description: Deterministic candidate surfacing for pre-submission structural self-review (regexes, user-facing strings, markdown sections, symmetric-pair functions)
user-invocable: false
---

# Self-Review Candidate Surfacing

**Role**: Deterministic helper for the `default:pre-submission-self-review` finalize step. Surfaces concrete candidates from the worktree's staged diff so the LLM cognitive review pass can apply the four structural-defect checks (symmetric pair, regex over-fit, wording disambiguation, duplication) against a bounded surface, not an unbounded read of the whole diff.

## Enforcement

**Execution mode**: Library script; invoked via the standard 3-part executor notation by `phase-6-finalize/standards/pre-submission-self-review.md`.

**Prohibited actions:**
- Do not modify any source files; the helper is read-only against the worktree
- Do not invoke `git` without `git -C {project_dir}` (per dev-general-practices)
- Do not write to `/tmp/` or any path outside `.plan/temp/` when staging intermediate state (lesson `2026-04-27-23-001`)

**Constraints:**
- stdlib-only (no third-party Python dependencies)
- Output is TOON to stdout; errors are TOON with `status: error` and a non-zero exit code
- Every candidate entry MUST carry `file` (repo-relative path) and `line` (1-based line number in the post-diff file content) — these are the only fields the LLM cognitive review consumes for navigation

## When to Use

Invoked exclusively by `default:pre-submission-self-review` (see `phase-6-finalize/standards/pre-submission-self-review.md`). No other caller is supported. The script is registered as `plan-marshall:tools-self-review:self_review` and is NOT user-invocable from a slash command — `user-invocable: false` per the script-only registration convention (see MEMORY.md "plugin.json Registration Rules"; this skill is intentionally absent from `plan-marshall/.claude-plugin/plugin.json`).

## Subcommand: `surface`

Surfaces four candidate lists from the worktree's staged diff against the base branch.

### Inputs

| Argument | Required | Description |
|----------|----------|-------------|
| `--plan-id PLAN_ID` | Yes | Plan identifier (kebab-case). Used to read `references.modified_files`. |
| `--project-dir PROJECT_DIR` | Yes | Absolute path to the active git worktree. All `git` calls run as `git -C {project_dir} ...`. |
| `--base-branch BRANCH` | No | Base branch for diff computation. Defaults to `main`. |

### Output

TOON to stdout. The four candidate-list keys are always present (possibly empty):

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
  total: N1+N2+N3+N4

regexes[N1]{file,line,pattern}:
  {repo-relative-path},{line},{regex-pattern-string}

user_facing_strings[N2]{file,line,context,text}:
  {repo-relative-path},{line},{context-tag},{string-text}

markdown_sections[N3]{file,line,heading,siblings}:
  {repo-relative-path},{heading},{semicolon-joined-sibling-headings}

symmetric_pairs[N4]{file,line,name,partner}:
  {repo-relative-path},{line},{function-name},{inferred-partner-name}
```

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

4. **Symmetric-pair candidates** — added lines in `.py` files matching `^def\s+(\w+)`. The captured function name is split on `_` and inspected for any of the 6 pair tokens: `save/load`, `init/restore`, `push/pop`, `acquire/release`, `open/close`, `start/stop`. When a match is found, the `partner` field is the same function name with the matched token swapped to its pair (e.g., `save_state` → `load_state`).

### Errors

| Condition | Output |
|-----------|--------|
| `references.modified_files` missing or empty | `status: success` with empty candidate lists (no diff scope) |
| `git -C {project_dir}` fails | `status: error\nerror: git_unavailable\nmessage: ...` (exit 1) |
| Base branch not found | `status: error\nerror: base_branch_not_found\nbase_branch: {base}` (exit 1) |
| Plan not found | `status: error\nerror: plan_not_found` (exit 1) |

## Cwd Policy

This script is **Bucket B** (per `tools-script-executor/standards/cwd-policy.md`): callers MUST pass `--project-dir {worktree_path}`. The script does NOT call `git rev-parse --git-common-dir` to discover its own root — `--project-dir` is the only authoritative source.

`manage-references` and `manage-status` reads (Bucket A) inside this script do NOT receive `--project-dir`; they discover `.plan/` via `git rev-parse --git-common-dir` from the script's own cwd.

## Tests

`test/plan-marshall/tools-self-review/test_self_review.py` covers:

- Regex detection across `.py` and `.md` hunks (positive + negative)
- User-facing string detection in docstrings, `print()`, and argparse `help=`
- Markdown section enumeration with sibling-list correctness
- Symmetric-pair detection across all 6 pairings
- Empty-diff edge case (no `modified_files` → empty candidate lists)
- `--project-dir` honoring (script does not discover root from cwd)

## Related

- `phase-6-finalize/standards/pre-submission-self-review.md` — sole consumer of this script's output
- `manage-execution-manifest/standards/decision-rules.md` — `pre_submission_self_review_inactive` pre-filter that gates dispatch of the consumer step
- `tools-script-executor/standards/cwd-policy.md` — Bucket B cwd contract this script obeys
