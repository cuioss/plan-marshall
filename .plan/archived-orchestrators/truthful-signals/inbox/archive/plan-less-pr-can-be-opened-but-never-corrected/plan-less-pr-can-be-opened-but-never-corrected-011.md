envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T13:05:15Z

# direct-gh-glab-usage reports diff_leak 0 whether Surface B was scanned or unscannable — and its canonical invocation makes it unscannable

- **component**: `plan-marshall:plan-retrospective`
- **category**: bug
- **severity**: warning
- **confidence**: high
- **source**: plan-retrospective of `plan-less-pr-can-be-opened-but-never-corrected` (PR #1065)

## Two defects, one aspect

### 1. A vacuous zero on the documented invocation

The workflow's canonical Step-3 pattern for script-backed aspects is:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:direct-gh-glab-usage \
  run --plan-id {plan_id} --mode {live|archived} > work/fragment-{aspect}.toon
```

No `--base`, no `--project-root`. The script then defaults `project_root` to **cwd** and
`base` to **`main`**. At finalize time cwd is the main checkout and `HEAD` *is* `main`, so
`git diff main...HEAD` is empty and Surface B scans nothing.

It reported:

```
counts: {total: 0, by_surface: {log_leak: 0, diff_leak: 0}}
findings[0]:
```

Re-run against the real range (`--base d0da6742d --project-root <repo>`) it reported
**3** findings. The clean pass was an artifact of the invocation, and the output contract
cannot express the difference — `_git_diff_added_lines` documents this explicitly:

> Failure to run `git` (missing binary, non-repo cwd) returns an empty list without
> raising — the aspect then reports zero diff findings.

The same conflation the sibling candidate-lesson cl2 describes.

### 2. Docstring prose flagged as `severity: error`

All 3 findings from the corrected run are prose inside test docstrings:

```
test/plan-marshall/tools-integration-ci/test_pr_create_planless.py:20
  + from the store and builds the ``gh pr create`` argv from it), and
test/.../test_pr_create_planless.py:139
  + """``--label`` still forwards to ``gh pr create`` on the sentinel path."""
test/.../test_pr_create_planless.py:245
  + """A failed ``gh pr create`` leaves the prepared body in place for a retry.
```

`is_comment_or_blank` filters only `#` comments, so docstrings and string literals fall
through to `_SOURCE_INVOKE_RE` and are emitted at `severity: error` — the same severity a
genuine hard-rule violation would get. A test suite *about* the `gh pr create` path is
guaranteed to trip this, which is precisely the population this aspect should be quietest
about.

## Net substantive verdict for this plan

**No real gh/glab leak.** Surface A (logs) scanned genuinely clean, and all 3 Surface B
hits are false positives. The finding here is about the detector, not the plan.

## Suggested direction

- Emit a per-surface `scanned | unmeasurable` marker; never print a count for an
  unmeasurable surface.
- Either fix the workflow's canonical invocation to pass a real base/root, or have the
  script resolve the plan's own base ref from `references.json` / `status.metadata`
  instead of defaulting to `main` + cwd.
- Filter docstrings and string literals (AST-based) before applying `_SOURCE_INVOKE_RE`.
