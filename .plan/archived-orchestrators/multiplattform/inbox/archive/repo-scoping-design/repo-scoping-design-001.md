envelope_version=1
sender_type=plan
sender_id=repo-scoping-design
epic=multiplattform
kind=landing
created=2026-09-05T21:13:29Z

```landing-facts
schema=landing-facts/1
plan_id=repo-scoping-design
epic=multiplattform
pr=#1420
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=unknown
steps=step-4-implement:done,step-5-build-gate:done,step-6-verifier:clear,step-7-pr:done,step-8-merge:done,step-9-self-check:done
```

## Residue

- **`total_tokens=unknown`**: the opencode session could not report a token total; routed to `unknown` per the landing contract (never `n/a`). The orchestrator's completeness check will name it missing; this is the correct outcome, not a defect.
- **Sourcery review was rate-limited** (per-developer budget, "1 day and 16 hours" to next): optional reviewer, expected, not a shortfall; disclosed to the operator before merging.
- **Follow-up issue #1421** was created by CodeRabbit at the operator's acceptance: a machine-checkable lock-step check for the dispatch-boundary contract (out of this decision record's scope).
- **Contract improvements approved and applied**: RUNBOOK.md gained `--timeout 1800` guidance for `verify` and the worktree executor-provisioning note. The opencode runbook is host-local and git-ignored, so there is no version-controlled file to raise a separate PR for; the edits were applied to the working contract and recorded in the run report.
