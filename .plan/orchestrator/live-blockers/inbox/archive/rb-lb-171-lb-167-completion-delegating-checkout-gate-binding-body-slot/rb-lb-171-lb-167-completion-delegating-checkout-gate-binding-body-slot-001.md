envelope_version=1
sender_type=plan
sender_id=rb-lb-171-lb-167-completion-delegating-checkout-gate-binding-body-slot
epic=live-blockers
kind=landing
created=2026-11-20T08:22:52Z
revision=4
amended=2026-11-20T10:48:11Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-171-lb-167-completion-delegating-checkout-gate-binding-body-slot
epic=live-blockers
pr=#2033
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2155
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=16
review_body_findings_handled=16
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

## Outcome

**Merged.** PR #2033, merged by the merge queue; merge commit `c22d103fbf1b6a73ba66c82c238813b79b460f1c`. Merge-group run `44718895487` concluded `success`. Cleanup done: worktree removed (clean before removal), branch deleted locally and on the remote, main checkout fast-forwarded from `51859e67` to the merge commit.

`deliverables_done=4` of 5: **D1 is not met as written** — on the operator's direction its delegated branch was descoped (commit `1506824a0`, −1049 lines) and the delegating-consumer case is re-staged as its own plan.

## The merge override (recorded)

`review-gate` reported `merge_allowed: false` with `thread_concern_remains` on thread `PRRT_kwDOQ3xasM654AV2`. That finding is about the delegated branch the descope removed, and the gate keys on the reviewer's last comment, which no reply of ours rewrites. Everything else held on head `1506824a0`: CI green (`verify / verify`, `verify / gate`, `verify / conclusion`, SonarCloud, generate-check, dependency-review), local `verify` green, 0 unresolved threads, 16/16 review-body findings dispositioned.

The operator was asked with the question tool, the option text named the exact gap (thread, head, the gate's reason), and the operator selected **"Merge anyway (operator override)"**. The merge was then performed through the queue. This is recorded as an operator override of one gate condition — not as a gate pass.

## What shipped

- **D2** — head-bound read licence: `read_open_issues` requires `--carried-forward-head-revision` beside `--analysed-revision`, refuses `analysed_revision_requires_verified_head` and `carried_forward_head_mismatch`; `sonar-gate` and `sonar-facts` require the read's own `--carried-forward` marker with both revisions, and the facts render `carried_forward=true` with both heads.
- **D3** — per-caller body slot: the plan-less default slot is refused (`shared_body_slot_refused`) for a caller that reads a body; the slot bound admits a plan id; `land.md` names `slot land`; the lane names its plan id; the docs state the rule.
- **D4** — the lane's §6/§7/§8 and the Sonar skill state what the code does (no retry for a refused stale read, the cause the right way round, the marker's path).
- **D5** — the tests, written red-first (20 + 9 + 3 failures at `a024fc8c2`), including the two real-classifier twins.
- **D1** — descoped, not met.

## Residue

- The delegating-consumer case is re-staged; its review asked for run-identity evidence, which needs a CI-abstraction field that does not exist.
- D2's marker is caller-asserted, and the read's head comes from local refs.
- D3's slot is the plan id; a resolver-exposed bounded `body_slot` is follow-up, as is the mirrored body-verb tuple in the lane test.
