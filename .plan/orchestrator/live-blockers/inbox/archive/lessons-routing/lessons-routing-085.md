envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-10T16:59:37Z

# A quality gate that rewrites files records its success against a tree that is never committed, so the freshness gate cannot clear

**Severity:** high (operator grade, 2026-11-10 drain of the lessons-routing inbox)
**Bundle:** plan-marshall (`phase-5-execute`, `manage-tasks` freshness gate)
**Checked at:** `e7033b83a` (origin/main)

## What was reported

pm-mcp-core plan `plan-v2-93-http-tests-annotations`: `verify -Ppre-commit` rewrote the import order of `pm-provider-http/.../HttpClient.java` on every run. The freshness gate stayed `stale` with `build_indeterminate`:

- the dispatch row was recorded against the clean tree `1c781679` with status `unknown` (the wrapper returned `running` after 300 s);
- the success row (1049 s, 9367 tests) was recorded against the dirty end-state tree `9d87c1fb`;
- after the rewrite was discarded the tree was `1c781679` again, so no success row matched it. Re-running could never clear it. Two jobs showed the pattern (`8af4fa43`, `e01bad99`).

It cost an extra hand-back dispatch and an operator ruling. The sender's proposal: record the success of a long-running or rewriting build against the tree at dispatch, or record both and accept a match on the dispatch tree when the end-state diff is only the gate's own rewrite; name the rewrite in the hand-back.

## Ground truth at the checked commit

`marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py`:

- `:261-262` selects the rows that count as evidence with `entry.get('kind') == KIND_BUILD and entry.get('worktree_sha') == current_sha`. A success row keyed on any other tree never matches.
- `:264-266` returns `worktree_mutated` when no build row matches the current tree.
- `:268-271` reports the LAST row for the current tree, here the `unknown` dispatch row, which maps to `build_indeterminate`.

So the described behaviour follows from the code as read: a success recorded against a different tree than the one finally committed cannot satisfy the gate. The recording side (which tree the success row is keyed on) was NOT read.

## Relation to filed work

`lessons-routing-068` (freshness gate passed on a 5-test row labelled whole-tree) is the false-pass direction; this is the false-fail direction and cannot be cleared by re-running. `PLAN-LB-130` (freshness-gate-scope-by-notation, running) touches the same gate: please check for overlap before opening new work.

## Source

- `pm-mcp-core-m2-m4-v2-001`, archived verbatim at `lessons-routing/inbox/archive/pm-mcp-core-m2-m4-v2/`.
