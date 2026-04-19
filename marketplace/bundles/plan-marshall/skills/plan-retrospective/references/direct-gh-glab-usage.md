# Aspect: Direct gh/glab Usage

Detect CI-abstraction leaks where the GitHub CLI (`gh`) or GitLab CLI (`glab`) is invoked directly — bypassing the `plan-marshall:tools-integration-ci:ci` abstraction — and, in particular, where such an invocation also performs a local-git side-effect (checkout, branch delete, remote-branch delete). Direct usage is a hard-rule violation documented in `CLAUDE.md` under *Workflow Discipline → CI operations: use abstraction layer*.

**Conditional**: always runs; emits zero findings when the codebase is clean.

## Purpose

The CI integration abstraction exists because `gh`/`glab` invocations mix two concerns the retrospective needs to keep separate: remote provider operations (PR, issue, review) and local git mutations (checkout, branch delete). When a caller shortcuts to direct CLI usage AND tangles local-git side-effects into the same subprocess call, two failure modes become hard to prevent:

1. Worktree-isolated plans silently mutate the main checkout because the `cwd` is not the worktree.
2. The Q-Gate lessons-learned system loses the provenance trail — the retrospective can no longer attribute a side-effect to a known abstraction function.

This aspect surfaces every such leak so the plan retrospective report carries concrete, file-line-snippet evidence rather than a generic rule reminder.

## Inputs

Three detection surfaces, each inspected independently:

- **Surface A — plan logs**: `logs/work.log` and `logs/script-execution.log` inside the plan directory. Lines where `gh `, `glab `, or `gh.` appears outside comments and strings are flagged. This captures runtime leaks recorded during plan execution.
- **Surface B — plan diff**: `git diff {base}...HEAD` (where `{base}` is the plan's base branch, typically `main`). Added lines (`+` diff prefix) invoking `gh` or `glab` are flagged. This captures code-level leaks introduced by the plan.
- **Surface C — CI wrapper sources**: Python source files under `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/`, `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/`, and `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/` — the very modules that are supposed to be the abstraction. A finding is produced when a subprocess `args` list contains both the CLI name (`gh`/`glab`) AND any of the local-git-mutation tokens: `checkout`, `branch -d`, `branch -D`, `--delete-branch`, `--remove-source-branch`. This heuristic catches "tangled" invocations that mix remote and local side-effects.

## What It Detects

| Surface | Where | Category | Rationale |
|---------|-------|----------|-----------|
| A | `logs/work.log`, `logs/script-execution.log` | `log_leak` | Runtime evidence of a direct CLI invocation during plan execution |
| B | `git diff {base}...HEAD` added lines | `diff_leak` | Code-level evidence of a direct CLI invocation introduced by the plan |
| C | `tools-integration-ci` and `workflow-integration-*` scripts | `wrapper_tangle` | Static evidence that the abstraction itself couples CLI + local-git mutation |

## Finding Severity

Every distinct violation is emitted as **one finding at `severity: error`**. No batching — the retrospective compiles all findings verbatim so operators see the full surface area, not a deduplicated summary. When a single source file contains multiple violations (e.g., three `gh` invocations on different lines), each line yields its own finding.

## Heuristics (false-positive filters)

To avoid flagging commentary, documentation, or examples, the script applies the following filters to source inspection (Surfaces B and C):

- **Comment lines**: Lines whose first non-whitespace character is `#` are skipped.
- **Docstring lines**: Lines inside triple-quoted strings (`"""` or `'''`) are skipped. The script tracks docstring state line by line.
- **Markdown/documentation context**: Lines inside fenced code blocks within `.md` files are ignored unless the surface explicitly targets source code — Surface B's diff scan only counts added lines in `.py` files.

Surface A (logs) does not apply comment/docstring filters because log lines are never commented-out source — every matched line is real runtime evidence.

## Output TOON Schema

```toon
aspect: direct_gh_glab_usage
status: success
plan_id: {plan_id}
counts:
  total: N
  by_surface:
    log_leak: N
    diff_leak: N
    wrapper_tangle: N
findings[N]{surface,file,line,snippet,category,severity}:
  log_leak,logs/work.log,42,"...gh pr view 123...","log_leak",error
  diff_leak,scripts/foo.py,17,"+    subprocess.run(['gh', ...])","diff_leak",error
  wrapper_tangle,ci_base.py,88,"['gh', 'pr', 'merge', '--delete-branch']","wrapper_tangle",error
```

## LLM Interpretation Rules

- Every finding MUST surface in the final report verbatim — the compiler does not reorder, group, or truncate them.
- A non-zero `counts.total` always produces at least one lessons-proposal entry (see `references/lessons-proposal.md`) categorized as `bug`, since it represents a hard-rule violation.
- Surface C findings are the highest priority for remediation: they mean the abstraction itself is leaking. They should be proposed as blocking lessons (require fix before plan close) in user-invocable mode.
- Surface A findings without a matching Surface B or C finding indicate runtime-only leaks — typically an LLM manually typed `gh` into Bash despite the hard rule. These should be proposed as `improvement` lessons targeting the calling component.

## Finding Shape

```toon
aspect: direct_gh_glab_usage
severity: error
category: {log_leak|diff_leak|wrapper_tangle}
file: {relative path}
line: {1-based line number}
snippet: "{trimmed line content, max 200 chars}"
message: "Direct {gh|glab} usage detected at {file}:{line}"
```

## Out of Scope

- Automated remediation — this aspect reports only; fixes are proposed as lessons and applied in a separate plan.
- Runtime detection of git subprocess calls that do NOT involve `gh`/`glab` — plain `git checkout` outside worktrees is a separate concern handled by the worktree-isolation invariant.
- Documentation/example scanning — markdown files and docstrings are intentionally excluded per the heuristics above.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-direct-gh-glab-usage.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect direct-gh-glab-usage --fragment-file work/fragment-direct-gh-glab-usage.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
