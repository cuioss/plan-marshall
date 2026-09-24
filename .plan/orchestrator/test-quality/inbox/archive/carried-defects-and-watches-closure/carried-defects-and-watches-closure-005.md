envelope_version=1
sender_type=plan
sender_id=carried-defects-and-watches-closure
epic=test-quality
kind=landing
created=2026-09-24T05:29:28Z

# PLAN-183 shipped (carried-defects-and-watches-closure) — final landing

## landing-facts
- plan_marshall_plan_id: carried-defects-and-watches-closure
- epic_plan: PLAN-183
- pr: #1602
- pr_url: https://github.com/cuioss/plan-marshall/pull/1602
- merge_commit_sha: 4ef2efd2f51bbe001dcb0594b894543ef004ebe2
- strategy: squash (via platform merge queue)
- commits: b1d6517dc (10 files, D1–D8), 5f4f73cb6 (4 files, review triage)
- local_plan: archived to .plan/local/archived-plans/2026-09-24-carried-defects-and-watches-closure (reason normal_completion)
- worktree: removed; local branch deleted; remote head deleted by queue
- tier_m_skip_bot_review: n
- coderabbit: 5 actionable, all fixed/replied/resolved; rate-limited on fix commit (walkthrough only, no new actionables)
- sourcery: rate-limit notice only, zero findings
- ci_on_merge_head: success (verify 1381s, gate, generate-check, dependency-review)
- d7_decision: DEFER flip (counts 427/21/19 non-zero); re-check at zero
- known_residual: whole-tree module-tests exceed local build timeouts (CI verify covers it); main checkout left 2 behind origin (operator drain owns the pending ledger dirt — pull deferred to protect in-flight process-compliance/test-quality edits)

## Scope note (operator overrule invited)
- `test_test_conventions_rule2.py` edit read as D1 scope per the Done clause ("the kwarg test proves the PYTHONPATH behavior"); inbox filename 002 was re-allocated over a drained predecessor (triage content current, PR-update content in history) — orchestrator to confirm ledger soundness on drain.
