# Retrospective Aspect: Wrapper Tangle (plan-marshall-plugin-dev)

Detect CI-abstraction leaks in plan-marshall's own wrapper sources, where a `gh`/`glab` CLI invocation is tangled with a local-git side-effect (checkout, branch delete, remote-branch delete) inside the same subprocess / `run_gh` / `run_glab` call.

This is the domain-specific retrospective aspect contributed by `pm-plugin-development` via the `provides_retrospective_aspects()` extension point (`extension-api/standards/ext-point-retrospective.md`). It is the former **Surface C** of the generic `plan-marshall:plan-retrospective:direct-gh-glab-usage` aspect — moved here because scanning plan-marshall's own CI-abstraction sources is only meaningful for plans authored against the `plan-marshall-plugin-dev` domain. The generic aspect retains Surfaces A (plan logs) and B (plan diff), which are domain-invariant.

**Conditional**: runs only when the audited plan's domain is `plan-marshall-plugin-dev`. Emits zero findings when the wrapper sources are clean.

## Purpose

The CI integration abstraction exists because `gh`/`glab` invocations mix two concerns the retrospective needs to keep separate: remote provider operations (PR, issue, review) and local git mutations (checkout, branch delete). When a wrapper shortcuts to direct CLI usage AND tangles local-git side-effects into the same subprocess call, two failure modes become hard to prevent:

1. Worktree-isolated plans silently mutate the main checkout because the `cwd` is not the worktree.
2. The Q-Gate lessons-learned system loses the provenance trail — the retrospective can no longer attribute a side-effect to a known abstraction function.

This aspect surfaces every such leak so the plan retrospective report carries concrete, file-line-snippet evidence rather than a generic rule reminder.

## What It Detects

Python source files under the three plan-marshall CI-wrapper directories:

- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/`

A finding is produced when a call site (`subprocess.`, `run_gh(`, or `run_glab(`) carries, within an 8-line rolling window, both the CLI name (`gh`/`glab`, implicit for the `run_gh`/`run_glab` wrappers) AND any of the local-git-mutation tokens: `checkout`, `branch -d`, `branch -D`, `--delete-branch`, `--remove-source-branch`. This heuristic catches "tangled" invocations that mix remote and local side-effects.

| Surface | Where | Category | Rationale |
|---------|-------|----------|-----------|
| wrapper | `tools-integration-ci` and `workflow-integration-*` scripts | `wrapper_tangle` | Static evidence that the abstraction itself couples CLI + local-git mutation |

## Finding Severity

Every distinct violation is emitted as **one finding at `severity: error`**. No batching — the retrospective compiles all findings verbatim so operators see the full surface area, not a deduplicated summary. When a single source file contains multiple violations, each line yields its own finding.

## Heuristics (false-positive filters)

- **Comment lines**: Lines whose first non-whitespace character is `#` are skipped.
- **Docstring lines**: Lines inside triple-quoted strings (`"""` or `'''`) are skipped. The script tracks docstring state line by line.
- **Anchored mutation tokens**: `checkout`, `--delete-branch`, and `--remove-source-branch` are matched with anchored regexes that refuse adjacent word characters or hyphens, so prefix collisions like `branch_delete` or `--delete-branch-me` cannot trigger a false positive. The `branch -d` / `branch -D` pair is recognised by tokenising on whitespace, brackets, parens, commas, and quotes, then looking for a `branch` token immediately followed by `-d`/`-D` — capturing both shell-style strings and Python list-style args without flagging unrelated identifiers.
- **Pure remote-API calls**: A `gh api repos/...` or `glab` call with no local-git mutation token is a class-A remote-only call and is NOT flagged — the heuristic is scoped to CLI + local-git-mutation combinations.

## Output TOON Schema

```toon
aspect: wrapper-tangle
status: success
domain: plan-marshall-plugin-dev
plan_id: {plan_id}
counts:
  total: N
  by_surface:
    wrapper_tangle: N
findings[N]{surface,file,line,snippet,category,severity}:
  wrapper_tangle,ci_base.py,88,"['gh', 'pr', 'merge', '--delete-branch']","wrapper_tangle",error
```

## Finding Shape

```toon
aspect: wrapper-tangle
severity: error
category: wrapper_tangle
file: {relative path}
line: {1-based line number}
snippet: "{trimmed line content, max 200 chars}"
```

## LLM Interpretation Rules

- Every finding MUST surface in the final report verbatim — the compiler does not reorder, group, or truncate them.
- Wrapper-tangle findings are the highest priority for remediation: they mean the abstraction itself is leaking. They should be proposed as blocking lessons (require fix before plan close) in user-invocable mode.
- A non-zero `counts.total` always produces at least one lessons-proposal entry categorized as `bug`, since it represents a hard-rule violation.

## Out of Scope

- Automated remediation — this aspect reports only; fixes are proposed as lessons and applied in a separate plan.
- Runtime detection of git subprocess calls that do NOT involve `gh`/`glab` — plain `git checkout` outside worktrees is a separate concern handled by the worktree-isolation invariant.
- Documentation/example scanning — markdown files and docstrings are intentionally excluded per the heuristics above.
- Runtime/diff leaks — Surfaces A (plan logs) and B (plan diff) are handled by the generic, domain-invariant `plan-marshall:plan-retrospective:direct-gh-glab-usage` aspect.

## Persistence

After running the aspect script, the retrospective orchestrator pipes its stdout to `work/fragment-wrapper-tangle.toon` and registers it with the bundle:

```bash
python3 .plan/execute-script.py pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan run \
  --plan-id {plan_id} --mode live > work/fragment-wrapper-tangle.toon
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect wrapper-tangle --fragment-file work/fragment-wrapper-tangle.toon
```

`compile-report run --fragments-file` consumes the assembled bundle. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
