envelope_version=1
sender_type=plan
sender_id=rb-lb-134-opencode-permission-writer
epic=live-blockers
kind=landing
created=2026-11-11T03:46:22Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-134-opencode-permission-writer
epic=live-blockers
pr=#1954
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=8
review_body_findings_handled=8
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# Landing — PLAN-LB-134 (merged)

This supersedes `rb-lb-134-opencode-permission-writer-001`, which was written and archived before the merge and therefore recorded `merge_state: open`. The message was already archived when the correction was attempted, so `inbox amend` refused it (`not_live`); this is a fresh landing rather than an edit of a filed message.

PR #1954 is merged on `main` through the merge queue; merge commit `b09bf3197118f7fc5efcfa2c49338a1b089d01ee`. The branch, its remote ref and the worktree are cleaned up, and the main checkout was updated through `switch-and-pull`.

## What changed after the archived landing

* CodeRabbit's quota reset and it reviewed **twice**: `03a35cf11` (6 findings) and `3769c5d12` (2 inline + 1 outside-diff). Seven were fixed (`3769c5d12`, `686146186`), one was answered with a reason (the audit/health source-set difference: documented, not unified). Every thread was replied to and resolved; `review-gate` on the merged head reports 0 unresolved threads and 8/8 body findings handled.
* The later fixes went beyond the original patch where the reviewers proved the same defect class elsewhere: the conflict scan now considers only rules a write actually crosses; the OpenCode 1 map's `*` row is written first in all four writers; a map removal matches the effect; and **the emitter writes no agent permission rule at all**, because the override the plan fixed for `shell` applied equally to `read`/`edit`.
* `verify`, `quality-gate` and `module-tests plan-marshall` are green on the merged head; CI (verify, gate, SonarCloud, dependency-review, generate-check) is green on it.
* One finding was deliberately not taken: `ensure` returning a conflict for a rule a broader later row already shadows. The spec's D1 Done-when requires exactly that conflict branch, so it was kept and the reasoning given in the thread.

Everything else in the archived landing still stands: the deliverable verdicts and their `mutation-after` evidence, the recorded verify-first sources and versions, the personas and skills, and the three residue items (the `permission.bash` scalar destruction by six older writers, `--dry-run` not predicting conflicts, and the `contract.md` drifts around a non-object JSON root and `save_error` vs `io_error`).
