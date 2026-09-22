envelope_version=1
sender_type=plan
sender_id=run-3-carve-2-tools-permission-fix
epic=test-quality
kind=landing
created=2026-09-22T11:44:20Z
revision=1
amended=2026-09-22T14:53:03Z

# PLAN-181 carve 2 landing (merged)

PR: https://github.com/cuioss/plan-marshall/pull/1582 (squash-merged)
Merge commit: 1a9a67229ea04fa15741b6dee3da5cadd742d03a
Local plan: run-3-carve-2-tools-permission-fix (4/4 tasks done)

D1 re-derived at base: 2 files over budget (1618, 1587 lines),
65 monkeypatch + 287 tmp_path hits — matches nomination shape.
D2: `_permission_fix_fixtures.py` (198 lines) + 10 `test_*` splits (max 382),
2 originals deleted. Second commit 76d5ae800 removed dead local helpers
per Sourcery review (TASK-004, 5 files, 145 deletions).
D3: pytest 141 passed both orders; AST 124 preserved; `_fidelity_diff`
path-sensitive lost/gained by file moves only (Class::test preserved);
duplication introduced=0; banner introduced=0 (2 pre-existing fixed).
D4: pytest default + reverse green, no skips; doctor `test-conventions`
error-0 (budget 0, down from 2); quality-gate green; CI green on merged head.
D5 (Tier M): `skip-bot-review` label y; CodeRabbit skipped y (label-intended,
informational notice only); Sourcery present y — 1 nitpick triaged FIX,
re-review Approved, inline thread cleared. No human reviews outstanding.

```landing-facts
schema=landing-facts/1
plan_id=run-3-carve-2-tools-permission-fix
pr=#1582
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=0
steps=ship-pr-1582:done,verify-in-worktree:done,merge-queue:done,branch-cleanup:done
```

## Residue
- 3-line ruff-format churn (commit ade0e8ee2) never pushed: merge queue froze
  the head (GH006); CI green without it proves format unenforced; discarded
  with local branches post-merge.
- PR body text stale (single-commit/13-files vs 2 landed commits); D5 log
  lines live here per spec.
- Fidelity instrument path-sensitivity (filed to process-compliance): splits
  can never report lost=0/gained=0 on path-qualified identities.
- Fresh verification worktree retired post-verification; kept branch deleted
  post-merge. Orchestrator queue update (PLAN-181 launched -> shipped) is
  owed on the orchestrator side via this landing drain.
